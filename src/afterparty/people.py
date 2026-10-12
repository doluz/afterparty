"""People: one row per person across the user's events, filtered the same way
everywhere (the list, the map, the CSV export and a single person's card)."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from . import db

SocialFilter = Literal["any", "linkedin", "twitter", "instagram"]
FollowFilter = Literal["none", "todo", "contacted", "skip"]

#: "I was in the room": attended, or hosted and it has already started. A party you
#: host next week has RSVPs, not people you met.
MET = (
    "({a}.role = 'attended' OR ({a}.role = 'hosting' AND coalesce({a}.starts_at, now()) <= now()))"
)
MET_E = MET.format(a="e")

CLUSTER_LABEL = {
    "founder": "Founder",
    "investor": "Investor",
    "engineering": "Engineer",
    "product": "Product",
    "design": "Design",
    "gtm_growth": "GTM and growth",
    "other": "Other",
    "unknown": "No bio",
}


class PeopleFilters(BaseModel):
    q: str = Field(default="", max_length=200)
    cluster: str = Field(default="", max_length=40)
    social: SocialFilter | None = None
    follow_up: FollowFilter | None = None
    repeat: bool = False
    #: Only people on this event's guest list (any role, upcoming included).
    event_id: str | None = Field(default=None, max_length=128)
    #: Only these people (multi-select). Empty means "everyone matching".
    ids: list[str] = Field(default_factory=list, max_length=20000)


def query_people(
    user_id: int,
    f: PeopleFilters,
    *,
    limit: int | None = 60,
    offset: int = 0,
    with_events: bool = True,
    met_only: bool = True,
) -> tuple[int, list[dict]]:
    params: dict = {"u": user_id, "limit": limit, "offset": offset}
    where = ["g.user_id = %(u)s"]
    having = ["TRUE"]
    if f.event_id:
        # The event's guest list (even an upcoming one), with each person's history.
        where.append(f"({MET_E} OR g.event_id = %(event)s)")
        having.append("bool_or(g.event_id = %(event)s)")
        params["event"] = f.event_id
    elif met_only:
        where.append(MET_E)
    if f.ids:
        where.append("g.person_id = ANY(%(ids)s)")
        params["ids"] = list(f.ids)
    if f.q.strip():
        # Match on any of the person's rows, but aggregate over all of them.
        having.append("bool_or(g.name ILIKE %(q)s OR g.bio ILIKE %(q)s)")
        params["q"] = f"%{f.q.strip()}%"
    if f.cluster:
        having.append("(array_agg(g.cluster ORDER BY g.cluster = 'unknown'))[1] = %(cluster)s")
        params["cluster"] = f.cluster
    if f.social == "any":
        having.append("bool_or(g.socials <> '{}'::jsonb OR g.linkedin_url IS NOT NULL)")
    elif f.social == "linkedin":
        having.append("bool_or(g.socials ? 'linkedin' OR g.linkedin_url IS NOT NULL)")
    elif f.social:
        having.append("bool_or(g.socials ? %(social)s)")
        params["social"] = f.social
    if f.follow_up == "none":
        having.append("coalesce(f.status, 'none') = 'none'")
    elif f.follow_up:
        having.append("f.status = %(fu)s")
        params["fu"] = f.follow_up
    if f.repeat:
        having.append("count(*) >= 2")

    events_col = (
        "json_agg(json_build_object('id', e.event_id, 'title', e.title, 'starts_at', e.starts_at)"
        " ORDER BY e.starts_at DESC) AS events,"
        if with_events
        else ""
    )
    sql = f"""
        SELECT g.person_id,
               (array_agg(g.name ORDER BY e.starts_at DESC NULLS LAST))[1] AS name,
               (array_agg(g.username) FILTER (WHERE g.username IS NOT NULL))[1] AS username,
               (array_agg(g.avatar_url ORDER BY e.starts_at DESC NULLS LAST)
                    FILTER (WHERE g.avatar_url IS NOT NULL))[1] AS avatar_url,
               (array_agg(g.bio ORDER BY e.starts_at DESC NULLS LAST)
                    FILTER (WHERE g.bio IS NOT NULL))[1] AS bio,
               (array_agg(g.socials ORDER BY e.starts_at DESC NULLS LAST)
                    FILTER (WHERE g.socials <> '{{}}'::jsonb))[1] AS socials,
               (array_agg(g.linkedin_url) FILTER (WHERE g.linkedin_url IS NOT NULL))[1] AS linkedin_url,
               (array_agg(g.cluster ORDER BY g.cluster = 'unknown'))[1] AS cluster,
               count(*) AS times_met,
               min(e.starts_at) AS first_met,
               max(e.starts_at) AS last_met,
               {events_col}
               coalesce(f.status, 'none') AS follow_up, coalesce(f.note, '') AS note,
               count(*) OVER () AS total
        FROM guests g
        JOIN events e USING (user_id, event_id)
        LEFT JOIN follow_ups f ON f.user_id = g.user_id AND f.person_id = g.person_id
        WHERE {" AND ".join(where)}
        GROUP BY g.person_id, f.status, f.note
        HAVING {" AND ".join(having)}
        ORDER BY count(*) DESC, max(e.starts_at) DESC NULLS LAST, 2, g.person_id
        LIMIT %(limit)s OFFSET %(offset)s
    """  # noqa: S608 — only fixed fragments are interpolated; values are bound
    rows = db.all_(sql, params)
    total = rows[0]["total"] if rows else 0
    for r in rows:
        r.pop("total", None)
        r["socials"] = r["socials"] or {}
    return total, rows


# ---------------------------------------------------------------- export
COMPANY_RE = re.compile(
    r"(?:\bat\b|@)\s+([A-Z0-9][\w&.'\-]*(?:\s+(?!and\b|in\b|of\b|for\b)[A-Z0-9][\w&.'\-]*){0,3})"
)


def company_from_bio(bio: str | None) -> str:
    """A company name the person wrote after "at" or "@" ("CEO at Lumen"). A hint for
    enrichment tools, not a fact: empty when the bio doesn't say it that way."""
    if not bio:
        return ""
    m = COMPANY_RE.search(bio)
    return m.group(1).strip(" .,;") if m else ""


