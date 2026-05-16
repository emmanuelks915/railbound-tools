from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/registry", tags=["registry"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_execute(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _safe_select(sb, table: str, select: str = "*", *, limit: int = 250, guild_scoped: bool = True) -> list[dict[str, Any]]:
    if guild_scoped:
        rows = _safe_execute(
            sb.table(table)
            .select(select)
            .eq("guild_id", get_guild_id())
            .limit(limit)
        )
        if rows:
            return rows

    return _safe_execute(sb.table(table).select(select).limit(limit))


def _safe_select_for_ids(
    sb,
    table: str,
    id_column: str,
    character_ids: list[str],
    select: str = "*",
    *,
    limit: int = 1000,
    guild_scoped: bool = True,
) -> list[dict[str, Any]]:
    if not character_ids:
        return []

    if guild_scoped:
        rows = _safe_execute(
            sb.table(table)
            .select(select)
            .eq("guild_id", get_guild_id())
            .in_(id_column, character_ids)
            .limit(limit)
        )
        if rows:
            return rows

    return _safe_execute(
        sb.table(table)
        .select(select)
        .in_(id_column, character_ids)
        .limit(limit)
    )


def _safe_select_one(sb, table: str, id_column: str, character_id: str, select: str = "*") -> dict[str, Any] | None:
    rows = _safe_execute(
        sb.table(table)
        .select(select)
        .eq("guild_id", get_guild_id())
        .eq(id_column, character_id)
        .limit(1)
    )

    if not rows:
        rows = _safe_execute(
            sb.table(table)
            .select(select)
            .eq(id_column, character_id)
            .limit(1)
        )

    return rows[0] if rows else None


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
    return str(row.get("name") or row.get("oc_name") or row.get("character_name") or "Unnamed Citizen")


