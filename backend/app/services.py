from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.config import get_settings

CORE_STAT_KEYS = ["strength", "dexterity", "stamina", "magic_affinity", "mana"]


def sb_data(result: Any) -> Any:
    return getattr(result, "data", None)


def get_guild_id() -> int:
    return get_settings().railbound_guild_id


def get_character(sb: Client, character_id: UUID) -> dict[str, Any]:
    res = (
        sb.table("characters")
        .select("character_id,name,user_id")
        .eq("character_id", str(character_id))
        .limit(1)
        .execute()
    )
    rows = sb_data(res) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found.")
    return rows[0]


def get_character_stats(sb: Client, character_id: UUID, guild_id: int | None = None) -> dict[str, int]:
    guild_id = guild_id or get_guild_id()
    res = (
        sb.table("oc_stats")
        .select("stat_key,stat_value")
        .eq("guild_id", guild_id)
        .eq("character_id", str(character_id))
        .in_("stat_key", CORE_STAT_KEYS)
        .execute()
    )
    rows = sb_data(res) or []
    stats = {key: 0 for key in CORE_STAT_KEYS}
    for row in rows:
        key = str(row.get("stat_key") or "")
        if key in stats:
            stats[key] = int(row.get("stat_value") or 0)
    return stats


def get_wallet(sb: Client, character_id: UUID, guild_id: int | None = None) -> dict[str, int]:
    guild_id = guild_id or get_guild_id()
    sb.rpc(
        "ensure_oc_xp_wallet",
        {
            "p_guild_id": guild_id,
            "p_character_id": str(character_id),
        },
    ).execute()

    res = (
        sb.table("oc_xp_wallets")
        .select("available_xp,total_earned_xp,total_spent_xp")
        .eq("guild_id", guild_id)
        .eq("character_id", str(character_id))
        .limit(1)
        .execute()
    )
    rows = sb_data(res) or []
    if not rows:
        return {"available_xp": 0, "total_earned_xp": 0, "total_spent_xp": 0}
    row = rows[0]
    return {
        "available_xp": int(row.get("available_xp") or 0),
        "total_earned_xp": int(row.get("total_earned_xp") or 0),
        "total_spent_xp": int(row.get("total_spent_xp") or 0),
    }


def derived_stats_from_core(stats: dict[str, int]) -> dict[str, float]:
    strength = int(stats.get("strength") or 0)
    dexterity = int(stats.get("dexterity") or 0)
    stamina = int(stats.get("stamina") or 0)
    mana = int(stats.get("mana") or 0)

    reaction = dexterity * 1.5
    fortitude = stamina * 1.25
    safe_output = fortitude * 1.15
    magic_safe_output = (fortitude * 0.6) + (mana * 0.8)
    ap = 1 + (fortitude / 150)
    carry_capacity = 4 + (strength / 150)

    return {
        "reaction_score": round(reaction, 2),
        "fortitude": round(fortitude, 2),
        "safe_output": round(safe_output, 2),
        "magic_safe_output": round(magic_safe_output, 2),
        "ap": round(ap, 2),
        "carry_capacity": round(carry_capacity, 2),
    }


def build_preview(sb: Client, character_id: UUID, target_stats: dict[str, int]) -> dict[str, Any]:
    guild_id = get_guild_id()
    character = get_character(sb, character_id)
    current_stats = get_character_stats(sb, character_id, guild_id)
    wallet = get_wallet(sb, character_id, guild_id)

    items: list[dict[str, Any]] = []
    total_cost = 0

    for stat_key, target_value in target_stats.items():
        current_value = int(current_stats.get(stat_key) or 0)
        target_value = int(target_value)

        if target_value <= current_value:
            continue

        rpc = sb.rpc(
            "calculate_stat_upgrade_cost",
            {
                "p_stat_key": stat_key,
                "p_current_value": current_value,
                "p_target_value": target_value,
            },
        ).execute()
        preview = sb_data(rpc)

        # supabase-py may return jsonb directly or inside a single-item list depending on API version
        if isinstance(preview, list) and preview:
            preview = preview[0]

        if not isinstance(preview, dict):
            raise HTTPException(status_code=500, detail="Invalid cost preview response from Supabase.")

        cost = int(preview.get("total_cost") or 0)
        total_cost += cost
        items.append(preview)

    if not items:
        raise HTTPException(status_code=400, detail="No stat increases found in target stats.")

    available = int(wallet.get("available_xp") or 0)

    return {
        "character": character,
        "current_stats": current_stats,
        "target_stats": target_stats,
        "wallet": wallet,
        "items": items,
        "total_cost": total_cost,
        "affordable": available >= total_cost,
        "remaining_xp": available - total_cost,
    }
