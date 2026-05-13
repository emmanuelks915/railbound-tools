from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

import time
from httpx import RemoteProtocolError, ConnectError, ReadTimeout

def execute_with_retry(query, attempts: int = 3, delay: float = 0.35):
    last_error = None

    for attempt in range(attempts):
        try:
            return query.execute()
        except (RemoteProtocolError, ConnectError, ReadTimeout) as e:
            last_error = e
            if attempt < attempts - 1:
                time.sleep(delay)

    raise last_error