from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.services import derived_stats_from_core, get_character, get_character_stats, get_wallet, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("")
def list_characters(discord_id: str | None = Query(default=None)):
    sb = get_supabase()
    query = sb.table("characters").select("character_id,name,user_id").order("name", desc=False).limit(200)

    if discord_id:
        query = query.eq("user_id", str(discord_id))

    res = query.execute()
    return {"characters": sb_data(res) or []}


@router.get("/{character_id}/summary")
def character_summary(character_id: UUID):
    sb = get_supabase()
    character = get_character(sb, character_id)
    stats = get_character_stats(sb, character_id)
    wallet = get_wallet(sb, character_id)
    return {
        "character": character,
        "stats": stats,
        "derived": derived_stats_from_core(stats),
        "wallet": wallet,
    }
