from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import httpx
from fastapi import HTTPException
from httpx import ConnectError, ReadTimeout, RemoteProtocolError
from postgrest.exceptions import APIError
from supabase import create_client

from app.config import get_settings


class SimpleSupabaseResponse:
    def __init__(self, data: Any):
        self.data = data


def _postgrest_error(response: httpx.Response) -> APIError:
    try:
        payload = response.json()
    except Exception:
        payload = {
            "message": response.text or "Supabase request failed.",
            "code": str(response.status_code),
            "details": response.text,
            "hint": None,
        }

    if not isinstance(payload, dict):
        payload = {
            "message": str(payload),
            "code": str(response.status_code),
            "details": response.text,
            "hint": None,
        }

    payload.setdefault("message", "Supabase request failed.")
    payload.setdefault("code", str(response.status_code))
    payload.setdefault("details", None)
    payload.setdefault("hint", None)

    return APIError(payload)


class SupabaseRestQuery:
    def __init__(self, client: "SupabaseRestClient", table_name: str):
        self.client = client
        self.table_name = table_name
        self.method = "GET"
        self.params: dict[str, str] = {}
        self.body: Any = None
        self.prefer: list[str] = []

    def select(self, columns: str = "*"):
        self.method = "GET"
        self.params["select"] = columns
        return self

    def insert(self, payload: Any):
        self.method = "POST"
        self.body = payload
        self.prefer = ["return=representation"]
        return self

    def update(self, payload: dict[str, Any]):
        self.method = "PATCH"
        self.body = payload
        self.prefer = ["return=representation"]
        return self

    def delete(self):
        self.method = "DELETE"
        self.prefer = ["return=representation"]
        return self

    def upsert(self, payload: Any, on_conflict: str | None = None):
        self.method = "POST"
        self.body = payload
        self.prefer = ["resolution=merge-duplicates", "return=representation"]
        if on_conflict:
            self.params["on_conflict"] = on_conflict
        return self

    def eq(self, column: str, value: Any):
        self.params[column] = f"eq.{value}"
        return self

    def neq(self, column: str, value: Any):
        self.params[column] = f"neq.{value}"
        return self

    def in_(self, column: str, values: list[Any]):
        joined = ",".join(str(v) for v in values)
        self.params[column] = f"in.({joined})"
        return self

    def order(self, column: str, desc: bool = False):
        direction = "desc" if desc else "asc"
        self.params["order"] = f"{column}.{direction}"
        return self

    def limit(self, count: int):
        self.params["limit"] = str(count)
        return self

    def execute(self):
        url = f"{self.client.rest_url}/{self.table_name}"
        headers = self.client.headers.copy()

        if self.prefer:
            headers["Prefer"] = ",".join(self.prefer)

        response = self.client.http.request(
            self.method,
            url,
            params=self.params,
            json=self.body,
            headers=headers,
        )

        if response.status_code >= 400:
            raise _postgrest_error(response)

        if response.status_code == 204 or not response.content:
            return SimpleSupabaseResponse(None)

        return SimpleSupabaseResponse(response.json())


class SupabaseRestRpc:
    def __init__(self, client: "SupabaseRestClient", function_name: str, params: dict[str, Any] | None):
        self.client = client
        self.function_name = function_name
        self.params = params or {}

    def execute(self):
        url = f"{self.client.rest_url}/rpc/{self.function_name}"

        response = self.client.http.post(
            url,
            json=self.params,
            headers=self.client.headers,
        )

        if response.status_code >= 400:
            raise _postgrest_error(response)

        if response.status_code == 204 or not response.content:
            return SimpleSupabaseResponse(None)

        return SimpleSupabaseResponse(response.json())


class SupabaseRestClient:
    """
    Minimal Supabase REST client for new sb_secret_... keys.

    Why this exists:
    supabase-py/PostgREST client paths may place the API key into an
    Authorization Bearer header. New sb_secret_... keys are not JWTs,
    so PostgREST rejects that. This client sends the secret key as apikey only.
    """

    def __init__(self, supabase_url: str, secret_key: str):
        self.supabase_url = supabase_url.rstrip("/")
        self.rest_url = f"{self.supabase_url}/rest/v1"
        self.secret_key = secret_key

        self.headers = {
            "apikey": secret_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        self.http = httpx.Client(timeout=30.0)

    def table(self, table_name: str):
        return SupabaseRestQuery(self, table_name)

    def rpc(self, function_name: str, params: dict[str, Any] | None = None):
        return SupabaseRestRpc(self, function_name, params)


@lru_cache
def get_supabase():
    settings = get_settings()
    key = settings.supabase_admin_key

    if key.startswith("sb_publishable_"):
        raise ValueError(
            "SUPABASE_SECRET_KEY must be a backend secret key, not a publishable key."
        )

    if key.startswith("sb_secret_"):
        return SupabaseRestClient(settings.supabase_url, key)

    return create_client(settings.supabase_url, key)


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