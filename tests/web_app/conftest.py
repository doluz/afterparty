"""Afterparty test setup: a throwaway Postgres DB and a fake Partiful.

Settings are read at import time, so the environment is set before anything
from ``afterparty`` is imported. Needs `scripts/devdb.sh start`.
"""

from __future__ import annotations

import os
from typing import ClassVar

from cryptography.fernet import Fernet

os.environ.update(
    {
        "APP_ENV": "dev",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL", "postgresql://postgres@127.0.0.1:54329/afterparty_test"
        ),
        "ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "ADMIN_EMAILS": "admin@example.com",
        "FIREBASE_PROJECT_ID": "afterparty-test",
        "PARTIFUL_DELAY": "0",
    }
)
os.environ.pop("K_SERVICE", None)

import psycopg
import pytest


def _db_up() -> bool:
    try:
        psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2).close()
        return True
    except Exception:
        return False


DB_UP = _db_up()

ME = "me-partiful-uid"


def event(eid, title, start, *, rsvp="GOING", owners=(), bucket_end=None):
    return {
        "id": eid,
        "title": title,
        "startDate": start,
        "endDate": bucket_end or start,
        "ownerIds": list(owners),
        "location": "San Francisco",
        "attendedGuestCount": 100,
        "guest": {"status": rsvp},
        "image": {"upload": {"path": f"external/user/x/{eid}"}},
    }


def guest_row(pid, name, bio=None, socials=None):
    return {
        "id": f"row-{pid}",
        "status": "GOING",
        "plusOneCount": 0,
        "userId": pid,
        "name": name,
        "user": {
            "id": pid,
            "name": name,
            "bio": {"value": bio or "", "visibility": "PUBLIC"},
            "socials": {k: {"value": v} for k, v in (socials or {}).items()},
            "photo": {"upload": {"path": f"profileImages/{pid}"}},
        },
    }


HOME = [
    ("pastEvents", event("ev-past", "Founders Rooftop", "2026-09-01T01:00:00Z")),
    (
        "pastEvents",
        event(
            "ev-wait", "Waitlisted Mixer", "2026-09-02T01:00:00Z", rsvp="WAITLISTED_FOR_APPROVAL"
        ),
    ),
    ("pastEvents", event("ev-host", "My Dinner", "2026-08-01T01:00:00Z", owners=[ME])),
    ("upcomingEvents", event("ev-next", "Demo Night", "2099-01-01T01:00:00Z", rsvp="APPROVED")),
    ("upcomingEvents", event("ev-mine-next", "My Next Party", "2099-02-01T01:00:00Z", owners=[ME])),
    ("initialPastEvents", event("ev-past", "Founders Rooftop", "2026-09-01T01:00:00Z")),
]

GUESTS = {
    "ev-past": [
        guest_row("p-ada", "Ada", "Co-founder & CEO at Analytical", {"twitter": "ada"}),
        guest_row("p-bob", "Bob", "Partner at Seed Fund"),
        {**guest_row("p-dee", "Dee", "Declined founder"), "status": "DECLINED"},
        guest_row(ME, "Me"),
        {"id": "anon", "user": None, "userId": None, "name": ""},
    ],
    "ev-host": [guest_row("p-ada", "Ada", "Co-founder & CEO at Analytical", {"twitter": "ada"})],
    "ev-next": [guest_row("p-cy", "Cy", "Software engineer", {"linkedin": "cy-dev"})],
    # RSVPs to a party you host next year are not people you met.
    "ev-mine-next": [guest_row("p-rsvp", "Riley", "Coming to my party")],
}


class FakePartiful:
    """Stands in for PartifulClient: same surface, canned payloads."""

    calls: ClassVar[list[str]] = []
    broken: ClassVar[set[str]] = set()

    def __init__(self, refresh_token, api_key, delay=0.3, on_rotate=None):
        from afterparty.partiful_api import Token

        self.token = Token("id", refresh_token, ME, 9e18)

    @property
    def uid(self):
        return ME

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def home_events(self):
        return HOME

    def guests(self, event_id, hosting=False):
        from afterparty.partiful_api import PartifulApiError

        FakePartiful.calls.append(event_id)
        if event_id in FakePartiful.broken:
            raise PartifulApiError(f"getGuests -> HTTP 500 for {event_id}")
        return GUESTS.get(event_id, [])


@pytest.fixture
def client(monkeypatch):
    if not DB_UP:
        pytest.skip("local Postgres not running (scripts/devdb.sh start)")
    from fastapi.testclient import TestClient

    from afterparty import app as app_mod
    from afterparty import db, sync
    from afterparty.partiful_api import Token

    monkeypatch.setattr(sync, "PartifulClient", FakePartiful)
    monkeypatch.setattr(app_mod, "refresh", lambda rt, key: Token("id", rt, ME, 9e18))
    # Syncs run inline in tests so assertions see their results.
    real_start = sync.start_sync
    monkeypatch.setattr(
        sync,
        "start_sync",
        lambda uid, trig, full=False, background=True: real_start(uid, trig, full, False),
    )
    FakePartiful.calls = []
    FakePartiful.broken = set()
    with TestClient(app_mod.app) as c:
        db.run(
            "TRUNCATE users, partiful_accounts, events, guests, follow_ups, sync_runs"
            " RESTART IDENTITY CASCADE"
        )
        yield c


def as_(email):
    return {"Authorization": f"Dev {email}"}
