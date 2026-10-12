"""Pull one user's Partiful events and guest lists into Postgres.

Payload parsing and role rules live in ``afterparty.core``; this module drives
the API calls, writes the rows, and keeps each sync run's progress.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
import psycopg
from psycopg.types.json import Jsonb

from . import crypto, db, demo
from .config import settings
from .core.models import Event, Guest
from .core.parse import classify_event, event_from_row, guests_from_rows
from .core.roles import infer_role
from .partiful_api import PartifulApiError, PartifulAuthError, PartifulClient

log = logging.getLogger("afterparty.sync")

#: Events whose guest list we pull: you were there, you're hosting, or you're going.
GUEST_ROLES = {"attended", "hosting", "going"}
#: Guest-list statuses for people who were not (or will not be) at the event.
NOT_IN_ROOM = {
    "DECLINED",
    "WITHDRAWN",
    "SENT",
    "INVITED",
    "PENDING_APPROVAL",
    "WAITLISTED_FOR_APPROVAL",
    "WAITLISTED",
    "REJECTED",
    "REMOVED",
    "CANCELLED",
    "NOT_GOING",
}
#: Bucket order = trust order: an event in the past-events bucket is known past.
BUCKET_ORDER = ("pastEvents", "initialPastEvents", "upcomingEvents")
#: A run whose heartbeat has been silent this long died with its instance.
STALE_AFTER = timedelta(minutes=10)
#: Past events stop changing; a guest list pulled this long after the event ends is final.
SETTLE_AFTER = timedelta(days=3)
#: The scheduler skips users synced more recently than this.
DAILY_GAP = timedelta(hours=20)

IMGIX = "https://partiful.imgix.net"
#: Guests type whatever they like into socials. Only links to the platform itself survive.
SOCIAL_HOSTS = {
    "twitter": ("x.com", "twitter.com"),
    "instagram": ("instagram.com",),
    "linkedin": ("linkedin.com",),
    "tiktok": ("tiktok.com",),
    "facebook": ("facebook.com", "fb.com"),
    "snapchat": ("snapchat.com",),
    "venmo": ("venmo.com",),
}
IMAGE_HOSTS = ("partiful.imgix.net", "firebasestorage.googleapis.com")

_live_runs: set[int] = set()
_live_lock = threading.Lock()


# ---------------------------------------------------------------- transforms
def events_from_home(pairs: list[tuple[str, dict]], self_uid: str) -> list[Event]:
    """Dedupe bucketed home-page rows (most trusted bucket wins) and classify."""

    def rank(bucket: str) -> int:
        return BUCKET_ORDER.index(bucket) if bucket in BUCKET_ORDER else len(BUCKET_ORDER)

    best: dict[str, tuple[int, dict, str]] = {}
    for bucket, row in pairs:
        key = str(row["id"])
        r = rank(bucket)
        if key not in best or r < best[key][0]:
            best[key] = (r, row, bucket)
    out: list[Event] = []
    for _, row, bucket in best.values():
        ev = event_from_row({**row, "__source": "home", "__path": f"$.{bucket}"})
        ev.role = classify_event(ev, self_uid)
        out.append(ev)
    out.sort(key=lambda e: e.start_date or "", reverse=True)
    return out


def _host_ok(url: str, hosts: tuple[str, ...]) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme in ("http", "https") and any(
        host == h or host.endswith("." + h) for h in hosts
    )


def safe_socials(socials: dict[str, str]) -> dict[str, str]:
    """Drop any social link that doesn't point at its own platform: a guest
    could otherwise plant a phishing URL behind the X icon for everyone."""
    return {
        k: v
        for k, v in (socials or {}).items()
        if k in SOCIAL_HOSTS and isinstance(v, str) and _host_ok(v, SOCIAL_HOSTS[k])
    }


def event_image(raw: dict) -> str | None:
    image = raw.get("image") if isinstance(raw.get("image"), dict) else {}
    upload = image.get("upload") if isinstance(image.get("upload"), dict) else {}
    if upload.get("path"):
        return f"{IMGIX}/{str(upload['path']).strip('/')}?fit=crop&w=480&h=480&auto=format&dpr=2"
    url = image.get("url")
    # A host-chosen URL elsewhere would load in every viewer's browser: Partiful's own hosts only.
    return url if isinstance(url, str) and _host_ok(url, IMAGE_HOSTS) else None


def clean(value):
    """Postgres rejects NUL in text and jsonb; one stray byte in a bio must not sink a sync."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {clean(k): clean(v) for k, v in value.items()}
    return value


def person_key(g: Guest) -> str:
    return g.user_id or (f"u:{g.partiful_username}" if g.partiful_username else f"n:{g.name}")


