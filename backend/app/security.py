from __future__ import annotations

from fastapi import Header, HTTPException

from app.auth_tokens import verify_session_token
from app.config import get_settings


def _actor_from_bearer(authorization: str | None) -> int | None:
    if not authorization:
        return None

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    payload = verify_session_token(parts[1].strip())
    if not payload:
        return None

    discord_id = str(payload.get("discord_id") or "").strip()
    if not discord_id.isdigit():
        return None

    return int(discord_id)


def actor_from_header(
    x_discord_id: int | None = Header(default=None, alias="X-Discord-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> int | None:
    bearer_actor = _actor_from_bearer(authorization)
    if bearer_actor is not None:
        return bearer_actor

    # Manual Discord ID login is a local-dev escape hatch only.
    # In production, ALLOW_DEV_LOGIN should be false so users must authenticate through Discord OAuth.
    if get_settings().allow_dev_login:
        return x_discord_id

    return None


def require_staff(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Missing Discord identity.")

    if actor_discord_id not in get_settings().staff_ids:
        raise HTTPException(status_code=403, detail="Staff access required.")

    return actor_discord_id
