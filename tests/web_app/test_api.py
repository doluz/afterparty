"""API behaviour end to end against a real Postgres, with Partiful faked."""

from __future__ import annotations

from .conftest import FakePartiful, as_

CONNECT = {
    "uid": "me-partiful-uid",
    "refreshToken": "r" * 40,
    "apiKey": "AIza" + "x" * 35,
    "displayName": "Me",
}


def approve(client, email):
    client.get("/api/me", headers=as_(email))
    users = client.get("/api/admin/users", headers=as_("admin@example.com")).json()
    uid = next(u["id"] for u in users if u["email"] == email)
    r = client.post(
        f"/api/admin/users/{uid}", json={"status": "approved"}, headers=as_("admin@example.com")
    )
    assert r.status_code == 200


def test_signin_required(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_new_user_waits_for_approval(client):
    me = client.get("/api/me", headers=as_("guest@example.com")).json()
    assert me["user"]["status"] == "pending"
    assert client.get("/api/events", headers=as_("guest@example.com")).status_code == 403
    assert client.get("/api/admin/users", headers=as_("guest@example.com")).status_code == 403


def test_admin_email_is_auto_approved(client):
    me = client.get("/api/me", headers=as_("admin@example.com")).json()
    assert me["user"]["status"] == "approved"
    assert me["user"]["role"] == "admin"


def test_connect_sync_and_browse(client):
    approve(client, "sid@example.com")
    h = as_("sid@example.com")
    r = client.post("/api/partiful/connect", json=CONNECT, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["sync"]["id"]

    me = client.get("/api/me", headers=h).json()
    assert me["partiful"]["display_name"] == "Me"
    assert me["sync"]["status"] == "ok", me["sync"]
    assert "refresh" not in str(me).lower()  # the token never comes back

    # Guest lists pulled only for events you were (or will be) in the room for.
    assert sorted(FakePartiful.calls) == ["ev-host", "ev-mine-next", "ev-next", "ev-past"]

    events = {e["id"]: e for e in client.get("/api/events", headers=h).json()}
    assert (
        events["ev-past"]["guests"] == 2
    )  # you, the declined guest and the anonymous row excluded
    assert events["ev-past"]["hidden_rows"] == 1
    assert events["ev-wait"]["guests"] == 0

    stats = client.get("/api/stats", headers=h).json()
    assert stats["events_attended"] == 2
    assert stats["events_upcoming"] == 1
    assert stats["people"] == 2  # Ada, Bob (Cy is at a future event)
    assert stats["repeat"] == 1  # Ada was at two of your events
    assert stats["clusters"]["founder"] == 1

    people = client.get("/api/people", headers=h).json()
    assert people["total"] == 2
    ada = people["people"][0]
    assert ada["name"] == "Ada" and ada["times_met"] == 2
    assert ada["socials"]["twitter"] == "https://x.com/ada"

    r = client.put(
        f"/api/people/{ada['person_id']}/follow-up",
        json={"status": "contacted", "note": "met at rooftop"},
        headers=h,
    )
    assert r.status_code == 200
    contacted = client.get("/api/people?follow_up=contacted", headers=h).json()
    assert [p["name"] for p in contacted["people"]] == ["Ada"]
    assert client.get("/api/people?social=any", headers=h).json()["total"] == 1
    assert client.get("/api/people?q=seed", headers=h).json()["people"][0]["name"] == "Bob"

    detail = client.get("/api/events/ev-past", headers=h).json()
    assert {g["name"] for g in detail["guests"]} == {"Ada", "Bob"}


def test_one_broken_event_does_not_sink_the_sync(client):
    approve(client, "partial@example.com")
    h = as_("partial@example.com")
    FakePartiful.broken = {"ev-host"}
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    run = client.get("/api/sync", headers=h).json()
    assert run["status"] == "ok"
    assert "My Dinner" in run["error"]
    events = {e["id"]: e for e in client.get("/api/events", headers=h).json()}
    assert events["ev-past"]["guests"] == 2  # still pulled


def test_users_cannot_see_each_other(client):
    approve(client, "a@example.com")
    approve(client, "b@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=as_("a@example.com"))
    assert client.get("/api/events", headers=as_("b@example.com")).json() == []
    assert client.get("/api/events/ev-past", headers=as_("b@example.com")).status_code == 404
    assert (
        client.put(
            "/api/people/p-ada/follow-up", json={"status": "skip"}, headers=as_("b@example.com")
        ).status_code
        == 404
    )


def test_delete_me_removes_everything(client):
    approve(client, "gone@example.com")
    h = as_("gone@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    assert client.delete("/api/me", headers=h).status_code == 200
    me = client.get("/api/me", headers=h).json()  # signs in again as a fresh, pending user
    assert me["user"]["status"] == "pending" and me["partiful"] is None


def test_connect_rejects_bad_key(client):
    approve(client, "k@example.com")
    bad = {**CONNECT, "apiKey": "not-a-key"}
    assert (
        client.post("/api/partiful/connect", json=bad, headers=as_("k@example.com")).status_code
        == 422
    )


def test_scheduler_endpoint_needs_oidc(client):
    assert client.post("/internal/sync-all").status_code == 401


def test_future_hosted_event_is_not_people_met(client):
    approve(client, "host@example.com")
    h = as_("host@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    stats = client.get("/api/stats", headers=h).json()
    assert stats["events_attended"] == 2  # the 2099 party you host is not counted
    names = {p["name"] for p in client.get("/api/people", headers=h).json()["people"]}
    assert "Riley" not in names
    # ...but its guest list is still there to look at before the night.
    detail = client.get("/api/events/ev-mine-next", headers=h).json()
    assert [g["name"] for g in detail["guests"]] == ["Riley"]


def test_switching_partiful_accounts_starts_fresh(client):
    from afterparty import db

    approve(client, "switch@example.com")
    h = as_("switch@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    uid = client.get("/api/me", headers=h).json()["user"]["id"]
    db.run("UPDATE partiful_accounts SET partiful_uid = 'someone-else' WHERE user_id = %s", (uid,))
    db.run(
        "INSERT INTO events (user_id, event_id, title, role)"
        " VALUES (%s, 'old-acct-ev', 'Old', 'attended')",
        (uid,),
    )
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    ids = {e["id"] for e in client.get("/api/events", headers=h).json()}
    assert "old-acct-ev" not in ids and "ev-past" in ids


def test_note_without_a_status_is_kept(client):
    approve(client, "notes@example.com")
    h = as_("notes@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    r = client.put(
        "/api/people/p-bob/follow-up",
        json={"status": "none", "note": "ask about fund II"},
        headers=h,
    )
    assert r.status_code == 200
    bob = next(
        p for p in client.get("/api/people", headers=h).json()["people"] if p["name"] == "Bob"
    )
    assert bob["follow_up"] == "none" and bob["note"] == "ask about fund II"
    assert client.get("/api/people?follow_up=none", headers=h).json()["total"] == 2


def test_one_running_sync_per_user(client):
    import psycopg
    import pytest as _pytest

    from afterparty import db

    approve(client, "once@example.com")
    uid = client.get("/api/me", headers=as_("once@example.com")).json()["user"]["id"]
    db.run("INSERT INTO sync_runs (user_id, trigger) VALUES (%s, 'manual')", (uid,))
    with _pytest.raises(psycopg.errors.UniqueViolation):
        db.run("INSERT INTO sync_runs (user_id, trigger) VALUES (%s, 'manual')", (uid,))


def test_dev_header_refused_on_cloud_run(client, monkeypatch):
    monkeypatch.setenv("K_SERVICE", "afterparty")
    assert client.get("/api/me", headers=as_("admin@example.com")).status_code == 401


def test_security_headers_and_asset_404(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert client.get("/assets/index-gone.js").status_code == 404


def test_new_access_request_pings_admin_once(client, monkeypatch):
    from afterparty import notify

    pings = []
    monkeypatch.setattr(notify, "access_requested", lambda email, name: pings.append(email))
    client.get("/api/me", headers=as_("newcomer@example.com"))
    client.get("/api/me", headers=as_("newcomer@example.com"))
    client.get("/api/me", headers=as_("admin@example.com"))  # admins are approved, no ping
    assert pings == ["newcomer@example.com"]


def test_public_brand_files_are_served(client):
    from afterparty.app import STATIC

    if not (STATIC / "index.html").exists():
        import pytest

        pytest.skip("frontend not built")
    for path in ("/privacy", "/manifest.webmanifest", "/og.png", "/icon-192.png"):
        assert client.get(path).status_code == 200, path


def _csv_rows(text):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def test_export_everyone_filtered_and_selected(client):
    approve(client, "export@example.com")
    h = as_("export@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=h)

    r = client.post("/api/people/export", json={}, headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = _csv_rows(r.text)
    assert [x["name"] for x in rows] == ["Ada", "Bob"]
    ada = rows[0]
    assert ada["first_name"] == "Ada" and ada["designation"] == "Founder"
    assert ada["company_from_bio"] == "Analytical"
    assert ada["x_url"] == "https://x.com/ada" and ada["times_met"] == "2"
    assert ada["partiful_url"].startswith("https://partiful.com/u/")

    # Any filter applies to the export exactly as to the list.
    rows = _csv_rows(client.post("/api/people/export", json={"social": "any"}, headers=h).text)
    assert [x["name"] for x in rows] == ["Ada"]
    # Multi-select exports only the chosen people.
    rows = _csv_rows(client.post("/api/people/export", json={"ids": ["p-bob"]}, headers=h).text)
    assert [x["name"] for x in rows] == ["Bob"]
    # One event's guest list, including an upcoming one.
    rows = _csv_rows(
        client.post("/api/people/export", json={"event_id": "ev-next"}, headers=h).text
    )
    assert [x["name"] for x in rows] == ["Cy"]


def test_export_defuses_spreadsheet_formulas():
    from afterparty.people import to_csv

    row = {
        "person_id": "p1",
        "name": '=HYPERLINK("http://evil")',
        "username": None,
        "bio": "+1 cmd",
        "socials": {},
        "linkedin_url": None,
        "cluster": "other",
        "times_met": 1,
        "events": [],
        "first_met": None,
        "last_met": None,
        "follow_up": "none",
        "note": "",
    }
    out = _csv_rows(to_csv([row]))[0]
    assert out["name"].startswith("'=") and out["bio"].startswith("'+")


def test_export_and_map_are_per_user(client):
    approve(client, "owner@example.com")
    approve(client, "other@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=as_("owner@example.com"))
    other = as_("other@example.com")
    assert (
        _csv_rows(client.post("/api/people/export", json={"ids": ["p-ada"]}, headers=other).text)
        == []
    )
    assert client.get("/api/people/map", headers=other).json()["total"] == 0
    assert client.get("/api/people/p-ada", headers=other).status_code == 404


def test_map_and_person_detail(client):
    approve(client, "mapper@example.com")
    h = as_("mapper@example.com")
    client.post("/api/partiful/connect", json=CONNECT, headers=h)
    m = client.get("/api/people/map", headers=h).json()
    assert m["total"] == 2
    by = {p["name"]: p for p in m["people"]}
    assert by["Ada"]["cluster"] == "founder" and by["Ada"]["reachable"] is True
    # "Partner at Seed Fund": bare "partner" is deliberately not an investor signal.
    assert by["Bob"]["cluster"] == "other" and by["Bob"]["times_met"] == 1
    ada = client.get("/api/people/p-ada", headers=h).json()
    assert ada["name"] == "Ada" and len(ada["events"]) == 2
