"""Turn Partiful API payloads into events and guests.

Partiful's web app talks to ``api.partiful.com``. These helpers read the rows
that its endpoints return (home-page event lists, guest lists) and map them to
:class:`~afterparty.core.models.Event` and :class:`~afterparty.core.models.Guest`.
Every field is optional on Partiful's side, so every reader degrades to ``None``.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

from .models import Event, Guest
from .roles import infer_role, linkedin_from_bio

BASE = "https://partiful.com"

NAME_KEYS = ("name", "title", "eventName", "displayName", "fullName", "firstName")
DATE_KEYS = (
    "startDate",
    "endDate",
    "startTime",
    "endTime",
    "eventDate",
    "startDateMs",
    "date",
    "startsAt",
)
LOCATION_KEYS = ("location", "address", "venue", "locationName", "place")
RSVP_KEYS = (
    "rsvp",
    "rsvpStatus",
    "rsvpType",
    "status",
    "guestStatus",
    "plusOnes",
    "checkedIn",
    "invitedBy",
    "inviterId",
    "guestCount",
    "email",
    "phone",
)
EVENT_MARKERS = set(DATE_KEYS) | {"hosts", "hostsById", "eventId", "poster", "theme"}
#: Only these endpoints carry guest rows. Everything else that merely contains a
#: nested `user` (comments, hosts, mutuals) would inflate the list.
GUEST_ENDPOINTS = ("getGuests", "getEventGuests", "getMutualGuests")

#: Most informative first. An event seen in the past-events bucket is known to be
#: in the past; the same event re-served by getEventsByIds carries no such signal.
SOURCE_PRIORITY = (
    "getMyPastEventsForHomePage",
    "getMyUpcomingEventsForHomePage",
    "getMyFollowedEvents",
    "getMySavedEvents",
    "getCreatedCards",
    "getEventsByIds",
    "getMutualGuests",
)


#: Only these endpoints describe *your* events. Discover/explore payloads also
#: contain event-shaped objects (recommendations, nearby parties) and would
#: otherwise show up as events you attended.
MY_EVENT_ENDPOINTS = (
    "getMyPastEventsForHomePage",
    "getMyUpcomingEventsForHomePage",
    "getMyFollowedEvents",
    "getMySavedEvents",
    "getCreatedCards",
    "getEventsByIds",
    "getCohostRequestedEvents",
    "getMutualGuests",
)

#: Bucket names inside those payloads, which state the role outright.
BUCKET_ROLES = {
    "pastevents": "attended",
    "attendedevents": "attended",
    "upcomingevents": "upcoming",
    "hostedevents": "hosting",
    "createdcards": "hosting",
}


def _bucket_role(row: dict) -> str | None:
    path = str(row.get("__path") or "").lower()
    for bucket, role in BUCKET_ROLES.items():
        if bucket in path:
            return role
    return None


#: Your own RSVP, straight off the event object. This is the difference between
#: "I was there" and "I asked to be and never got in" — the guest list is visible
#: for the first and hidden for the second.
CONFIRMED_RSVPS = {"APPROVED", "GOING", "YES", "ACCEPTED", "CHECKED_IN"}
NOT_ADMITTED_RSVPS = {"WAITLISTED_FOR_APPROVAL", "PENDING_APPROVAL", "WAITLISTED", "REJECTED"}


def _my_rsvp(row: dict) -> str | None:
    guest = row.get("guest")
    if isinstance(guest, dict):
        status = guest.get("status")
        if isinstance(status, str) and status:
            return status
    for key in ("myRsvp", "rsvpStatus", "userRsvpStatus"):
        val = row.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _in_past(iso: str | None) -> bool:
    if not iso:
        return False
    try:
        stamp = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp < datetime.now(UTC)


def _in_future(iso: str | None) -> bool:
    if not iso:
        return False
    try:
        stamp = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp > datetime.now(UTC)


def _source_rank(row: dict) -> int:
    src = str(row.get("__source") or "")
    try:
        return SOURCE_PRIORITY.index(src)
    except ValueError:
        return len(SOURCE_PRIORITY)


def _has_any(d: dict, keys) -> bool:
    return any(k in d and d[k] not in (None, "", [], {}) for k in keys)


def _first(d: dict, keys) -> Any:
    for k in keys:
        if d.get(k) not in (None, "", [], {}):
            return d[k]
    return None


def _looks_like_event(d: dict) -> bool:
    return isinstance(d, dict) and "id" in d and _has_any(d, NAME_KEYS) and _has_any(d, DATE_KEYS)


def _rows_of_endpoint(data: Any) -> list[dict]:
    """Guest data arrives as a list of rows, or as a map that hides them.

    ``getMutualGuests`` returns ``{"totalCount": 2, "guests": [...]}``.
    """
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        sub = data.get("guests")
        if isinstance(sub, list):
            return [r for r in sub if isinstance(r, dict)]
        if isinstance(sub, dict):
            return [r for r in sub.values() if isinstance(r, dict)]
    return []


def _guest_name(row: dict) -> tuple[str, dict | None]:
    """A guest's display name, plus the person object it came from.

    Guest rows carry the person inline under ``user`` (null when Partiful is
    hiding identities) and sometimes a plain ``name`` string.
    """
    person = row.get("user") if isinstance(row.get("user"), dict) else None
    name = _longest_text(person) if person else ""
    if not name:
        name = (row.get("name") or "").strip() if isinstance(row.get("name"), str) else ""
    return name, person


#: Partiful exposes handles, not URLs, and only for the platforms it supports.
#: LinkedIn is not one of them — there is no field for it anywhere in the payload.
SOCIAL_URL_TEMPLATES = {
    "twitter": "https://x.com/{handle}",
    "instagram": "https://instagram.com/{handle}",
    "snapchat": "https://snapchat.com/add/{handle}",
    "tiktok": "https://tiktok.com/@{handle}",
    "facebook": "https://facebook.com/{handle}",
    "venmo": "https://venmo.com/u/{handle}",
    "linkedin": "https://linkedin.com/in/{handle}",
}


def _clean_handle(value: str) -> str | None:
    """Partiful stores whatever the user typed. Keep things that look like a
    handle; drop the rest rather than emitting a link that goes nowhere."""
    handle = value.strip().lstrip("@").strip()
    if not handle:
        return None
    if any(ch.isspace() for ch in handle):
        return None
    if len(handle) > 60:
        return None
    return handle


def _bio_of(person: dict | None) -> str | None:
    """Profile description. Partiful wraps it as ``{value, visibility}`` and
    leaves the value empty when the guest hasn't filled one in."""
    bio = (person or {}).get("bio")
    if isinstance(bio, dict):
        value = bio.get("value")
        return value.strip() if isinstance(value, str) and value.strip() else None
    if isinstance(bio, str) and bio.strip():
        return bio.strip()
    return None


