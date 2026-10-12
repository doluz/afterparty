"""Tell the admin about things that need a human: today, new access requests.

Optional Telegram message. Off unless TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are
set. Never blocks or fails the request that triggered it.
"""

from __future__ import annotations

import logging
import os
import threading

import httpx

from .config import settings

log = logging.getLogger("afterparty.notify")


def _send(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=10,
        ).raise_for_status()
    except Exception as exc:  # a missed ping must never break sign-in
        log.warning("telegram notify failed: %s", type(exc).__name__)


def access_requested(email: str, name: str | None) -> None:
    who = f"{name} <{email}>" if name else email
    text = f"Afterparty: {who} asked for access.\nApprove or decline: {settings.public_url}/admin"
    threading.Thread(target=_send, args=(text,), daemon=True).start()