def _first_value(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _portrait_url(row: dict[str, Any]) -> str | None:
    value = _first_value(row, ["portrait_url", "image_url", "avatar_url", "profile_image_url", "faceclaim_url"])
    return str(value) if value else None


def _sheet_url(row: dict[str, Any]) -> str | None:
    value = _first_value(row, ["sheet_url", "character_sheet_url", "sheet_link", "profile_url", "doc_url", "google_doc_url"])
    return str(value) if value else None


def _occupation(row: dict[str, Any]) -> str | None:
    value = _first_value(row, ["occupation", "profession", "job", "class", "role", "title"])
    return str(value) if value else None


def _affiliation(row: dict[str, Any]) -> str | None:
    value = _first_value(row, ["affiliation", "guild", "faction", "company", "company_name", "organization", "crew"])
    return str(value) if value else None


def _origin(row: dict[str, Any]) -> str | None:
    value = _first_value(row, ["origin", "hometown", "region", "city", "nation"])
    return str(value) if value else None


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
        "hometown",
        "region",
        "city",
        "nation",
        "affiliation",
        "guild",
        "faction",
        "company",
        "company_name",
        "occupation",
        "profession",
        "job",
        "class",
        "role",
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
        "sheet_url",
        "character_sheet_url",
        "sheet_link",
        "profile_url",
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


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        raw = str(value)
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _iso(value: Any) -> str | None:
    parsed = _parse_dt(value)
    return parsed.isoformat() if parsed else (str(value) if value else None)


def _public_recent_posts(sb, character_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    rows = _first_nonempty_source(
        sb,
        character_ids,
        [
            ("rp_posts", "character_id"),
            ("rp_messages", "character_id"),
            ("rp_activity", "character_id"),
            ("rp_logs", "character_id"),
        ],
    )

    cleaned: list[dict[str, Any]] = []
    for row in rows:
        cid = str(row.get("character_id") or row.get("oc_id") or "")
        if not cid:
            continue

        created_at = (
            row.get("created_at")
            or row.get("timestamp")
            or row.get("posted_at")
            or row.get("message_created_at")
        )

        channel_label = (
            row.get("channel_name")
            or row.get("thread_name")
            or row.get("scene_name")
            or row.get("location")
            or row.get("channel_id")
            or "Unknown location"
        )

        snippet = (
            row.get("snippet")
            or row.get("preview")
            or row.get("content")
            or row.get("message_content")
            or ""
        )

        cleaned.append(
            {
                "character_id": cid,
                "created_at": _iso(created_at),
                "channel_label": str(channel_label),
                "jump_url": row.get("jump_url") or row.get("post_url") or row.get("message_url"),
                "words": row.get("word_count") or row.get("words"),
                "snippet": str(snippet)[:260],
            }
        )

    cleaned.sort(key=lambda item: _parse_dt(item.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    grouped = _group_by_character(cleaned)

    return {cid: posts[:8] for cid, posts in grouped.items()}


def _last_seen_from_posts(posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not posts:
        return None

    latest = posts[0]
    return {
        "at": latest.get("created_at"),
        "label": latest.get("channel_label") or "Unknown location",
        "jump_url": latest.get("jump_url"),
    }


def _activity_status(last_seen: dict[str, Any] | None) -> str:
    if not last_seen or not last_seen.get("at"):
        return "Unknown"

    parsed = _parse_dt(last_seen.get("at"))
    if not parsed:
        return "Unknown"

    now = datetime.now(timezone.utc)
    age_days = (now - parsed).days

    if age_days <= 30:
        return "Active"
    if age_days <= 90:
        return "Quiet"
    return "Inactive"


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
            rows = _safe_execute(
                sb.table(table)
                .select("*")
                .eq("guild_id", get_guild_id())
                .in_(id_column, list(owner_ids))
                .limit(500)
            )

            if not rows:
                rows = _safe_execute(
                    sb.table(table)
                    .select("*")
                    .in_(id_column, list(owner_ids))
                    .limit(500)
                )

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

    rows = _safe_execute(
        sb.table("skill_definitions")
        .select("skill_key,name,tree,tier,cost,description")
        .eq("guild_id", get_guild_id())
        .in_("skill_key", skill_keys)
    )

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
    recent_posts_by_id: dict[str, list[dict[str, Any]]] | None = None,
    users_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cid = _character_id(row)
    owner_id = _owner_id(row)
    owner_user = (users_by_id or {}).get(str(owner_id)) if owner_id else None
    stats = (stats_by_id or {}).get(cid) or _extract_stats_from_character(row)
    recent_posts = (recent_posts_by_id or {}).get(cid, [])
    last_seen = _last_seen_from_posts(recent_posts)

    return {
        "character_id": cid,
        "name": _character_name(row),
        "owner_discord_id": owner_id,
        "owner_display_name": _display_name_for_user(owner_user, owner_id),
        "portrait_url": _portrait_url(row),
        "sheet_url": _sheet_url(row),
        "status": _activity_status(last_seen),
        "approval_status": row.get("status") or row.get("approval_status"),
        "is_active": row.get("is_active"),
        "species": row.get("species") or row.get("race"),
        "origin": _origin(row),
        "affiliation": _affiliation(row),
        "occupation": _occupation(row),
        "title": row.get("title"),
        "pronouns": row.get("pronouns"),
        "blurb": row.get("blurb") or row.get("summary") or row.get("description"),
        "last_seen": last_seen,
        "recent_posts": recent_posts,
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
        approval_status = str(row.get("status") or row.get("approval_status") or "").lower()
        if approval_status and approval_status not in {"approved", "active", "published", "registered"}:
            continue

        if row.get("is_active") is False:
            continue

        haystack = " ".join(
            str(value or "")
            for value in [
                _character_name(row),
                _owner_id(row),
                _occupation(row),
                _affiliation(row),
                _origin(row),
                row.get("species"),
                row.get("race"),
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
    recent_posts_by_id = _public_recent_posts(sb, character_ids)

    characters = [
        _normalize_character(
            row,
            stats_by_id=stats_by_id,
            skills_by_id=skills_by_id,
            traits_by_id=traits_by_id,
            recent_posts_by_id=recent_posts_by_id,
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
    recent_posts_by_id = _public_recent_posts(sb, character_ids)

    return {
        "character": _normalize_character(
            row,
            stats_by_id=stats_by_id,
            skills_by_id=skills_by_id,
            traits_by_id=traits_by_id,
            inventory_by_id=inventory_by_id,
            recent_posts_by_id=recent_posts_by_id,
            users_by_id=users_by_id,
        )
    }
