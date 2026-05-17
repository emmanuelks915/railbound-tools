from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.services import derived_stats_from_core, get_character, get_character_stats, get_wallet, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/characters", tags=["characters"])


# --- Character Summary Traits v1 ---

def _safe_rows(query):
    try:
        return sb_data(query.execute()) or []
    except Exception:
        return []


def _character_traits(sb, character_id: UUID) -> list[dict]:
    gid = None
    try:
        character = get_character(sb, character_id)
        gid = character.get("guild_id")
    except Exception:
        gid = None

    owned_rows: list[dict] = []
    for table in ("oc_traits", "character_traits"):
        rows = _safe_rows(sb.table(table).select("*").eq("character_id", str(character_id)))
        if rows:
            owned_rows = rows
            break

    if not owned_rows:
        return []

    trait_ids = []
    slugs = []

    for row in owned_rows:
        if row.get("trait_id"):
            trait_ids.append(str(row.get("trait_id")))
        for key in ("slug", "trait_slug", "trait_key"):
            if row.get(key):
                slugs.append(str(row.get(key)))

    trait_by_id: dict[str, dict] = {}
    trait_by_slug: dict[str, dict] = {}

    if trait_ids:
        q = sb.table("traits").select("*").in_("trait_id", trait_ids)
        if gid:
            q = q.eq("guild_id", gid)
        trait_rows = _safe_rows(q)
        trait_by_id = {str(row.get("trait_id")): row for row in trait_rows if row.get("trait_id")}

    if slugs:
        q = sb.table("traits").select("*").in_("slug", slugs)
        if gid:
            q = q.eq("guild_id", gid)
        trait_rows = _safe_rows(q)
        trait_by_slug = {str(row.get("slug")): row for row in trait_rows if row.get("slug")}

    out: list[dict] = []
    seen = set()

    for owned in owned_rows:
        source = None

        if owned.get("trait_id"):
            source = trait_by_id.get(str(owned.get("trait_id")))

        if not source:
            for key in ("slug", "trait_slug", "trait_key"):
                if owned.get(key):
                    source = trait_by_slug.get(str(owned.get(key)))
                    if source:
                        break

        source = source or {}

        slug = (
            source.get("slug")
            or owned.get("slug")
            or owned.get("trait_slug")
            or owned.get("trait_key")
            or owned.get("trait_id")
            or owned.get("name")
        )

        if slug and slug in seen:
            continue
        if slug:
            seen.add(slug)

        out.append({
            "trait_id": str(source.get("trait_id") or owned.get("trait_id") or ""),
            "slug": slug,
            "name": source.get("name") or owned.get("name") or owned.get("trait_name") or owned.get("trait_key") or "Trait",
            "tier": source.get("tier") or owned.get("tier"),
            "cost": source.get("cost") if source.get("cost") is not None else owned.get("cost"),
            "category": source.get("category") or owned.get("category") or owned.get("type") or owned.get("trait_type"),
            "description": source.get("description") or owned.get("description") or owned.get("summary"),
            "effects_json": source.get("effects_json") or owned.get("effects_json") or {},
            "requirements_json": source.get("requirements_json") or owned.get("requirements_json") or {},
            "acquired_at": owned.get("acquired_at") or owned.get("created_at"),
            "notes": owned.get("notes") or owned.get("staff_note"),
        })

    return out


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
        "traits": _character_traits(sb, character_id),
    }
