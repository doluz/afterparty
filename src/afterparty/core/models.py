"""Normalised shapes for the data we care about."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

#: Partiful stores times in UTC. Showing the UTC calendar date makes an event at
#: 6pm Pacific read as *tomorrow's* date (01:00Z the next day), which looks like
#: an event you have not been to yet.
LOCAL_TZ = os.environ.get("PARTIFUL_TZ", "America/Los_Angeles")


def local_when(iso: str | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Render a stored UTC timestamp in the local zone."""
    if not iso:
        return ""
    try:
        stamp = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return str(iso)[:10]
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    try:
        return stamp.astimezone(ZoneInfo(LOCAL_TZ)).strftime(fmt)
    except Exception:  # unknown tz name — UTC is better than crashing
        return stamp.strftime(fmt)


@dataclass
class Event:
    id: str
    name: str = ""
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    host: str | None = None
    url: str = ""
    role: str = "unknown"  # hosting | attended | going | waitlisted | maybe | followed
    my_rsvp: str | None = None  # your own RSVP: APPROVED/GOING/WAITLISTED_FOR_APPROVAL...
    #: Partiful's own headline number. NOT the guest-list size — on a real event
    #: this read 792 while getGuests returned 215 rows.
    partiful_attended_count: int | None = None
    source: str = ""
    bucket: str = ""  # json path it was found at, e.g. $.result.data.pastEvents[0]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        d = asdict(self)
        if not include_raw:
            d.pop("raw", None)
        return d


@dataclass
class Guest:
    name: str
    partiful_username: str | None = None
    partiful_url: str | None = None
    rsvp_status: str | None = None
    plus_ones: int | None = None
    user_id: str | None = None
    #: platform -> full profile URL, e.g. {"twitter": "https://x.com/flenfrie"}
    socials: dict[str, str] = field(default_factory=dict)
    #: platform -> the raw handle exactly as Partiful stores it
    social_handles: dict[str, str] = field(default_factory=dict)
    photo_url: str | None = None
    #: public imgix thumbnail (the firebasestorage original returns 403)
    avatar_url: str | None = None
    #: profile bio / description, when the guest filled one in and it is visible
    bio: str | None = None
    #: cluster derived from the bio: founder/investor/engineering/.../other/unknown
    role: str = "unknown"
    #: LinkedIn URL the guest pasted into their own bio (self-declared)
    linkedin_url: str | None = None
    #: scored LinkedIn candidates found by searching with a signed-in session
    linkedin_matches: list[dict[str, Any]] = field(default_factory=list)
    is_host: bool = False
    event_id: str | None = None
    source: str = ""  # api:<endpoint> | dom
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        d = asdict(self)
        if not include_raw:
            d.pop("raw", None)
        return d


@dataclass
class GuestList:
    """A guest list plus what we know about its completeness.

    ``anon_rows`` matters: when you are not an approved guest or host, Partiful
    returns the right number of rows with the identities stripped out. Reporting
    that is the difference between "the event had nobody" and "you can't see them".
    """

    guests: list[Guest] = field(default_factory=list)
    anon_rows: int = 0
    raw_rows: int = 0
    sources: list[str] = field(default_factory=list)
