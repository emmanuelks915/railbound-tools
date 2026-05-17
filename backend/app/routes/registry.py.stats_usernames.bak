from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/registry", tags=["registry"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(sb, table: str, *, limit: int = 250) -> list[dict[str, Any]]:
    try:
        return _as_list(
            sb.table(table)
            .select("*")
            .eq("guild_id", get_guild_id())
            .limit(limit)
            .execute()
        )
    except Exception:
        return []


def _safe_rows_for_ids(sb, table: str, id_column: str, character_ids: list[str]) -> list[dict[str, Any]]:
    if not character_ids:
        return []

    try:
        return _as_list(
            sb.table(table)
            .select("*")
            .eq("guild_id", get_guild_id())
            .in_(id_column, character_ids)
            .limit(1000)
            .execute()
        )
    except Exception:
        return []


def _safe_one(sb, table: str, id_column: str, character_id: str) -> dict[str, Any] | None:
    try:
        rows = _as_list(
            sb.table(table)
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(id_column, character_id)
            .limit(1)
            .execute()
        )
        return rows[0] if rows else None
    except Exception:
        return None


def _cid(row: dict[str, Any]) -> str:
    return str(row.get("character_id") or row.get("id") or "")


def _name(row: dict[str, Any]) -> str:
    return str(row.get("name") or row.get("oc_name") or row.get("character_name") or "Unnamed OC")


def _owner(row: dict[str, Any]) -> str | None:
    value = (
        row.get("user_id")
        or row.get("discord_id")
        or row.get("owner_discord_id")
        or row.get("player_discord_id")
        or row.get("created_by_discord_id")
    )
    return str(value) if value is not None else None


def _portrait(row: dict[str, Any]) -> str | None:
    for key in ("portrait_url", "image_url", "avatar_url", "profile_image_url", "faceclaim_url"):
        if row.get(key):
            return str(row.get(key))
    return None


def _stats_from_character(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "strength", "dexterity", "stamina", "magic_affinity", "mana",
        "hp", "health", "speed", "dodge", "blitz", "carry_capacity",
        "current_xp", "available_xp", "spent_xp", "total_xp", "xp",
    ]
    return {key: row.get(key) for key in keys if row.get(key) is not None}