IMGIX = "https://partiful.imgix.net"


def _avatar_url(person: dict | None, width: int = 96) -> str | None:
    """Public thumbnail via Partiful's imgix proxy.

    The firebasestorage original returns 403 without the app's own auth; imgix
    serves the same image publicly, which is exactly what the web app renders.
    """
    photo = (person or {}).get("photo")
    if not isinstance(photo, dict):
        return None
    upload = photo.get("upload")
    path = (upload.get("path") if isinstance(upload, dict) else None) or photo.get("path")
    if not path and photo.get("name"):
        path = f"profileImages/{photo['name']}"
    if not path and isinstance(photo.get("url"), str):
        match = re.search(r"/o/([^?&]+)", photo["url"])
        if match:
            path = unquote(match.group(1))
    if not path:
        return None
    return f"{IMGIX}/{str(path).strip('/')}_thumbnail?fit=clip&w={width}&auto=format&dpr=2"


def _socials_of(person: dict | None) -> tuple[dict[str, str], dict[str, str]]:
    """Return (platform -> url, platform -> raw handle) from a user object.

    Each entry looks like ``{"value": "flenfrie", "visibility": "MUTUALS"}``.
    """
    urls: dict[str, str] = {}
    handles: dict[str, str] = {}
    for platform, entry in ((person or {}).get("socials") or {}).items():
        raw = entry.get("value") if isinstance(entry, dict) else entry
        if not isinstance(raw, str) or not raw.strip():
            continue
        value = raw.strip()
        if value.lower().startswith("http"):
            urls[platform] = value
            handles[platform] = value.rstrip("/").split("/")[-1]
            continue
        handle = _clean_handle(value)
        if not handle:
            continue
        handles[platform] = handle
        template = SOCIAL_URL_TEMPLATES.get(platform)
        if template:
            urls[platform] = template.format(handle=handle)
    return urls, handles


