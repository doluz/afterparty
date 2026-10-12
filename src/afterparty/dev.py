"""`afterparty-dev`: run the API in local mode against the Postgres from scripts/devdb.sh.

    scripts/devdb.sh start          # once per boot
    uv run afterparty-dev           # http://localhost:8080

Local mode signs you in with any email and no password, so it listens on
127.0.0.1 only. Every setting can be overridden from the environment or `.env`.
"""

from __future__ import annotations

import os


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    import uvicorn
    from cryptography.fernet import Fernet

    _load_dotenv()
    os.environ.setdefault("APP_ENV", "dev")
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres@127.0.0.1:54331/afterparty")
    os.environ.setdefault("FIREBASE_PROJECT_ID", "afterparty-local")
    keyfile = os.path.join(".devdb", "fernet.key")
    if not os.environ.get("ENCRYPTION_KEY"):
        os.makedirs(".devdb", exist_ok=True)
        if not os.path.exists(keyfile):
            with open(keyfile, "w") as f:
                f.write(Fernet.generate_key().decode())
        with open(keyfile) as f:
            os.environ["ENCRYPTION_KEY"] = f.read().strip()
    port = int(os.environ.get("PORT", "8080"))
    os.environ.setdefault("PUBLIC_URL", f"http://localhost:{port}")
    uvicorn.run("afterparty.app:app", host="127.0.0.1", port=port, reload=False)
