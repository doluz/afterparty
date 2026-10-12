"""Self-hosting settings: cron secret, the email allowlist, the per-instance connector."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace

from .conftest import as_


def test_cron_secret_runs_the_daily_sync(client, monkeypatch):
    from afterparty import auth

    monkeypatch.setattr(auth, "settings", replace(auth.settings, cron_secret="s3cret-value"))
    wrong = {"Authorization": "Bearer nope"}
    assert client.post("/internal/sync-all", headers=wrong).status_code == 401
    ok = client.post("/internal/sync-all", headers={"Authorization": "Bearer s3cret-value"})
    assert ok.status_code == 200
    assert "users" in ok.json()


def test_allowlist_keeps_a_shared_instance_private(client, monkeypatch):
    from afterparty import auth

    rules = ["friend@example.com", "@team.example.com"]
    monkeypatch.setattr(auth, "settings", replace(auth.settings, allowed_emails=rules))
    assert client.get("/api/me", headers=as_("friend@example.com")).status_code == 200
    assert client.get("/api/me", headers=as_("ana@team.example.com")).status_code == 200
    r = client.get("/api/me", headers=as_("stranger@example.com"))
    assert r.status_code == 403
    assert "private" in r.json()["detail"]


def test_empty_allowlist_lets_everyone_in(client):
    assert client.get("/api/me", headers=as_("anyone@example.com")).status_code == 200


def test_connector_zip_allows_only_this_instance(client, monkeypatch):
    from afterparty import app as app_mod

    url = "https://afterparty.example.com"
    monkeypatch.setattr(app_mod, "settings", replace(app_mod.settings, public_url=url))
    r = client.get("/afterparty-extension.zip")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    manifest = json.loads(z.read("afterparty-extension/manifest.json"))
    assert manifest["externally_connectable"]["matches"] == [f"{url}/*"]
    assert manifest["key"]  # same id as the unpacked build, so the app can find it
    assert f"{url}/onboarding" in z.read("afterparty-extension/popup.html").decode()


def test_store_build_has_no_key_and_files_at_root():
    from afterparty.connector import build_zip

    z = zipfile.ZipFile(io.BytesIO(build_zip("https://a.example.com", store=True)))
    assert "manifest.json" in z.namelist()
    assert "key" not in json.loads(z.read("manifest.json"))


def test_local_instance_keeps_localhost_origins():
    from afterparty.connector import origins_for

    assert origins_for("http://localhost:8080") == ["http://localhost/*", "http://127.0.0.1/*"]


def test_config_defaults_to_the_unpacked_connector_id(client):
    from afterparty.connector import extension_id, manifest

    cfg = client.get("/api/config").json()
    assert cfg["extensionIds"] == [extension_id(manifest()["key"])]
