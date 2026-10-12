"""Who is calling: Firebase ID tokens for users; a shared secret or OIDC for the scheduler."""

from __future__ import annotations

import hmac
import threading
import time

import httpx
from fastapi import HTTPException, Request
from google.auth import jwt as gjwt

from . import db
from .config import settings

CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
)
_certs: dict[str, str] = {}
_certs_expiry = 0.0
_lock = threading.Lock()


def _firebase_certs() -> dict[str, str]:
    """Google's signing certs, cached for as long as Cache-Control allows."""
    global _certs, _certs_expiry
    with _lock:
        if time.time() < _certs_expiry and _certs:
            return _certs
        resp = httpx.get(CERTS_URL, timeout=10)
        resp.raise_for_status()
        max_age = 3600
        for part in resp.headers.get("cache-control", "").split(","):
            if part.strip().startswith("max-age="):
                max_age = int(part.strip()[8:])
        _certs, _certs_expiry = resp.json(), time.time() + max_age
        return _certs


def verify_firebase(token: str) -> dict:
    project = settings.firebase_project_id
    try:
        claims = gjwt.decode(
            token, certs=_firebase_certs(), audience=project, clock_skew_in_seconds=10
        )
    except ValueError as exc:
        raise HTTPException(401, "Invalid or expired sign-in. Sign in again.") from exc
    if claims.get("iss") != f"https://securetoken.google.com/{project}" or not claims.get("sub"):
        raise HTTPException(401, "Token was not issued for this app.")
    # ALLOWED_EMAILS keys off the email, so it must be one the user proved they own.
    # Google sign-in and email links both verify it.
    if not claims.get("email_verified"):
        raise HTTPException(403, "Verify your email address, then sign in again.")
    return claims


def claims_from_request(request: Request) -> dict:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value:
        return verify_firebase(value)
    if scheme.lower() == "dev" and value and settings.dev_auth_allowed:
        email = value.strip().lower()
        name = " ".join(w.capitalize() for w in email.split("@")[0].replace("_", ".").split("."))
        return {"sub": f"dev:{email}", "email": email, "name": name}
    raise HTTPException(401, "Sign in required.")


def allowed(email: str) -> bool:
    """ALLOWED_EMAILS: exact addresses and "@domain" entries. Empty allows everyone."""
    rules = settings.allowed_emails
    if not rules:
        return True
    domain = "@" + email.rsplit("@", 1)[-1]
    return email in rules or domain in rules


def upsert_user(claims: dict) -> dict:
    email = (claims.get("email") or "").lower()
    if not email:
        raise HTTPException(400, "Your sign-in has no email address.")
    if not allowed(email):
        raise HTTPException(403, "This Afterparty is private. Ask its owner to add your email.")
    return db.one(
        """
        INSERT INTO users (firebase_uid, email, name, photo_url)
        VALUES (%(uid)s, %(email)s, %(name)s, %(photo)s)
        ON CONFLICT (firebase_uid) DO UPDATE SET
            email = EXCLUDED.email,
            name = COALESCE(EXCLUDED.name, users.name),
            photo_url = COALESCE(EXCLUDED.photo_url, users.photo_url),
            last_seen_at = now()
        RETURNING *
        """,
        {
            "uid": claims["sub"],
            "email": email,
            "name": claims.get("name"),
            "photo": claims.get("picture"),
        },
    )


def current_user(request: Request) -> dict:
    return upsert_user(claims_from_request(request))


def verify_scheduler(request: Request) -> None:
    """/internal/* callers: `Bearer <CRON_SECRET>`, or (Google Cloud) Cloud Scheduler's
    OIDC token for SCHEDULER_SA."""
    from google.auth.transport import requests as greq
    from google.oauth2 import id_token

    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Scheduler token required.")
    if settings.cron_secret and hmac.compare_digest(token, settings.cron_secret):
        return
    if not settings.scheduler_sa:
        raise HTTPException(401, "Scheduler token required.")
    try:
        claims = id_token.verify_oauth2_token(token, greq.Request(), audience=settings.service_url)
    except ValueError as exc:
        raise HTTPException(401, "Invalid scheduler token.") from exc
    if claims.get("email") != settings.scheduler_sa or not claims.get("email_verified"):
        raise HTTPException(403, "Wrong caller.")
