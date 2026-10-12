"""Afterparty HTTP API + the built single-page app."""

from __future__ import annotations

import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import connector, crypto, db, demo, sync
from .auth import current_user, verify_scheduler
from .config import settings
from .partiful_api import PartifulApiError, PartifulAuthError, refresh
from .people import FollowFilter, PeopleFilters, SocialFilter, query_people, to_csv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("afterparty")

STATIC = Path(str(resources.files("afterparty"))) / "static"

#: "I was in the room": attended, or hosted and it has already started. A party you
#: host next week has RSVPs, not people you met. `{a}` is the events alias.
_MET = (
    "({a}.role = 'attended' OR ({a}.role = 'hosting' AND coalesce({a}.starts_at, now()) <= now()))"
)
MET_E = _MET.format(a="e")
MET_E2 = _MET.format(a="e2")
MET_EVENTS = _MET.format(a="events")


#: Most people the map draws at once.
MAP_LIMIT = 8000


def met_sql(sql: str) -> str:
    """Fill the {MET_*} slots (fixed fragments, never user input)."""
    return (
        sql.replace("{MET_E2}", MET_E2)
        .replace("{MET_EVENTS}", MET_EVENTS)
        .replace("{MET_E}", MET_E)
    )


def _background_sync(stop: threading.Event) -> None:
    """BACKGROUND_SYNC: every hour, sync whoever has not synced for a day."""
    while not stop.wait(3600):
        try:
            n = sync.sync_all("schedule")
            if n:
                log.info("background sync: %s users", n)
        except Exception:
            log.exception("background sync failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not (settings.encryption_key or settings.kms_key):
        raise RuntimeError(
            "Set ENCRYPTION_KEY to store Partiful tokens. Generate one with: python3 -c "
            '"import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"'
        )
    applied = db.migrate()
    if applied:
        log.info("migrations applied: %s", ", ".join(applied))
    stop = threading.Event()
    if settings.background_sync:
        threading.Thread(target=_background_sync, args=(stop,), daemon=True).start()
    yield
    stop.set()
    sync.abandon_live_runs()
    db.close()


app = FastAPI(title="Afterparty", lifespan=lifespan, docs_url=None, redoc_url=None)


# ------------------------------------------------------------------ public
# Not /healthz: Google's front end reserves paths ending in "z" on run.app.
@app.get("/api/health")
def health():
    db.one("SELECT 1 AS ok")
    return {"ok": True}


def _connector_ids() -> list[str]:
    """EXTENSION_ID, or the unpacked connector's id from extension/manifest.json."""
    return settings.extension_ids or [connector.unpacked_id()]


@app.get("/api/config")
def public_config():
    return {
        "firebase": json.loads(settings.firebase_web_config or "{}"),
        "extensionId": _connector_ids()[0],
        "extensionIds": _connector_ids(),
        "connectorStoreUrl": settings.connector_store_url,
        "env": settings.app_env,
    }


# ------------------------------------------------------------------ me
def _me(user: dict) -> dict:
    acct = db.one(
        "SELECT partiful_uid, display_name, connected_at, last_sync_at, token_error"
        " FROM partiful_accounts WHERE user_id = %s",
        (user["id"],),
    )
    run = db.one(
        "SELECT * FROM sync_runs WHERE user_id = %s ORDER BY started_at DESC LIMIT 1",
        (user["id"],),
    )
    return {
        "user": {k: user[k] for k in ("id", "email", "name", "photo_url", "onboarded_at")},
        "partiful": acct,
        "sync": run,
    }


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return _me(user)


@app.post("/api/me/onboarded")
def onboarded(user: dict = Depends(current_user)):
    db.run(
        "UPDATE users SET onboarded_at = COALESCE(onboarded_at, now()) WHERE id = %s", (user["id"],)
    )
    return {"ok": True}


@app.delete("/api/me")
def delete_me(user: dict = Depends(current_user)):
    """Delete the account and every row that hangs off it (FK cascades)."""
    db.run("DELETE FROM users WHERE id = %s", (user["id"],))
    return {"ok": True}


# ------------------------------------------------------------------ partiful
class ConnectBody(BaseModel):
    uid: str = Field(min_length=6, max_length=128)
    refreshToken: str = Field(min_length=20, max_length=4096)
    apiKey: str = Field(pattern=r"^AIza[0-9A-Za-z_\-]{30,}$")
    displayName: str | None = Field(default=None, max_length=200)


@app.post("/api/partiful/connect")
def connect_partiful(body: ConnectBody, user: dict = Depends(current_user)):
    try:
        token = refresh(body.refreshToken, body.apiKey)
    except PartifulAuthError as exc:
        raise HTTPException(
            400, "Partiful rejected that session. Sign in on partiful.com again."
        ) from exc
    except (PartifulApiError, httpx.HTTPError) as exc:
        log.warning("connect: token check failed: %s", exc)
        raise HTTPException(502, "Partiful did not answer. Try again in a minute.") from exc
    if token.uid != body.uid:
        raise HTTPException(400, "That Partiful session belongs to a different account.")
    _forget_other_account(user["id"], token.uid)
    db.run(
        """
        INSERT INTO partiful_accounts (user_id, partiful_uid, display_name, refresh_token_enc, api_key)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            partiful_uid = EXCLUDED.partiful_uid, display_name = EXCLUDED.display_name,
            refresh_token_enc = EXCLUDED.refresh_token_enc, api_key = EXCLUDED.api_key,
            connected_at = now(), token_error = NULL
        """,
        (user["id"], token.uid, body.displayName, crypto.encrypt(token.refresh_token), body.apiKey),
    )
    run = sync.start_sync(user["id"], "connect", full=True)
    return {"displayName": body.displayName, "sync": run}


def _forget_other_account(user_id: int, partiful_uid: str) -> None:
    """Connecting a different Partiful account starts its event history fresh, so
    two accounts' guest lists never merge. Notes on people are kept."""
    current = db.one("SELECT partiful_uid FROM partiful_accounts WHERE user_id = %s", (user_id,))
    if current and current["partiful_uid"] != partiful_uid:
        db.run("DELETE FROM events WHERE user_id = %s", (user_id,))


@app.post("/api/dev/demo-connect")
def demo_connect(user: dict = Depends(current_user)):
    """Local walkthroughs only: connect a synthetic Partiful account and play a
    first sync with made-up people. 404 anywhere dev auth is off (all of prod)."""
    if not settings.dev_auth_allowed:
        raise HTTPException(404)
    _forget_other_account(user["id"], demo.DEMO_UID)
    db.run(
        """
        INSERT INTO partiful_accounts (user_id, partiful_uid, display_name, refresh_token_enc, api_key)
        VALUES (%s, %s, 'Demo Partiful', %s, 'AIzaDemo')
        ON CONFLICT (user_id) DO UPDATE SET partiful_uid = EXCLUDED.partiful_uid,
            display_name = EXCLUDED.display_name, refresh_token_enc = EXCLUDED.refresh_token_enc,
            connected_at = now(), token_error = NULL
        """,
        (user["id"], demo.DEMO_UID, crypto.encrypt("demo")),
    )
    run = sync.start_sync(user["id"], "connect", full=True)
    return {"displayName": "Demo Partiful", "sync": run}


@app.delete("/api/partiful")
def disconnect_partiful(user: dict = Depends(current_user)):
    db.run("DELETE FROM partiful_accounts WHERE user_id = %s", (user["id"],))
    return {"ok": True}


# ------------------------------------------------------------------ sync
class SyncBody(BaseModel):
    full: bool = False


@app.post("/api/sync")
def start_sync(body: SyncBody | None = None, user: dict = Depends(current_user)):
    if not db.one("SELECT 1 FROM partiful_accounts WHERE user_id = %s", (user["id"],)):
        raise HTTPException(409, "Connect Partiful first.")
    return sync.start_sync(user["id"], "manual", full=bool(body and body.full))


@app.get("/api/sync")
def sync_status(user: dict = Depends(current_user)):
    sync.active_run(user["id"])  # closes stale runs
    return db.one(
        "SELECT * FROM sync_runs WHERE user_id = %s ORDER BY started_at DESC LIMIT 1",
        (user["id"],),
    )


@app.post("/internal/sync-all", dependencies=[Depends(verify_scheduler)])
def sync_everyone():
    return {"users": sync.sync_all("schedule")}


# ------------------------------------------------------------------ data
@app.get("/api/stats")
def stats(user: dict = Depends(current_user)):
    uid = user["id"]
    s = db.one(
        met_sql("""
        WITH met AS (
            SELECT g.person_id, count(*) AS n,
                   bool_or(g.socials <> '{}'::jsonb OR g.linkedin_url IS NOT NULL) AS reachable,
                   (array_agg(g.cluster ORDER BY g.cluster = 'unknown'))[1] AS cluster
            FROM guests g JOIN events e USING (user_id, event_id)
            WHERE g.user_id = %(u)s AND {MET_E}
            GROUP BY g.person_id
        )
        SELECT
            (SELECT count(*) FROM events WHERE user_id = %(u)s AND {MET_EVENTS}) AS events_attended,
            (SELECT count(*) FROM events WHERE user_id = %(u)s AND role = 'going') AS events_upcoming,
            (SELECT count(*) FROM met) AS people,
            (SELECT count(*) FROM met WHERE reachable) AS reachable,
            (SELECT count(*) FROM met WHERE n >= 2) AS repeat,
            (SELECT count(*) FROM follow_ups WHERE user_id = %(u)s AND status = 'contacted') AS contacted,
            (SELECT coalesce(json_object_agg(cluster, c), '{}'::json)
               FROM (SELECT cluster, count(*) AS c FROM met GROUP BY cluster) x) AS clusters
        """),
        {"u": uid},
    )
    return s


@app.get("/api/events")
def list_events(user: dict = Depends(current_user)):
    return db.all_(
        """
        SELECT e.event_id AS id, e.title, e.starts_at, e.ends_at, e.timezone, e.location,
               e.image_url, e.role, e.my_rsvp, e.partiful_count, e.guest_rows, e.hidden_rows,
               e.guests_synced_at,
               count(g.person_id) AS guests,
               count(g.person_id) FILTER (WHERE g.socials <> '{}'::jsonb OR g.linkedin_url IS NOT NULL) AS reachable
        FROM events e
        LEFT JOIN guests g ON g.user_id = e.user_id AND g.event_id = e.event_id
        WHERE e.user_id = %s
        GROUP BY e.user_id, e.event_id
        ORDER BY e.starts_at DESC NULLS LAST
        """,
        (user["id"],),
    )


@app.get("/api/events/{event_id}")
def event_detail(event_id: str, user: dict = Depends(current_user)):
    uid = user["id"]
    event = db.one(
        "SELECT event_id AS id, title, starts_at, ends_at, timezone, location, image_url, role,"
        " my_rsvp, partiful_count, guest_rows, hidden_rows, guests_synced_at"
        " FROM events WHERE user_id = %s AND event_id = %s",
        (uid, event_id),
    )
    if not event:
        raise HTTPException(404, "Event not found.")
    guests = db.all_(
        met_sql("""
        SELECT g.person_id, g.name, g.username, g.avatar_url, g.bio, g.rsvp, g.plus_ones,
               g.socials, g.linkedin_url, g.cluster,
               coalesce(f.status, 'none') AS follow_up, coalesce(f.note, '') AS note,
               (SELECT count(*) FROM guests g2 JOIN events e2 USING (user_id, event_id)
                 WHERE g2.user_id = g.user_id AND g2.person_id = g.person_id
                   AND {MET_E2}) AS times_met
        FROM guests g
        LEFT JOIN follow_ups f ON f.user_id = g.user_id AND f.person_id = g.person_id
        WHERE g.user_id = %(u)s AND g.event_id = %(e)s
        ORDER BY (g.socials <> '{}'::jsonb OR g.linkedin_url IS NOT NULL) DESC,
                 (g.bio IS NOT NULL) DESC, g.name
        """),
        {"u": uid, "e": event_id},
    )
    return {"event": event, "guests": guests}


def _filters(
    q: str = "",
    cluster: str = "",
    social: SocialFilter | None = None,
    follow_up: FollowFilter | None = None,
    repeat: bool = False,
    event_id: str | None = None,
) -> PeopleFilters:
    return PeopleFilters(
        q=q, cluster=cluster, social=social, follow_up=follow_up, repeat=repeat, event_id=event_id
    )


@app.get("/api/people")
def people(
    f: PeopleFilters = Depends(_filters),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(current_user),
):
    total, rows = query_people(user["id"], f, limit=limit, offset=offset)
    return {"total": total, "people": rows}


@app.get("/api/people/map")
def people_map(f: PeopleFilters = Depends(_filters), user: dict = Depends(current_user)):
    """Everyone matching, lightly: enough to draw the map by designation."""
    total, rows = query_people(user["id"], f, limit=MAP_LIMIT, with_events=False)
    return {
        "total": total,
        "people": [
            {
                "person_id": r["person_id"],
                "name": r["name"],
                "cluster": r["cluster"],
                "times_met": r["times_met"],
                "reachable": bool(r["socials"] or r["linkedin_url"]),
                "follow_up": r["follow_up"],
                "bio": (r["bio"] or "")[:140],
            }
            for r in rows
        ],
    }


@app.get("/api/people/{person_id}")
def person(person_id: str, user: dict = Depends(current_user)):
    _, rows = query_people(user["id"], PeopleFilters(ids=[person_id]), limit=1, met_only=False)
    if not rows:
        raise HTTPException(404, "Person not found.")
    return rows[0]


@app.post("/api/people/export")
def export_people(f: PeopleFilters, user: dict = Depends(current_user)):
    """CSV of everyone matching the filters, or only the selected ids."""
    _, rows = query_people(user["id"], f, limit=None)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    name = f"afterparty-{'selected' if f.ids else 'people'}-{stamp}.csv"
    log.info("user %s exported %d people", user["id"], len(rows))
    return Response(
        to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
            "X-Afterparty-Rows": str(len(rows)),
        },
    )


