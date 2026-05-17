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


def _safe_select(sb, table: str, select: str = "*", *, limit: int = 250) -> list[dict[str, Any]]:
    try:
        return _as_list(
            sb.table(table)
            .select(select)
            .eq("guild_id", get_guild_id())
            .limit(limit)
            .execute()
        )
    except Exception:
        return []


def _safe_select_for_ids(
    sb,
    table: str,
    id_column: str,
    character_ids: list[str],
    select: str = "*",
    *,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    if not character_ids:
        return []

    try:
        return _as_list(
            sb.table(table)
            .select(select)
            .eq("guild_id", get_guild_id())
            .in_(id_column, character_ids)
            .limit(limit)
            .execute()
        )
    except Exception:
        return []


def _safe_select_one(sb, table: str, id_column: str, character_id: str, select: str = "*") -> dict[str, Any] | None:
    try:
        rows = _as_list(
            sb.table(table)
            .select(select)
            .eq("guild_id", get_guild_id())
            .eq(id_column, character_id)
            .limit(1)
            .execute()
        )
        return rows[0] if rows else None
    except Exception:
        return None


def _character_id(row: dict[str, Any]) -> str:
    return str(row.get("character_id") or row.get("id") or "")


def _owner_id(row: dict[str, Any]) -> str | None:
    value = (
        row.get("user_id")
        or row.get("discord_id")
        or row.get("owner_discord_id")
        or row.get("player_discord_id")
        or row.get("created_by_discord_id")
    )
    return str(value) if value is not None else None


def _character_name(row: dict[str, Any]) -> str:
    return str(row.get("name") or row.get("oc_name") or row.get("character_name") or "Unnamed OC")


def _portrait_url(row: dict[str, Any]) -> str | None:
    for key in ("portrait_url", "image_url", "avatar_url", "profile_image_url", "faceclaim_url"):
        value = row.get(key)
        if value:
            return str(value)
    return None


def _pick_public_fields(row: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = [
        "character_id",
        "id",
        "name",
        "oc_name",
        "character_name",
        "user_id",
        "discord_id",
        "owner_discord_id",
        "player_discord_id",
        "status",
        "is_active",
        "species",
        "race",
        "origin",
        "faction",
        "guild",
        "class",
        "profession",
        "title",
        "age",
        "pronouns",
        "blurb",
        "summary",
        "description",
        "portrait_url",
        "image_url",
        "avatar_url",
        "profile_image_url",
        "faceclaim_url",
        "xp",
        "current_xp",
        "available_xp",
        "spent_xp",
        "total_xp",
        "strength",
        "dexterity",
        "stamina",
        "magic_affinity",
        "mana",
        "created_at",
        "updated_at",
    ]
    return {key: row.get(key) for key in allowed_keys if key in row}


def _extract_stats_from_character(row: dict[str, Any]) -> dict[str, Any]:
    stat_keys = [
        "strength",
        "dexterity",
        "stamina",
        "magic_affinity",
        "mana",
        "hp",
        "health",
        "speed",
        "dodge",
        "blitz",
        "carry_capacity",
        "safe_output",
        "fortitude",
        "reaction_score",
        "current_xp",
        "available_xp",
        "spent_xp",
        "total_xp",
        "xp",
    ]
    return {key: row.get(key) for key in stat_keys if row.get(key) is not None}


def _group_by_character(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        cid = str(row.get("character_id") or row.get("oc_id") or row.get("id") or "")
        if not cid:
            continue
        grouped.setdefault(cid, []).append(row)

    return grouped


def _first_nonempty_source(sb, character_ids: list[str], sources: list[tuple[str, str]]) -> list[dict[str, Any]]:
    for table, id_column in sources:
        rows = _safe_select_for_ids(sb, table, id_column, character_ids)
        if rows:
            return rows
    return []


def _user_lookup(sb, owner_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not owner_ids:
        return {}

    lookup: dict[str, dict[str, Any]] = {}

    possible_tables = [
        "users",
        "discord_users",
        "profiles",
        "user_profiles",
    ]

    possible_id_columns = [
        "discord_id",
        "user_id",
        "id",
    ]

    for table in possible_tables:
        for id_column in possible_id_columns:
            try:
                rows = _as_list(
                    sb.table(table)
                    .select("*")
                    .eq("guild_id", get_guild_id())
                    .in_(id_column, list(owner_ids))
                    .limit(500)
                    .execute()
                )
            except Exception:
                continue

            for row in rows:
                owner_id = str(row.get(id_column) or "")
                if owner_id:
                    lookup[owner_id] = row

            if lookup:
                return lookup

    return {}


def _display_name_for_user(user: dict[str, Any] | None, fallback_id: str | None) -> str | None:
    if not user:
        return fallback_id

    for key in (
        "display_name",
        "global_name",
        "username",
        "discord_username",
        "name",
        "nickname",
    ):
        value = user.get(key)
        if value:
            return str(value)

    return fallback_id


def _public_stat_rows(sb, character_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows = _first_nonempty_source(
        sb,
        character_ids,
        [
            ("character_stats", "character_id"),
            ("oc_stats", "character_id"),
            ("stats", "character_id"),
            ("derived_stats", "character_id"),
            ("character_derived_stats", "character_id"),
        ],
    )

    stats: dict[str, dict[str, Any]] = {}

    hidden_keys = {
        "id",
        "guild_id",
        "character_id",
        "oc_id",
        "created_at",
        "updated_at",
    }

    for row in rows:
        cid = str(row.get("character_id") or row.get("oc_id") or "")
        if not cid:
            continue

        bucket = stats.setdefault(cid, {})

        # Supports row-style stats:
        # character_id | stat_key | stat_value
        stat_key = (
            row.get("stat_key")
            or row.get("key")
            or row.get("name")
            or row.get("stat_name")
        )
        stat_value = (
            row.get("stat_value")
            if row.get("stat_value") is not None
            else row.get("value")
            if row.get("value") is not None
            else row.get("amount")
        )

        if stat_key and stat_value is not None:
            bucket[str(stat_key)] = stat_value
            continue

        # Supports wide-row stats:
        # character_id | strength | dexterity | stamina...
        for key, value in row.items():
            if key in hidden_keys:
                continue
            if value is None or isinstance(value, (dict, list)):
                continue
            bucket[key] = value

    return stats


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


def _public_skill_rows(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_nonempty_source(
        sb,
        character_ids,
        [
            ("character_skills", "character_id"),
            ("oc_skills", "character_id"),
            ("character_owned_skills", "character_id"),
            ("owned_skills", "character_id"),
        ],
    )

    skill_keys = sorted({str(row.get("skill_key")) for row in rows if row.get("skill_key")})
    definitions = _skill_definitions(sb, skill_keys)

    out: list[dict[str, Any]] = []
    for row in rows:
        skill_key = str(row.get("skill_key") or "")
        definition = definitions.get(skill_key) or {}
        out.append(
            {
                "character_id": str(row.get("character_id") or row.get("oc_id") or ""),
                "skill_key": skill_key,
                "name": definition.get("name") or row.get("name") or skill_key,
                "tree": definition.get("tree") or row.get("tree"),
                "tier": definition.get("tier") or row.get("tier"),
                "cost": definition.get("cost") or row.get("cost"),
                "description": definition.get("description") or row.get("description"),
                "created_at": row.get("created_at"),
                "status": row.get("status"),
            }
        )

    return _group_by_character(out)


def _public_trait_rows(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_nonempty_source(
        sb,
        character_ids,
        [
            ("character_traits", "character_id"),
            ("oc_traits", "character_id"),
            ("traits", "character_id"),
        ],
    )

    cleaned = []
    for row in rows:
        cleaned.append(
            {
                "character_id": str(row.get("character_id") or row.get("oc_id") or ""),
                "name": row.get("name") or row.get("trait_name") or row.get("trait_key") or "Trait",
                "description": row.get("description") or row.get("summary"),
                "type": row.get("type") or row.get("trait_type"),
            }
        )

    return _group_by_character(cleaned)


def _public_inventory_rows(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_nonempty_source(
        sb,
        character_ids,
        [
            ("character_inventory", "character_id"),
            ("oc_inventory", "character_id"),
            ("inventory", "character_id"),
        ],
    )

    cleaned = []
    for row in rows:
        cleaned.append(
            {
                "character_id": str(row.get("character_id") or row.get("oc_id") or ""),
                "name": row.get("name") or row.get("item_name") or row.get("item_key") or "Item",
                "quantity": row.get("quantity") or row.get("amount") or 1,
                "description": row.get("description"),
                "type": row.get("type") or row.get("item_type"),
            }
        )

    return _group_by_character(cleaned)


def _normalize_character(
    row: dict[str, Any],
    *,
    stats_by_id: dict[str, dict[str, Any]] | None = None,
    skills_by_id: dict[str, list[dict[str, Any]]] | None = None,
    traits_by_id: dict[str, list[dict[str, Any]]] | None = None,
    inventory_by_id: dict[str, list[dict[str, Any]]] | None = None,
    users_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cid = _character_id(row)
    owner_id = _owner_id(row)
    owner_user = (users_by_id or {}).get(str(owner_id)) if owner_id else None
    stats = (stats_by_id or {}).get(cid) or _extract_stats_from_character(row)

    return {
        "character_id": cid,
        "name": _character_name(row),
        "owner_discord_id": owner_id,
        "owner_display_name": _display_name_for_user(owner_user, owner_id),
        "portrait_url": _portrait_url(row),
        "status": row.get("status"),
        "is_active": row.get("is_active"),
        "species": row.get("species") or row.get("race"),
        "origin": row.get("origin"),
        "faction": row.get("faction") or row.get("guild"),
        "title": row.get("title") or row.get("class") or row.get("profession"),
        "pronouns": row.get("pronouns"),
        "blurb": row.get("blurb") or row.get("summary") or row.get("description"),
        "stats": stats or {},
        "skills": (skills_by_id or {}).get(cid, []),
        "traits": (traits_by_id or {}).get(cid, []),
        "inventory": (inventory_by_id or {}).get(cid, []),
        "public": _pick_public_fields(row),
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
    rows = _safe_select(sb, "characters", "*", limit=250)

    filtered: list[dict[str, Any]] = []
    search_text = search.strip().lower()

    for row in rows:
        status = str(row.get("status") or row.get("approval_status") or "").lower()
        if status and status not in {"approved", "active", "published", "registered"}:
            continue

        if row.get("is_active") is False:
            continue

        haystack = " ".join(
            str(value or "")
            for value in [
                _character_name(row),
                _owner_id(row),
                row.get("species"),
                row.get("race"),
                row.get("origin"),
                row.get("faction"),
                row.get("guild"),
                row.get("title"),
                row.get("class"),
                row.get("profession"),
            ]
        ).lower()

        if search_text and search_text not in haystack:
            continue

        filtered.append(row)

    filtered = filtered[:limit]
    character_ids = [_character_id(row) for row in filtered if _character_id(row)]
    owner_ids = {str(_owner_id(row)) for row in filtered if _owner_id(row)}
    users_by_id = _user_lookup(sb, owner_ids)

    stats_by_id = _public_stat_rows(sb, character_ids)
    skills_by_id = _public_skill_rows(sb, character_ids)
    traits_by_id = _public_trait_rows(sb, character_ids)

    characters = [
        _normalize_character(
            row,
            stats_by_id=stats_by_id,
            skills_by_id=skills_by_id,
            traits_by_id=traits_by_id,
            users_by_id=users_by_id,
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

    row = _safe_select_one(sb, "characters", "character_id", character_id)
    if not row:
        row = _safe_select_one(sb, "characters", "id", character_id)

    if not row:
        raise HTTPException(status_code=404, detail="Character not found.")

    cid = _character_id(row)
    character_ids = [cid] if cid else [character_id]
    owner_id = _owner_id(row)
    users_by_id = _user_lookup(sb, {str(owner_id)} if owner_id else set())

    stats_by_id = _public_stat_rows(sb, character_ids)
    skills_by_id = _public_skill_rows(sb, character_ids)
    traits_by_id = _public_trait_rows(sb, character_ids)
    inventory_by_id = _public_inventory_rows(sb, character_ids)

    return {
        "character": _normalize_character(
            row,
            stats_by_id=stats_by_id,
            skills_by_id=skills_by_id,
            traits_by_id=traits_by_id,
            inventory_by_id=inventory_by_id,
            users_by_id=users_by_id,
        )
    }