def _group(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        cid = str(row.get("character_id") or row.get("oc_id") or "")
        if cid:
            grouped.setdefault(cid, []).append(row)
    return grouped


def _first_source(sb, character_ids: list[str], sources: list[tuple[str, str]]) -> list[dict[str, Any]]:
    for table, id_column in sources:
        rows = _safe_rows_for_ids(sb, table, id_column, character_ids)
        if rows:
            return rows
    return []


def _skill_definitions(sb, skill_keys: list[str]) -> dict[str, dict[str, Any]]:
    if not skill_keys:
        return {}
    try:
        rows = _as_list(
            sb.table("skill_definitions")
            .select("skill_key,name,tree,tier,cost,description")
            .eq("guild_id", get_guild_id())
            .in_("skill_key", skill_keys)
            .execute()
        )
    except Exception:
        return {}
    return {str(row.get("skill_key")): row for row in rows if row.get("skill_key")}


def _skills(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_source(
        sb,
        character_ids,
        [
            ("character_skills", "character_id"),
            ("oc_skills", "character_id"),
            ("character_owned_skills", "character_id"),
            ("owned_skills", "character_id"),
        ],
    )
    defs = _skill_definitions(sb, sorted({str(row.get("skill_key")) for row in rows if row.get("skill_key")}))
    out = []
    for row in rows:
        key = str(row.get("skill_key") or "")
        d = defs.get(key) or {}
        out.append(
            {
                "character_id": row.get("character_id") or row.get("oc_id"),
                "skill_key": key,
                "name": d.get("name") or row.get("name") or key,
                "tree": d.get("tree") or row.get("tree"),
                "tier": d.get("tier") or row.get("tier"),
                "cost": d.get("cost") or row.get("cost"),
                "description": d.get("description") or row.get("description"),
            }
        )
    return _group(out)


def _traits(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_source(
        sb,
        character_ids,
        [
            ("character_traits", "character_id"),
            ("oc_traits", "character_id"),
            ("traits", "character_id"),
        ],
    )
    out = []
    for row in rows:
        out.append(
            {
                "character_id": row.get("character_id") or row.get("oc_id"),
                "name": row.get("name") or row.get("trait_name") or row.get("trait_key") or "Trait",
                "description": row.get("description") or row.get("summary"),
                "type": row.get("type") or row.get("trait_type"),
            }
        )
    return _group(out)


def _inventory(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_source(
        sb,
        character_ids,
        [
            ("character_inventory", "character_id"),
            ("oc_inventory", "character_id"),
            ("inventory", "character_id"),
        ],
    )
    out = []
    for row in rows:
        out.append(
            {
                "character_id": row.get("character_id") or row.get("oc_id"),
                "name": row.get("name") or row.get("item_name") or row.get("item_key") or "Item",
                "quantity": row.get("quantity") or row.get("amount") or 1,
                "description": row.get("description"),
                "type": row.get("type") or row.get("item_type"),
            }
        )
    return _group(out)


def _stats(sb, character_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows = _first_source(
        sb,
        character_ids,
        [
            ("character_stats", "character_id"),
            ("oc_stats", "character_id"),
            ("stats", "character_id"),
        ],
    )
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("character_id") or row.get("oc_id") or "")
        if cid:
            out[cid] = row
    return out


def _normalize(
    row: dict[str, Any],
    stats_by_id: dict[str, dict[str, Any]] | None = None,
    skills_by_id: dict[str, list[dict[str, Any]]] | None = None,
    traits_by_id: dict[str, list[dict[str, Any]]] | None = None,
    inventory_by_id: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    cid = _cid(row)
    return {
        "character_id": cid,
        "name": _name(row),
        "owner_discord_id": _owner(row),
        "portrait_url": _portrait(row),
        "status": row.get("status"),
        "is_active": row.get("is_active"),
        "species": row.get("species") or row.get("race"),
        "origin": row.get("origin"),
        "faction": row.get("faction") or row.get("guild"),
        "title": row.get("title") or row.get("class") or row.get("profession"),
        "pronouns": row.get("pronouns"),
        "blurb": row.get("blurb") or row.get("summary") or row.get("description"),
        "stats": (stats_by_id or {}).get(cid) or _stats_from_character(row),
        "skills": (skills_by_id or {}).get(cid, []),
        "traits": (traits_by_id or {}).get(cid, []),
        "inventory": (inventory_by_id or {}).get(cid, []),
    }


@router.get("/characters")
def list_registry_characters(
    search: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=250),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()
    rows = _safe_rows(sb, "characters", limit=250)

    query = search.strip().lower()
    filtered: list[dict[str, Any]] = []

    for row in rows:
        status = str(row.get("status") or row.get("approval_status") or "").lower()
        if status and status not in {"approved", "active", "published", "registered"}:
            continue
        if row.get("is_active") is False:
            continue

        haystack = " ".join(
            str(value or "")
            for value in [
                _name(row), _owner(row), row.get("species"), row.get("race"), row.get("origin"),
                row.get("faction"), row.get("guild"), row.get("title"), row.get("class"),
                row.get("profession"),
            ]
        ).lower()

        if query and query not in haystack:
            continue

        filtered.append(row)

    filtered = filtered[:limit]
    ids = [_cid(row) for row in filtered if _cid(row)]

    characters = [
        _normalize(
            row,
            stats_by_id=_stats(sb, ids),
            skills_by_id=_skills(sb, ids),
            traits_by_id=_traits(sb, ids),
        )
        for row in filtered
    ]

    return {"characters": characters, "count": len(characters)}


@router.get("/characters/{character_id}")
def get_registry_character(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()
    row = _safe_one(sb, "characters", "character_id", character_id) or _safe_one(sb, "characters", "id", character_id)

    if not row:
        raise HTTPException(status_code=404, detail="Character not found.")

    cid = _cid(row) or character_id
    ids = [cid]

    return {
        "character": _normalize(
            row,
            stats_by_id=_stats(sb, ids),
            skills_by_id=_skills(sb, ids),
            traits_by_id=_traits(sb, ids),
            inventory_by_id=_inventory(sb, ids),
        )
    }
