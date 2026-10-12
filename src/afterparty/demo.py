"""Synthetic events and people, for local UI work and onboarding walkthroughs.

Nothing here is real: every name, bio and handle is generated. Only reachable
when dev auth is allowed (never on Cloud Run). A "demo" Partiful account plays
the same progress a real first sync reports, so the onboarding animation runs.
"""

from __future__ import annotations

import random
import time
from datetime import UTC, datetime, timedelta

from psycopg.types.json import Jsonb

from . import db

DEMO_UID = "demo"

FIRST = (
    "Avery Blake Casey Devon Emery Finley Gray Harper Indy Jules Kai Logan Morgan Noel Oakley "
    "Parker Quinn Reese Sage Tatum Umi Val Wren Yael Zion Ari Bo Cam Dara Eli"
).split()
LAST = (
    "Okafor Lindqvist Moreau Tanaka Reyes Novak Adeyemi Castillo Fischer Haddad Ivanova Kowalski "
    "Laurent Mbeki Nakamura Ortega Petrov Quintero Rossi Sato Usman Varga Weiss Xu Yilmaz Zamora"
).split()
BIOS = [
    ("founder", "Co-founder & CEO at {co}. Building {thing}."),
    ("founder", "Founder, {co} (YC W26). Previously eng at a big tech co."),
    ("investor", "Partner at {co} Ventures. Pre-seed and seed, {thing}."),
    ("investor", "Angel investor. Writing first checks into {thing}."),
    ("engineering", "Software engineer at {co}. Into {thing}."),
    ("engineering", "Founding engineer, {co}. Rust, Go and too much coffee."),
    ("product", "Product manager at {co}, working on {thing}."),
    ("design", "Product designer. Making {thing} feel simple."),
    ("gtm_growth", "Head of growth at {co}. Sales, partnerships, {thing}."),
    ("other", "Here for the snacks and the conversations."),
    ("unknown", None),
    ("unknown", None),
]
COS = "Lumen Fieldnote Parcel Tidewater Quill Northwind Kiln Halyard Brightline Saltbox".split()
THINGS = [
    "voice AI agents",
    "developer tools",
    "climate hardware",
    "fintech infra",
    "meeting intelligence",
    "robotics",
    "healthcare AI",
    "creator tools",
]
EVENTS = [
    "Demos After Dark w/ Friends",
    "Founders and Funders Rooftop Party #SFTechWeek",
    "Oktoberfest Block Party",
    "Voice AI Builders Night",
    "Seed Investor Breakfast",
    "Hot Sauce Pitch Competition",
    "Infra Founders Dinner",
    "Agent Economy After Party",
    "Design x AI Salon",
    "Late Night Hack & Tacos",
]


def _people(rng: random.Random, n: int = 320) -> list[dict]:
    out = []
    for i in range(n):
        cluster, bio = rng.choice(BIOS)
        first, last = rng.choice(FIRST), rng.choice(LAST)
        socials = {}
        if rng.random() < 0.35:
            socials["twitter"] = f"https://x.com/{first.lower()}{i}"
        if rng.random() < 0.25:
            socials["instagram"] = f"https://instagram.com/{first.lower()}.{i}"
        if rng.random() < 0.2:
            socials["linkedin"] = f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{i}"
        out.append(
            {
                "id": f"demo-{i}",
                "name": f"{first} {last}",
                "cluster": cluster,
                "bio": bio.format(co=rng.choice(COS), thing=rng.choice(THINGS)) if bio else None,
                "socials": socials,
            }
        )
    return out


def _progress(run_id: int | None, **fields) -> None:
    if run_id is None:
        return
    sets = ", ".join(f"{k} = %({k})s" for k in fields)
    db.run(f"UPDATE sync_runs SET {sets} WHERE id = %(id)s", {**fields, "id": run_id})  # noqa: S608


def seed(user_id: int, run_id: int | None = None, delay: float = 0.0, seed_value: int = 7) -> None:
    """Replace the user's events and guests with the synthetic set."""
    rng = random.Random(seed_value)  # noqa: S311 — made-up data, not security
    people = _people(rng)
    db.run("DELETE FROM events WHERE user_id = %s", (user_id,))
    now = datetime.now(UTC)
    _progress(run_id, phase="events")
    time.sleep(delay * 2)
    plans = []
    for k, title in enumerate(EVENTS):
        upcoming = k < 2
        start = (
            now + timedelta(days=2 + k) if upcoming else now - timedelta(days=3 * k + 1, hours=k)
        )
        eid = f"demo-ev-{k}"
        hidden = k == 4
        db.run(
            """
            INSERT INTO events (user_id, event_id, title, starts_at, ends_at, timezone, location,
                                role, my_rsvp, partiful_count)
            VALUES (%s, %s, %s, %s, %s, 'America/Los_Angeles', 'San Francisco', %s, 'APPROVED', %s)
            """,
            (
                user_id,
                eid,
                title,
                start,
                start + timedelta(hours=3),
                "going" if upcoming else "attended",
                200,
            ),
        )
        plans.append((eid, hidden))
    _progress(run_id, phase="guests", events_total=len(plans))
    total = 0
    for i, (eid, hidden) in enumerate(plans, 1):
        time.sleep(delay)
        guests = [] if hidden else rng.sample(people, rng.randint(25, 90))
        with db.conn() as c, c.transaction(), c.cursor() as cur:
            cur.executemany(
                "INSERT INTO guests (user_id, event_id, person_id, name, bio, rsvp, socials,"
                " cluster) VALUES (%s, %s, %s, %s, %s, 'GOING', %s, %s) ON CONFLICT DO NOTHING",
                [
                    (user_id, eid, p["id"], p["name"], p["bio"], Jsonb(p["socials"]), p["cluster"])
                    for p in guests
                ],
            )
            cur.execute(
                "UPDATE events SET guest_rows = %s, hidden_rows = %s, guests_synced_at = now()"
                " WHERE user_id = %s AND event_id = %s",
                (len(guests), 140 if hidden else 0, user_id, eid),
            )
        total += len(guests)
        _progress(run_id, events_done=i, guests=total)
    db.run(
        "UPDATE partiful_accounts SET last_sync_at = now(), token_error = NULL WHERE user_id = %s",
        (user_id,),
    )
    _progress(run_id, status="ok", phase="done", finished_at=datetime.now(UTC))
