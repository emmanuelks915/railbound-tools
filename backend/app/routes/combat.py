from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.models import ManualDerivedStatsRequest
from app.services import derived_stats_from_core, get_character, get_character_stats
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/combat", tags=["combat"])


@router.post("/derived")
def calculate_manual_derived_stats(payload: ManualDerivedStatsRequest):
    return {
        "core": payload.model_dump(),
        "derived": derived_stats_from_core(payload.model_dump()),
    }


@router.get("/derived/{character_id}")
def calculate_character_derived_stats(character_id: UUID):
    sb = get_supabase()
    character = get_character(sb, character_id)
    stats = get_character_stats(sb, character_id)
    return {
        "character": character,
        "core": stats,
        "derived": derived_stats_from_core(stats),
    }
