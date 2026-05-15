from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.config import get_settings


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def create_session_token(payload: dict[str, Any], *, max_age_seconds: int = 60 * 60 * 24 * 7) -> str:
    settings = get_settings()
    now = int(time.time())
    body = {**payload, "iat": now, "exp": now + max_age_seconds}

    encoded_payload = _b64encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(
        settings.auth_session_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return f"{encoded_payload}.{_b64encode(signature)}"


def verify_session_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None

    settings = get_settings()
    encoded_payload, supplied_signature = token.split(".", 1)

    expected_signature = hmac.new(
        settings.auth_session_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    try:
        supplied_bytes = _b64decode(supplied_signature)
    except Exception:
        return None

    if not hmac.compare_digest(expected_signature, supplied_bytes):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
    except Exception:
        return None

    expires_at = int(payload.get("exp") or 0)
    if expires_at and expires_at < int(time.time()):
        return None

    return payload
