from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from fastapi import HTTPException
from httpx import ConnectError, ReadTimeout, RemoteProtocolError
from postgrest.exceptions import APIError
from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def execute_with_retry(query, attempts: int = 3, delay: float = 0.35):
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            return query.execute()
        except (RemoteProtocolError, ConnectError, ReadTimeout) as e:
            last_error = e
            if attempt < attempts - 1:
                time.sleep(delay)

    raise last_error or RuntimeError("Supabase request failed.")


def api_error_message(error: APIError) -> str:
    raw: Any = error.args[0] if error.args else None

    if isinstance(raw, dict):
        return (
            raw.get("message")
            or raw.get("details")
            or raw.get("hint")
            or "Database request failed."
        )

    return str(error) or "Database request failed."


def raise_clean_api_error(error: APIError):
    message = api_error_message(error)
    lower = message.lower()

    if "not found" in lower:
        status = 404
    elif "stale" in lower or "not pending" in lower or "already" in lower:
        status = 409
    elif (
        "not enough xp" in lower
        or "cannot be lower" in lower
        or "target value" in lower
        or "no changed stats" in lower
        or "invalid" in lower
        or "must be" in lower
    ):
        status = 400
    else:
        status = 400

    raise HTTPException(status_code=status, detail=message)