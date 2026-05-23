
from __future__ import annotations

from math import ceil
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/companions", tags=["companions"])

CORE_STATS = ["strength", "dexterity", "stamina", "magic_affinity", "mana"]

BEAST_TYPE_RULES = {
    "combat": {"combat": 3, "mount": 2, "utility": 1, "own_type_skill_cap_per_tier": 3, "non_type_skill_cap_per_tier": 2},
    "mount": {"combat": 1, "mount": 3, "utility": 2, "own_type_skill_cap_per_tier": 3, "non_type_skill_cap_per_tier": 2},
    "utility": {"combat": 2, "mount": 1, "utility": 3, "own_type_skill_cap_per_tier": 3, "non_type_skill_cap_per_tier": 2},
}


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _require_login(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")
    return int(actor_discord_id)


def _character(sb, character_id: str) -> dict[str, Any]:
    rows = _safe_rows(sb.table("characters").select("*").eq("guild_id", get_guild_id()).eq("character_id", character_id).limit(1))
    if not rows:
        rows = _safe_rows(sb.table("characters").select("*").eq("character_id", character_id).limit(1))
    if not rows:
        raise HTTPException(status_code=404, detail="OC not found.")
    return rows[0]


def _can_access_character(character: dict[str, Any], actor: int) -> bool:
    if is_staff(actor):
        return True
    possible_owner_ids = [character.get("user_id"), character.get("discord_id"), character.get("owner_discord_id"), character.get("player_discord_id")]
    return any(str(value) == str(actor) for value in possible_owner_ids if value is not None)


def _trait_rows(sb, character_id: str, guild_id: int) -> list[dict[str, Any]]:
    owned_rows: list[dict[str, Any]] = []
    for table in ("oc_traits", "character_traits"):
        rows = _safe_rows(sb.table(table).select("*").eq("character_id", character_id).limit(200))
        if rows:
            owned_rows.extend(rows)
    if not owned_rows:
        return []

    trait_ids = [str(row.get("trait_id")) for row in owned_rows if row.get("trait_id")]
    slugs = []
    for row in owned_rows:
        for key in ("slug", "trait_slug", "trait_key"):
            if row.get(key):
                slugs.append(str(row.get(key)))

    found: list[dict[str, Any]] = []
    if trait_ids:
        found.extend(_safe_rows(sb.table("traits").select("*").eq("guild_id", guild_id).in_("trait_id", trait_ids).limit(300)))
    if slugs:
        found.extend(_safe_rows(sb.table("traits").select("*").eq("guild_id", guild_id).in_("slug", slugs).limit(300)))

    found_by_id = {str(row.get("trait_id")): row for row in found if row.get("trait_id")}
    found_by_slug = {str(row.get("slug")): row for row in found if row.get("slug")}
    resolved: list[dict[str, Any]] = []
    seen = set()
    for owned in owned_rows:
        source = None
        if owned.get("trait_id"):
            source = found_by_id.get(str(owned.get("trait_id")))
        if not source:
            for key in ("slug", "trait_slug", "trait_key"):
                if owned.get(key):
                    source = found_by_slug.get(str(owned.get(key)))
                    if source:
                        break
        source = source or owned
        slug = str(source.get("slug") or owned.get("slug") or owned.get("trait_slug") or owned.get("trait_key") or "")
        name = str(source.get("name") or owned.get("name") or owned.get("trait_name") or "")
        key = slug or name
        if key in seen:
            continue
        seen.add(key)
        resolved.append({**source, "slug": slug, "name": name or slug or "Trait"})
    return resolved


def _has_loyal_companion(traits: list[dict[str, Any]]) -> bool:
    for trait in traits:
        slug = str(trait.get("slug") or "").lower().replace("-", "_").replace(" ", "_")
        name = str(trait.get("name") or "").lower()
        if slug in {"loyal_companion", "keystone_loyal_companion", "trait_loyal_companion"}:
            return True
        if "loyal companion" in name or "loyal_companion" in slug:
            return True
    return False


def _stats(sb, character_id: str, guild_id: int) -> dict[str, int]:
    rows = _safe_rows(sb.table("oc_stats").select("stat_key,stat_value,value").eq("guild_id", guild_id).eq("character_id", character_id).limit(100))
    out = {key: 0 for key in CORE_STATS}
    for row in rows:
        key = str(row.get("stat_key") or "")
        if key in out:
            out[key] = int(row.get("stat_value") if row.get("stat_value") is not None else row.get("value") or 0)
    return out


def _default_beast(character_id: str, guild_id: int) -> dict[str, Any]:
    return {
        "character_id": character_id,
        "guild_id": guild_id,
        "beast_name": "",
        "beast_type": "utility",
        "description": "",
        "image_url": "",
        "xp": 0,
        "base_strength": 5,
        "base_dexterity": 5,
        "base_stamina": 5,
        "base_magic_affinity": 5,
        "base_mana": 5,
        "current_skills": "",
        "notes": "",
    }


def _computed_stats(beast: dict[str, Any], oc_stats: dict[str, int]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for key in CORE_STATS:
        base_key = f"base_{key}"
        base = int(beast.get(base_key) or 5)
        modifier = ceil(int(oc_stats.get(key) or 0) * 0.10)
        out[key] = {"base": base, "modifier": modifier, "final": base + modifier}
    return out


@router.get("/eligibility")
def companion_eligibility(actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    character_rows = _safe_rows(
        sb.table("characters")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("user_id", str(actor))
        .limit(300)
    )

    if not character_rows:
        character_rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq("user_id", str(actor))
            .limit(300)
        )

    eligible_characters = []

    for character in character_rows:
        cid = str(character.get("character_id") or "")
        if not cid:
            continue

        guild_id = int(character.get("guild_id") or get_guild_id())
        traits = _trait_rows(sb, cid, guild_id)

        if _has_loyal_companion(traits):
            eligible_characters.append({
                "character_id": cid,
                "name": character.get("name"),
            })

    return {
        "eligible": bool(eligible_characters),
        "eligible_characters": eligible_characters,
    }

@router.get("/{character_id}")
def get_companion(character_id: UUID, actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    cid = str(character_id)
    character = _character(sb, cid)
    if not _can_access_character(character, actor):
        raise HTTPException(status_code=403, detail="You can only view your own companion.")
    guild_id = int(character.get("guild_id") or get_guild_id())
    traits = _trait_rows(sb, cid, guild_id)
    eligible = _has_loyal_companion(traits)
    beast_rows = _safe_rows(sb.table("source_beasts").select("*").eq("guild_id", guild_id).eq("character_id", cid).limit(1))
    beast = beast_rows[0] if beast_rows else _default_beast(cid, guild_id)
    oc_stats = _stats(sb, cid, guild_id)
    beast_type = str(beast.get("beast_type") or "utility")
    return {
        "eligible": eligible,
        "character": {"character_id": cid, "name": character.get("name")},
        "loyal_companion_trait": next((trait for trait in traits if _has_loyal_companion([trait])), None),
        "beast": beast,
        "oc_stats": oc_stats,
        "computed_stats": _computed_stats(beast, oc_stats),
        "type_rules": BEAST_TYPE_RULES.get(beast_type, BEAST_TYPE_RULES["utility"]),
        "allowed_types": ["combat", "mount", "utility"],
    }


@router.put("/{character_id}")
def save_companion(character_id: UUID, payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    cid = str(character_id)
    character = _character(sb, cid)
    if not _can_access_character(character, actor):
        raise HTTPException(status_code=403, detail="You can only edit your own companion.")
    guild_id = int(character.get("guild_id") or get_guild_id())
    traits = _trait_rows(sb, cid, guild_id)
    if not _has_loyal_companion(traits):
        raise HTTPException(status_code=403, detail="This OC does not have the Loyal Companion trait.")
    beast_type = str(payload.get("beast_type") or "utility").strip().lower()
    if beast_type == "support":
        beast_type = "utility"
    if beast_type not in BEAST_TYPE_RULES:
        raise HTTPException(status_code=400, detail="Beast type must be combat, mount, or utility.")
    def stat_value(key: str) -> int:
        try:
            return max(0, int(payload.get(key, 5)))
        except Exception:
            return 5
    row = {
        "guild_id": guild_id,
        "character_id": cid,
        "beast_name": str(payload.get("beast_name") or "").strip()[:160],
        "beast_type": beast_type,
        "description": str(payload.get("description") or "").strip()[:4000],
        "image_url": str(payload.get("image_url") or "").strip()[:1000],
        "xp": max(0, int(payload.get("xp") or 0)),
        "base_strength": stat_value("base_strength"),
        "base_dexterity": stat_value("base_dexterity"),
        "base_stamina": stat_value("base_stamina"),
        "base_magic_affinity": stat_value("base_magic_affinity"),
        "base_mana": stat_value("base_mana"),
        "current_skills": str(payload.get("current_skills") or "").strip()[:4000],
        "notes": str(payload.get("notes") or "").strip()[:4000],
    }
    try:
        rows = _as_list(sb.table("source_beasts").upsert(row, on_conflict="character_id").execute())
    except Exception:
        existing = _safe_rows(sb.table("source_beasts").select("character_id").eq("character_id", cid).limit(1))
        if existing:
            rows = _as_list(sb.table("source_beasts").update(row).eq("character_id", cid).execute())
        else:
            rows = _as_list(sb.table("source_beasts").insert(row).execute())
    saved = rows[0] if rows else row
    oc_stats = _stats(sb, cid, guild_id)
    return {"message": "Source Beast saved.", "beast": saved, "computed_stats": _computed_stats(saved, oc_stats), "type_rules": BEAST_TYPE_RULES.get(beast_type, BEAST_TYPE_RULES["utility"])}