class FollowUpBody(BaseModel):
    status: Literal["none", "todo", "contacted", "skip"]
    note: str = Field(default="", max_length=2000)


@app.put("/api/people/{person_id}/follow-up")
def set_follow_up(person_id: str, body: FollowUpBody, user: dict = Depends(current_user)):
    if not db.one(
        "SELECT 1 FROM guests WHERE user_id = %s AND person_id = %s LIMIT 1",
        (user["id"], person_id),
    ):
        raise HTTPException(404, "Person not found.")
    if body.status == "none" and not body.note.strip():
        db.run(
            "DELETE FROM follow_ups WHERE user_id = %s AND person_id = %s", (user["id"], person_id)
        )
    else:
        db.run(
            """
            INSERT INTO follow_ups (user_id, person_id, status, note) VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, person_id) DO UPDATE SET
                status = EXCLUDED.status, note = EXCLUDED.note, updated_at = now()
            """,
            (user["id"], person_id, body.status, body.note),
        )
    return {"ok": True}


# ------------------------------------------------------------------ spa
# This origin bridges to an extension that can read a Partiful session, so it
# gets a strict policy: no framing, our own scripts plus Firebase sign-in only.
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://apis.google.com https://www.gstatic.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: blob: https://partiful.imgix.net"
        " https://firebasestorage.googleapis.com https://*.googleusercontent.com",
        "connect-src 'self' https://*.googleapis.com",
        "frame-src 'self' https://*.firebaseapp.com https://accounts.google.com https://apis.google.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def headers(request, call_next):
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    path = request.url.path
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"  # hashed names
    elif not path.startswith("/api/") and "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-cache"  # always pick up the newest bundle names
    return response