def _ts(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        stamp = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


def needs_guest_pull(ev: Event, last_pulled: datetime | None, full: bool) -> bool:
    """Pull until a pull has happened after the event settled. A list pulled
    before the night (RSVPs) is never the final record of who was there."""
    if full or last_pulled is None:
        return True
    ended = _ts(ev.end_date) or _ts(ev.start_date)
    return ended is None or last_pulled < ended + SETTLE_AFTER


# ---------------------------------------------------------------- db writes
def _upsert_event(user_id: int, ev: Event) -> None:
    raw = ev.raw or {}
    db.run(
        """
        INSERT INTO events (user_id, event_id, title, starts_at, ends_at, timezone, location,
                            image_url, role, my_rsvp, partiful_count, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (user_id, event_id) DO UPDATE SET
            title = EXCLUDED.title, starts_at = EXCLUDED.starts_at, ends_at = EXCLUDED.ends_at,
            timezone = EXCLUDED.timezone, location = EXCLUDED.location,
            image_url = EXCLUDED.image_url, role = EXCLUDED.role, my_rsvp = EXCLUDED.my_rsvp,
            partiful_count = EXCLUDED.partiful_count, updated_at = now()
        """,
        clean_row(
            (
                user_id,
                ev.id,
                (ev.name or "").strip(),
                _ts(ev.start_date),
                _ts(ev.end_date),
                raw.get("timezone"),
                ev.location,
                event_image(raw),
                ev.role,
                ev.my_rsvp,
                ev.partiful_attended_count,
            )
        ),
    )


def clean_row(row: tuple) -> tuple:
    return tuple(clean(v) for v in row)


def _replace_guests(user_id: int, event_id: str, guests: list[Guest], hidden: int, rows: int):
    with db.conn() as c, c.transaction():
        c.execute("DELETE FROM guests WHERE user_id = %s AND event_id = %s", (user_id, event_id))
        with c.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO guests (user_id, event_id, person_id, name, username, avatar_url, bio,
                                    rsvp, plus_ones, socials, linkedin_url, cluster)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [
                    clean_row(
                        (
                            user_id,
                            event_id,
                            person_key(g),
                            g.name,
                            g.partiful_username,
                            g.avatar_url,
                            g.bio,
                            g.rsvp_status,
                            g.plus_ones,
                            Jsonb(clean(safe_socials(g.socials or {}))),
                            g.linkedin_url,
                            g.role or "unknown",
                        )
                    )
                    for g in guests
                ],
            )
        c.execute(
            "UPDATE events SET guest_rows = %s, hidden_rows = %s, guests_synced_at = now()"
            " WHERE user_id = %s AND event_id = %s",
            (rows, hidden, user_id, event_id),
        )


def _progress(run_id: int, **fields) -> None:
    """Record progress; every write is also the run's heartbeat."""
    fields["heartbeat_at"] = _now()
    sets = ", ".join(f"{k} = %({k})s" for k in fields)
    db.run(f"UPDATE sync_runs SET {sets} WHERE id = %(id)s", {**fields, "id": run_id})  # noqa: S608


# ---------------------------------------------------------------- the sync
def sync_user(user_id: int, run_id: int, full: bool = False) -> None:
    with _live_lock:
        _live_runs.add(run_id)
    try:
        _sync_user(user_id, run_id, full)
    finally:
        with _live_lock:
            _live_runs.discard(run_id)


def _sync_user(user_id: int, run_id: int, full: bool) -> None:
    acct = db.one("SELECT * FROM partiful_accounts WHERE user_id = %s", (user_id,))
    if not acct:
        _progress(run_id, status="error", error="Partiful is not connected.", finished_at=_now())
        return
    if acct["partiful_uid"] == demo.DEMO_UID and settings.dev_auth_allowed:
        demo.seed(user_id, run_id, delay=0.7)
        return

    stored = acct["refresh_token_enc"]

    def keep_rotated(new_token: str) -> None:
        # Guard on the blob we started from, so a reconnect that happened mid-sync wins.
        nonlocal stored
        new_blob = crypto.encrypt(new_token)
        db.run(
            "UPDATE partiful_accounts SET refresh_token_enc = %s"
            " WHERE user_id = %s AND refresh_token_enc = %s",
            (new_blob, user_id, stored),
        )
        stored = new_blob

    try:
        refresh_token = crypto.decrypt(stored)
        with PartifulClient(
            refresh_token, acct["api_key"], settings.partiful_delay, on_rotate=keep_rotated
        ) as pc:
            _progress(run_id, phase="events")
            events = events_from_home(pc.home_events(), pc.uid)
            for ev in events:
                _upsert_event(user_id, ev)

            pulled = {
                r["event_id"]: r["guests_synced_at"]
                for r in db.all_(
                    "SELECT event_id, guests_synced_at FROM events WHERE user_id = %s", (user_id,)
                )
            }
            targets = [
                e
                for e in events
                if e.role in GUEST_ROLES and needs_guest_pull(e, pulled.get(e.id), full)
            ]
            _progress(run_id, phase="guests", events_total=len(targets))
            total, failed = 0, []
            for i, ev in enumerate(targets, 1):
                try:
                    rows = pc.guests(ev.id, hosting=ev.role == "hosting")
                    guests = [
                        g
                        for g in guests_from_rows(rows, ev.id)
                        if g.user_id != pc.uid and (g.rsvp_status or "").upper() not in NOT_IN_ROOM
                    ]
                    hidden = sum(1 for r in rows if not (r.get("user") or r.get("name")))
                    _replace_guests(user_id, ev.id, guests, hidden, len(rows))
                    total += len(guests)
                except PartifulAuthError:
                    raise
                except (PartifulApiError, httpx.HTTPError, psycopg.DataError) as exc:
                    # One unreadable event must not cost the user every other one.
                    log.warning("user %s event %s: %s", user_id, ev.id, exc)
                    failed.append(ev.name or ev.id)
                _progress(run_id, events_done=i, guests=total)

        if targets and len(failed) * 2 > len(targets):
            # Most of the run failed: say so, and don't claim a fresh sync.
            _progress(
                run_id,
                status="error",
                error="Partiful did not answer for most events. Afterparty will try again.",
                finished_at=_now(),
            )
            return
        recluster(user_id)
        db.run(
            "UPDATE partiful_accounts SET last_sync_at = now(), token_error = NULL"
            " WHERE user_id = %s",
            (user_id,),
        )
        note = (
            f"Could not read {len(failed)} event(s): {', '.join(failed)[:300]}" if failed else None
        )
        _progress(run_id, status="ok", phase="done", error=note, finished_at=_now())
    except PartifulAuthError as exc:
        log.warning("user %s: Partiful session expired: %s", user_id, exc)
        db.run(
            "UPDATE partiful_accounts SET token_error = %s WHERE user_id = %s",
            (str(exc)[:300], user_id),
        )
        _progress(
            run_id,
            status="error",
            error="Your Partiful session expired. Reconnect Partiful in Settings.",
            finished_at=_now(),
        )
    except Exception:
        # The detail goes to the logs, not to the browser.
        log.exception("user %s: sync failed", user_id)
        _progress(
            run_id,
            status="error",
            error="The sync stopped on an error. Try again in a few minutes.",
            finished_at=_now(),
        )