def _split_name(name: str) -> tuple[str, str]:
    parts = name.strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


def _cell(value) -> str:
    """Guests write their own bios. A cell that starts like a formula would run in
    Excel or Sheets, so it is defused with a leading apostrophe."""
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t") else text


def _day(ts: datetime | None) -> str:
    return ts.date().isoformat() if ts else ""


CSV_COLUMNS = [
    "name",
    "first_name",
    "last_name",
    "designation",
    "company_from_bio",
    "bio",
    "linkedin_url",
    "x_url",
    "instagram_url",
    "tiktok_url",
    "facebook_url",
    "partiful_url",
    "times_met",
    "events",
    "first_met",
    "last_met",
    "follow_up",
    "note",
    "partiful_user_id",
]


def to_csv(rows: list[dict]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(CSV_COLUMNS)
    for r in rows:
        socials = r.get("socials") or {}
        first, last = _split_name(r["name"])
        partiful = f"https://partiful.com/u/{r.get('username') or r['person_id']}"
        events = " | ".join(e["title"] for e in (r.get("events") or []) if e.get("title"))
        w.writerow(
            [
                _cell(v)
                for v in (
                    r["name"],
                    first,
                    last,
                    CLUSTER_LABEL.get(r["cluster"], r["cluster"]),
                    company_from_bio(r.get("bio")),
                    r.get("bio") or "",
                    socials.get("linkedin") or r.get("linkedin_url") or "",
                    socials.get("twitter", ""),
                    socials.get("instagram", ""),
                    socials.get("tiktok", ""),
                    socials.get("facebook", ""),
                    partiful,
                    r["times_met"],
                    events,
                    _day(r.get("first_met")),
                    _day(r.get("last_met")),
                    "" if r["follow_up"] == "none" else r["follow_up"],
                    r.get("note") or "",
                    r["person_id"],
                )
            ]
        )
    # A BOM so Excel opens accented names correctly; Sheets and Clay ignore it.
    return "﻿" + out.getvalue()