def _looks_like_file(path: str) -> bool:
    return path.startswith("/assets/") or "." in path.rsplit("/", 1)[-1]


@app.exception_handler(404)
async def spa_fallback(request, exc):
    """Unknown app routes get the SPA so client-side routes deep-link. Missing
    files stay 404: serving HTML for a stale bundle URL shows a blank page."""
    path = request.url.path
    if (
        path.startswith(("/api/", "/internal/"))
        or _looks_like_file(path)
        or not (STATIC / "index.html").exists()
    ):
        detail = getattr(exc, "detail", "Not found")
        return JSONResponse({"detail": detail}, status_code=404)
    return FileResponse(STATIC / "index.html")


if (STATIC / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")


@app.get("/afterparty-extension.zip", include_in_schema=False)
def connector_zip():
    """The connector for this instance: its own address is the only allowed origin."""
    return Response(
        connector.instance_zip(settings.public_url),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="afterparty-extension.zip"'},
    )


@app.get("/{name}.{ext}", include_in_schema=False)
def static_file(name: str, ext: str):
    """Top-level files from the build (favicon, the extension zip…)."""
    path = (STATIC / f"{name}.{ext}").resolve()
    if path.parent != STATIC.resolve() or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/", include_in_schema=False)
def index():
    if not (STATIC / "index.html").exists():
        return JSONResponse({"detail": "Frontend not built. Run: npm --prefix web run build"})
    return FileResponse(STATIC / "index.html")
