"""Seed a demo account with synthetic people, for UI work without real guest data.

    uv run python scripts/seed_demo.py     # then dev sign-in as demo@example.com

Every name, bio and handle is made up (src/afterparty/demo.py).
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://postgres@127.0.0.1:54329/afterparty")
# Settings are read at import: the dev key must be in place first.
with open(".devdb/fernet.key") as f:
    os.environ.setdefault("ENCRYPTION_KEY", f.read().strip())

from afterparty import crypto, db, demo  # noqa: E402


def main() -> None:
    db.migrate()
    db.run("DELETE FROM users WHERE email = 'demo@example.com'")
    uid = db.one(
        "INSERT INTO users (firebase_uid, email, name, status, role, onboarded_at, approved_at)"
        " VALUES ('dev:demo@example.com', 'demo@example.com', 'Demo Person', 'approved', 'user',"
        " now(), now()) RETURNING id"
    )["id"]
    db.run(
        "INSERT INTO partiful_accounts (user_id, partiful_uid, display_name, refresh_token_enc, api_key)"
        " VALUES (%s, %s, 'Demo Partiful', %s, 'AIzaDemo')",
        (uid, demo.DEMO_UID, crypto.encrypt("demo")),
    )
    demo.seed(uid)
    for pid, status in (("demo-3", "contacted"), ("demo-8", "todo"), ("demo-15", "skip")):
        db.run(
            "INSERT INTO follow_ups (user_id, person_id, status, note) VALUES (%s, %s, %s, %s)",
            (uid, pid, status, "Talked about pilots."),
        )
    print("demo@example.com seeded")


if __name__ == "__main__":
    main()