def recluster(user_id: int) -> int:
    """Apply the current designation rules to every stored bio, so a rule fix
    reaches past events that are no longer re-read."""
    rows = db.all_(
        "SELECT DISTINCT bio, cluster FROM guests WHERE user_id = %s AND bio IS NOT NULL",
        (user_id,),
    )
    changed = 0
    for r in rows:
        new = infer_role(r["bio"])
        if new != r["cluster"]:
            changed += db.run(
                "UPDATE guests SET cluster = %s WHERE user_id = %s AND bio = %s AND cluster <> %s",
                (new, user_id, r["bio"], new),
            )
    return changed


def _now() -> datetime:
    return datetime.now(UTC)


def active_run(user_id: int) -> dict | None:
    """The running sync, if any. Runs whose heartbeat went silent are closed as dead."""
    db.run(
        "UPDATE sync_runs SET status = 'error', error = 'The sync stopped unexpectedly.',"
        " finished_at = now() WHERE user_id = %s AND status = 'running'"
        " AND coalesce(heartbeat_at, started_at) < %s",
        (user_id, _now() - STALE_AFTER),
    )
    return db.one(
        "SELECT * FROM sync_runs WHERE user_id = %s AND status = 'running'"
        " ORDER BY started_at DESC LIMIT 1",
        (user_id,),
    )


def start_sync(user_id: int, trigger: str, full: bool = False, background: bool = True) -> dict:
    """Start a sync unless one is already running; return the run row either way.
    A unique index allows one running run per user, so two callers can't both start."""
    running = active_run(user_id)
    if running:
        return running
    try:
        run = db.one(
            "INSERT INTO sync_runs (user_id, trigger, phase) VALUES (%s, %s, 'starting')"
            " RETURNING *",
            (user_id, trigger),
        )
    except psycopg.errors.UniqueViolation:
        return active_run(user_id) or {}
    if background:
        threading.Thread(
            target=sync_user, args=(user_id, run["id"], full), daemon=True, name=f"sync-{user_id}"
        ).start()
    else:
        sync_user(user_id, run["id"], full)
    return run


def abandon_live_runs() -> None:
    """On shutdown: runs this process was doing will not finish. Say so now
    instead of leaving a frozen "Syncing 3 of 40" until the heartbeat expires."""
    with _live_lock:
        ids = list(_live_runs)
    if ids:
        db.run(
            "UPDATE sync_runs SET status = 'error', finished_at = now(),"
            " error = 'The server restarted during the sync. Sync again.'"
            " WHERE id = ANY(%s) AND status = 'running'",
            (ids,),
        )


def sync_all(trigger: str = "schedule") -> int:
    """Daily: sync every connected user not synced in the last DAILY_GAP,
    one after another. Accounts with an expired session are retried too: the
    refresh fails fast if it is really dead, and recovers if it was transient."""
    users = db.all_(
        "SELECT u.id FROM users u JOIN partiful_accounts a ON a.user_id = u.id"
        " WHERE a.last_sync_at IS NULL OR a.last_sync_at < %s"
        " ORDER BY a.last_sync_at NULLS FIRST",
        (_now() - DAILY_GAP,),
    )
    for u in users:
        start_sync(u["id"], trigger, background=False)
    return len(users)
