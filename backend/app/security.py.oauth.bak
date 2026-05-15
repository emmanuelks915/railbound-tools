from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import get_settings


def actor_from_header(x_discord_id: str | None = Header(default=None)) -> int | None:
    if not x_discord_id:
        return None
    if not x_discord_id.isdigit():
        raise HTTPException(status_code=400, detail="X-Discord-Id must be numeric.")
    return int(x_discord_id)


def require_staff(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Discord-Id header.")

    settings = get_settings()
    if actor_discord_id not in settings.staff_ids:
        raise HTTPException(status_code=403, detail="Staff only.")

    return actor_discord_id
