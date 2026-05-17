
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["character-self"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in rows:
        key = str(row.get("character_id") or row.get("id") or row.get("name") or row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)

    return out


@router.get("/characters/mine")
def get_my_characters(actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()
    actor = str(actor_discord_id)

    owner_columns = [
        "user_id",
        "discord_id",
        "owner_discord_id",
        "player_discord_id",
    ]

    rows: list[dict[str, Any]] = []

    for column in owner_columns:
        rows.extend(
            _safe_rows(
                sb.table("characters")
                .select("*")
                .eq("guild_id", get_guild_id())
                .eq(column, actor)
                .limit(200)
            )
        )

    if not rows:
        for column in owner_columns:
            rows.extend(
                _safe_rows(
                    sb.table("characters")
                    .select("*")
                    .eq(column, actor)
                    .limit(200)
                )
            )

    return {"characters": _dedupe(rows)}
