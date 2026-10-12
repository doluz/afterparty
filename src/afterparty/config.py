"""Runtime settings, all from the environment so one image serves every stage."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _csv(name: str) -> list[str]:
    return [v.strip().lower() for v in os.environ.get(name, "").split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    #: Firebase project that issues *our* users' ID tokens (not Partiful's).
    firebase_project_id: str = field(
        default_factory=lambda: os.environ.get("FIREBASE_PROJECT_ID", "")
    )
    #: Public web config handed to the SPA at runtime (apiKey, authDomain, appId…).
    firebase_web_config: str = field(
        default_factory=lambda: os.environ.get("FIREBASE_WEB_CONFIG", "{}")
    )
    #: Who may sign in: emails and/or "@domain" entries, comma-separated. Empty means
    #: anyone who can sign in. Each user only ever sees their own data.
    allowed_emails: list[str] = field(default_factory=lambda: _csv("ALLOWED_EMAILS"))
    #: Fernet key that encrypts Partiful tokens at rest. Generate one with
    #: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    encryption_key: str = field(default_factory=lambda: os.environ.get("ENCRYPTION_KEY", ""))
    #: Optional: a Google Cloud KMS key name. When set, it encrypts instead of
    #: ENCRYPTION_KEY, so the database alone cannot reveal a token. Needs the `gcp` extra.
    kms_key: str = field(default_factory=lambda: os.environ.get("KMS_KEY", ""))
    #: Connector ids, comma-separated. Empty means the unpacked build in extension/
    #: (its id is fixed by the manifest key). Add your Web Store item id here if you publish one.
    extension_ids: list[str] = field(default_factory=lambda: _csv("EXTENSION_ID"))
    #: The connector's Chrome Web Store page, once it is published. Empty until then.
    connector_store_url: str = field(
        default_factory=lambda: os.environ.get("CONNECTOR_STORE_URL", "")
    )
    app_env: str = field(default_factory=lambda: os.environ.get("APP_ENV", "prod"))
    #: Where people open this instance. The connector zip and notifications use it.
    public_url: str = field(
        default_factory=lambda: os.environ.get("PUBLIC_URL", "http://localhost:8080").rstrip("/")
    )
    #: Sync everyone once a day from inside the server process. Simplest for one machine.
    background_sync: bool = field(default_factory=lambda: _flag("BACKGROUND_SYNC"))
    #: Or call POST /internal/sync-all from any scheduler with
    #: `Authorization: Bearer <CRON_SECRET>`.
    cron_secret: str = field(default_factory=lambda: os.environ.get("CRON_SECRET", ""))
    #: Optional, Google Cloud: accept Cloud Scheduler's OIDC token for this service account.
    #: SERVICE_URL is the audience the token carries.
    service_url: str = field(default_factory=lambda: os.environ.get("SERVICE_URL", ""))
    scheduler_sa: str = field(default_factory=lambda: os.environ.get("SCHEDULER_SA", ""))
    #: Seconds between Partiful calls during a sync. Keep it polite.
    partiful_delay: float = field(
        default_factory=lambda: float(os.environ.get("PARTIFUL_DELAY", "0.3"))
    )

    @property
    def dev_auth_allowed(self) -> bool:
        """Local mode: `Authorization: Dev <email>` signs in with no password. Only for
        an instance nobody else can reach. Cloud Run always sets K_SERVICE, so a
        misconfigured APP_ENV there still can't enable it."""
        return self.app_env == "dev" and not os.environ.get("K_SERVICE")


settings = Settings()