def _longest_text(node) -> str:
    """Best-effort first plausible name from a raw dict."""
    if isinstance(node, dict):
        for k in NAME_KEYS:
            v = node.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def classify_event(ev: Event, self_user_id: str | None) -> str:
    """Role in priority order: hosting, your own RSVP, then the payload bucket.

    RSVP must beat the bucket: three events in the past-events list are
    WAITLISTED_FOR_APPROVAL — a past event you never got into is not one you
    attended, and its guest list stays hidden.
    """
    owners = ev.raw.get("ownerIds") or []
    if self_user_id and isinstance(owners, list) and self_user_id in owners:
        return "hosting"
    hosts = ev.raw.get("hosts") or ev.raw.get("hostsById") or {}
    if self_user_id and self_user_id in json.dumps(hosts)[:8000]:
        return "hosting"

    bucket = _bucket_role({"__path": ev.bucket})
    rsvp = (ev.my_rsvp or "").upper()
    if rsvp in CONFIRMED_RSVPS:
        # A future-dated event is "going", never "attended", whatever bucket
        # Partiful filed it under: one live event dated tomorrow arrived in
        # the past-events payload with an APPROVED RSVP, and trusting the
        # bucket would have put an event you haven't been to in the report.
        if _in_future(ev.start_date):
            return "going"
        if bucket == "attended" or _in_past(ev.start_date):
            return "attended"
        return "going"
    if rsvp in NOT_ADMITTED_RSVPS:
        return "waitlisted" if "WAITLIST" in rsvp else "pending"
    if rsvp == "MAYBE":
        return "maybe"
    if bucket == "hosting":
        return "hosting"

    src = (ev.source or "").lower()
    if "follow" in src:
        return "followed"
    if "saved" in src:
        return "saved"
    if bucket in ("attended", "upcoming"):
        return bucket
    if "past" in src:
        return "attended"
    if "upcoming" in src:
        return "upcoming"
    return "unknown"


def event_from_row(row: dict) -> Event:
    """One raw Partiful event object -> Event. ``__source``/``__path`` are the
    recorder's tags (endpoint and JSON path), used for the role bucket."""
    name = _first(row, NAME_KEYS) or ""
    url = row.get("url") or row.get("eventUrl")
    return Event(
        id=str(row["id"]),
        name=str(name) if isinstance(name, str) else "",
        start_date=_as_str(_first(row, DATE_KEYS)),
        end_date=_as_str(_first(row, ("endDate", "endTime"))),
        location=_as_str(_first(row, LOCATION_KEYS)),
        host=_host_of(row),
        url=str(url)
        if isinstance(url, str) and url.startswith("http")
        else f"{BASE}/e/{row['id']}",
        my_rsvp=_my_rsvp(row),
        partiful_attended_count=_as_int(
            _first(row, ("attendedGuestCount", "guestCount", "goingCount"))
        ),
        source=row.get("__source", ""),
        bucket=row.get("__path", ""),
        raw={k: v for k, v in row.items() if not k.startswith("__")},
    )


def guests_from_rows(rows: list[dict], event_id: str) -> list[Guest]:
    out: list[Guest] = []
    for row in rows:
        name, person = _guest_name(row)
        if not name:
            continue  # anonymous row: Partiful hides it unless you're approved
        pid = (person or {}).get("id") or row.get("userId")
        username = (person or {}).get("username") or row.get("username")
        url = f"{BASE}/u/{username}" if username else (f"{BASE}/u/{pid}" if pid else None)
        socials, handles = _socials_of(person)
        out.append(
            Guest(
                name=name,
                partiful_username=str(username) if username else None,
                partiful_url=url,
                rsvp_status=_as_str(
                    _first(row, ("status", "rsvpStatus", "rsvp", "rsvpType", "guestStatus"))
                ),
                plus_ones=_as_int(_first(row, ("plusOneCount", "plusOnes", "guestCount"))),
                user_id=str(pid) if pid else None,
                socials=socials,
                social_handles=handles,
                photo_url=((person or {}).get("photo") or {}).get("url"),
                avatar_url=_avatar_url(person),
                bio=_bio_of(person),
                role=infer_role(_bio_of(person)),
                linkedin_url=linkedin_from_bio(_bio_of(person)),
                event_id=event_id,
                source=f"api:{row.get('__source', '')}",
                raw={k: v for k, v in row.items() if not k.startswith("__")},
            )
        )
    return out


# ---------------------------------------------------------------- helpers
def _normalise_event_id(value: str) -> str:
    value = value.strip()
    m = re.search(r"/e/([A-Za-z0-9_-]+)", value)
    if m:
        return m.group(1)
    return value.split("?")[0].rstrip("/").split("/")[-1]


def _as_str(v: Any) -> str | None:
    if v is None or isinstance(v, (dict, list)):
        return None
    return str(v)


def _as_int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _host_of(row: dict) -> str | None:
    hosts = row.get("hosts")
    if isinstance(hosts, list) and hosts:
        h = hosts[0]
        if isinstance(h, dict):
            return _longest_text(h) or _as_str(h.get("username") or h.get("id"))
        return _as_str(h)
    return _as_str(row.get("hostName") or row.get("hostUsername"))


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    """Collapse duplicate guest rows (the UI often fetches the same page twice)."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = str(row.get("id") or row.get("userId") or "")
        if not key:
            key = f"{row.get('name', '')}|{row.get('rsvpDate', '')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _dedupe_guests(guests: list[Guest]) -> list[Guest]:
    seen: set[str] = set()
    out: list[Guest] = []
    for g in guests:
        key = (g.user_id or g.partiful_username or g.name).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(g)
    return sorted(out, key=lambda g: g.name.lower())
