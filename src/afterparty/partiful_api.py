"""Partiful over plain HTTPS, from a stored Firebase refresh token.

Partiful's web app signs users in with Firebase Auth (project ``getpartiful``).
A refresh token from that session mints fresh ID tokens at
``securetoken.googleapis.com``, and ``api.partiful.com`` accepts the ID token as
a bearer — the same two calls the browser makes. Verified 2026-10-08.

Partiful's public API key is referrer-restricted, so the refresh call must say
it comes from partiful.com or Google rejects it.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

API = "https://api.partiful.com"
TOKEN_URL = "https://securetoken.googleapis.com/v1/token"  # noqa: S105 — a URL, not a secret
REFERER = "https://partiful.com/"


#: Google's refresh-token errors that mean the session is dead for good.
FATAL_REFRESH = (
    "INVALID_REFRESH_TOKEN",
    "TOKEN_EXPIRED",
    "USER_DISABLED",
    "USER_NOT_FOUND",
    "INVALID_ID_TOKEN",
)


class PartifulAuthError(RuntimeError):
    """The refresh token no longer works: the user must reconnect."""


class PartifulApiError(RuntimeError):
    pass


@dataclass
class Token:
    id_token: str
    refresh_token: str
    uid: str
    expires_at: float


def refresh(refresh_token: str, api_key: str, client: httpx.Client | None = None) -> Token:
    c = client or httpx.Client(timeout=30)
    try:
        resp = c.post(
            TOKEN_URL,
            params={"key": api_key},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            headers={"Referer": REFERER},
        )
    finally:
        if client is None:
            c.close()
    if not resp.is_success:
        try:
            msg = (resp.json().get("error") or {}).get("message", "")
        except ValueError:
            msg = ""
        # Only these mean the session itself is gone and the user must reconnect.
        # A 403 referrer block, 429 or 5xx is ours or Google's to fix: retry later.
        if any(msg.startswith(code) for code in FATAL_REFRESH):
            raise PartifulAuthError(msg)
        raise PartifulApiError(f"token refresh -> HTTP {resp.status_code} {msg}".strip())
    j = resp.json()
    return Token(
        id_token=j["id_token"],
        refresh_token=j["refresh_token"],
        uid=j["user_id"],
        expires_at=time.time() + int(j.get("expires_in", 3600)) - 120,
    )


class PartifulClient:
    def __init__(
        self,
        refresh_token: str,
        api_key: str,
        delay: float = 0.3,
        on_rotate: Callable[[str], None] | None = None,
    ):
        self.api_key = api_key
        self.delay = delay
        self.on_rotate = on_rotate
        self.http = httpx.Client(timeout=60)
        self.token = self._refresh(refresh_token)

    def _refresh(self, refresh_token: str) -> Token:
        token = refresh(refresh_token, self.api_key, self.http)
        if token.refresh_token != refresh_token and self.on_rotate:
            self.on_rotate(token.refresh_token)  # Google rotated it: keep the new one
        return token

    def close(self) -> None:
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @property
    def uid(self) -> str:
        return self.token.uid

    def _bearer(self, force: bool = False) -> str:
        if force or time.time() >= self.token.expires_at:
            self.token = self._refresh(self.token.refresh_token)
        return self.token.id_token

    def _send(self, method: str, url: str, **kw) -> httpx.Response:
        """One request with the user's bearer. A 401 gets one retry with a freshly
        minted token; 429 and 5xx back off and retry twice before giving up."""
        refreshed = False
        for attempt in range(3):
            headers = {"authorization": f"Bearer {self._bearer()}", "Referer": REFERER}
            resp = self.http.request(method, url, headers=headers, **kw)
            if self.delay:
                time.sleep(self.delay)
            if resp.status_code == 401 and not refreshed:
                self._bearer(force=True)
                refreshed = True
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            return resp
        return resp

    def call(self, endpoint: str, params: dict | None = None, paging: dict | None = None) -> Any:
        envelope: dict[str, Any] = {"params": params or {}, "userId": self.uid}
        if paging:
            envelope["paging"] = paging
        resp = self._send("POST", f"{API}/{endpoint}", json={"data": envelope})
        if not resp.is_success:
            raise PartifulApiError(f"{endpoint} -> HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json().get("result") or {}

    # ------------------------------------------------------------ endpoints
    def home_events(self) -> list[tuple[str, dict]]:
        """Every event on the user's home page, tagged with the bucket it came
        from (``pastEvents``/``upcomingEvents``/…). Buckets overlap; the caller
        dedupes, preferring the earlier bucket."""
        out: list[tuple[str, dict]] = []
        for endpoint in ("getMyPastEventsForHomePage", "getMyUpcomingEventsForHomePage"):
            data = self.call(endpoint).get("data") or {}
            for bucket, rows in data.items():
                if isinstance(rows, list):
                    out.extend((bucket, r) for r in rows if isinstance(r, dict) and r.get("id"))
        return out

    def guests(self, event_id: str, hosting: bool = False) -> list[dict]:
        """Guest rows in ``getGuests`` shape, whichever way Partiful serves them.

        Guests get the list from ``getGuests``. Hosts get "User is host" there:
        their app reads the event's Firestore ``guests`` collection instead.
        """
        if hosting:
            return self.host_guests(event_id)
        try:
            return self.guest_view(event_id)
        except PartifulApiError as exc:
            if "User is host" in str(exc):
                return self.host_guests(event_id)
            raise

    def guest_view(self, event_id: str, page_size: int = 500, max_pages: int = 40) -> list[dict]:
        rows: list[dict] = []
        cursor = None
        for _ in range(max_pages):
            result = self.call(
                "getGuests",
                {"eventId": event_id, "includeInvitedGuests": True},
                {"cursor": cursor, "maxResults": page_size},
            )
            data = result.get("data")
            if isinstance(data, list):
                rows.extend(r for r in data if isinstance(r, dict))
            cursor = (result.get("paging") or {}).get("nextCursor")
            if not cursor:
                break
        return rows

    def host_guests(self, event_id: str) -> list[dict]:
        """A host's guest list: Firestore ``events/<id>/guests`` (each doc points
        at ``users/<uid>``), then ``getUsers`` for the profiles behind them."""
        docs: list[dict] = []
        page_token = None
        for _ in range(40):
            params = {"pageSize": 300, **({"pageToken": page_token} if page_token else {})}
            resp = self._send("GET", f"{FIRESTORE}/events/{event_id}/guests", params=params)
            if not resp.is_success:
                raise PartifulApiError(f"host guest list -> HTTP {resp.status_code}")
            body = resp.json()
            docs.extend(_fs_doc(d) for d in body.get("documents", []))
            page_token = body.get("nextPageToken")
            if not page_token:
                break

        ids = sorted({d["userId"] for d in docs if d.get("userId")})
        profiles: dict[str, dict] = {}
        for i in range(0, len(ids), 50):
            data = self.call("getUsers", {"ids": ids[i : i + 50], "includePartyStats": False})
            for u in data.get("data") or []:
                if isinstance(u, dict) and u.get("id"):
                    profiles[u["id"]] = u
        rows = []
        for d in docs:
            uid = d.get("userId")
            person = profiles.get(uid) if uid else None
            rows.append(
                {
                    "id": d["id"],
                    "status": d.get("status"),
                    "plusOneCount": max(int(d.get("count") or 1) - 1, 0),
                    "userId": uid,
                    "name": d.get("name") or (person or {}).get("name") or "",
                    "user": person or ({"id": uid, "name": d.get("name")} if uid else None),
                }
            )
        return rows


FIRESTORE = "https://firestore.googleapis.com/v1/projects/getpartiful/databases/(default)/documents"


def _fs_value(v: dict):
    """Firestore REST typed value -> plain Python."""
    if "mapValue" in v:
        return {k: _fs_value(x) for k, x in (v["mapValue"].get("fields") or {}).items()}
    if "arrayValue" in v:
        return [_fs_value(x) for x in v["arrayValue"].get("values") or []]
    if "integerValue" in v:
        return int(v["integerValue"])
    for key in ("stringValue", "booleanValue", "doubleValue", "timestampValue", "referenceValue"):
        if key in v:
            return v[key]
    return None


def _fs_doc(doc: dict) -> dict:
    fields = {k: _fs_value(v) for k, v in (doc.get("fields") or {}).items()}
    ref = fields.get("user")
    return {
        "id": doc["name"].rsplit("/", 1)[-1],
        "status": fields.get("status"),
        "name": fields.get("name"),
        "count": fields.get("count"),
        "userId": ref.rsplit("/", 1)[-1] if isinstance(ref, str) and "/users/" in ref else None,
    }
