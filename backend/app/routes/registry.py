from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import uuid
import urllib.request
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile

from app.security import actor_from_header
from app.permissions import is_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase
from app.utils.activity_webhooks import send_staff_activity_webhook
from app.utils.activity_logger import log_activity

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


def _channel_label_from_row(row: dict[str, Any]) -> str | None:
    for key in (
        "channel_name",
        "thread_name",
        "scene_name",
        "location_name",
        "location",
        "name",
        "title",
        "label",
    ):
        value = row.get(key)
        if value:
            return str(value)

    return None


def _channel_label_lookup(sb, channel_ids: set[str]) -> dict[str, str]:
    if not channel_ids:
        return {}

    labels: dict[str, str] = {}

    sources = [
        ("rp_channels", ["channel_id", "discord_channel_id", "id"]),
        ("rp_scenes", ["channel_id", "discord_channel_id", "thread_id", "id"]),
        ("rp_threads", ["thread_id", "channel_id", "discord_channel_id", "id"]),
        ("rp_locations", ["channel_id", "discord_channel_id", "id"]),
        ("channels", ["channel_id", "discord_channel_id", "id"]),
    ]

    for table, id_columns in sources:
        for id_column in id_columns:
            rows = _safe_execute(
                sb.table(table)
                .select("*")
                .eq("guild_id", get_guild_id())
                .in_(id_column, list(channel_ids))
                .limit(500)
            )

            if not rows:
                rows = _safe_execute(
                    sb.table(table)
                    .select("*")
                    .in_(id_column, list(channel_ids))
                    .limit(500)
                )

            for row in rows:
                channel_id = str(row.get(id_column) or "")
                label = _channel_label_from_row(row)

                if channel_id and label:
                    labels[channel_id] = label

            if labels:
                return labels

    return labels


def _discord_channel_lookup(channel_ids: set[str]) -> dict[str, str]:
    if not channel_ids:
        return {}

    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not token:
        return {}

    labels: dict[str, str] = {}

    for channel_id in channel_ids:
        try:
            request = urllib.request.Request(
                f"https://discord.com/api/v10/channels/{channel_id}",
                method="GET",
                headers={
                    "Authorization": f"Bot {token}",
                    "Accept": "application/json",
                    "User-Agent": "RailboundToolsRegistry/1.0",
                },
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))

            label = payload.get("name")
            if label:
                labels[str(channel_id)] = str(label)
        except Exception:
            continue

    return labels

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

    channel_ids: set[str] = set()
    for row in rows:
        for key in ("channel_id", "discord_channel_id", "thread_id", "parent_channel_id", "scene_channel_id"):
            value = row.get(key)
            if value:
                channel_ids.add(str(value))

    channel_labels = _channel_label_lookup(sb, channel_ids)

    # Optional live Discord fallback if DISCORD_BOT_TOKEN is set in backend env.
    missing_ids = {cid for cid in channel_ids if cid not in channel_labels}
    channel_labels.update(_discord_channel_lookup(missing_ids))

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

        channel_id = (
            row.get("channel_id")
            or row.get("discord_channel_id")
            or row.get("thread_id")
            or row.get("parent_channel_id")
            or row.get("scene_channel_id")
        )
        channel_id = str(channel_id) if channel_id else None

        direct_label = (
            row.get("channel_name")
            or row.get("thread_name")
            or row.get("scene_name")
            or row.get("location")
            or row.get("location_name")
            or row.get("area")
            or row.get("region")
        )

        channel_label = (
            str(direct_label)
            if direct_label
            else channel_labels.get(channel_id or "")
            if channel_id
            else None
        )

        # Final fallback. This is intentionally better than "Unknown location",
        # and tells us exactly which channel needs a stored/display name later.
        if not channel_label:
            channel_label = f"Channel {channel_id}" if channel_id else "Unknown location"

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
                "channel_id": channel_id,
                "channel_label": channel_label,
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
    """Collect all public stats for each character.

    Earlier versions used _first_nonempty_source(), which meant if character_stats
    had Strength/Dexterity/Stamina, the registry stopped there and never checked
    derived stat tables. This merges every known stat source so the public file can
    show core stats plus derived stats.
    """
    sources = [
        ("character_stats", "character_id"),
        ("oc_stats", "character_id"),
        ("stats", "character_id"),
        ("derived_stats", "character_id"),
        ("character_derived_stats", "character_id"),
        ("oc_derived_stats", "character_id"),
        ("character_stat_values", "character_id"),
        ("stat_values", "character_id"),
    ]

    stats: dict[str, dict[str, Any]] = {}

    hidden_keys = {
        "id",
        "guild_id",
        "character_id",
        "oc_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "source",
        "notes",
    }

    key_columns = [
        "stat_key",
        "key",
        "name",
        "stat_name",
        "derived_key",
        "derived_stat",
        "label",
    ]

    value_columns = [
        "stat_value",
        "value",
        "amount",
        "score",
        "total",
        "computed_value",
        "calculated_value",
    ]

    for table, id_column in sources:
        rows = _safe_select_for_ids(sb, table, id_column, character_ids)

        for row in rows:
            cid = str(row.get("character_id") or row.get("oc_id") or row.get("id") or "")
            if not cid:
                continue

            bucket = stats.setdefault(cid, {})

            # Row-style tables:
            # character_id | stat_key | stat_value
            stat_key = None
            for key_col in key_columns:
                if row.get(key_col) not in (None, ""):
                    stat_key = str(row.get(key_col))
                    break

            stat_value = None
            for value_col in value_columns:
                if row.get(value_col) is not None:
                    stat_value = row.get(value_col)
                    break

            if stat_key and stat_value is not None:
                bucket[stat_key] = stat_value
                continue

            # Wide-row tables:
            # character_id | strength | dexterity | stamina | safe_output...
            for key, value in row.items():
                if key in hidden_keys:
                    continue
                if value is None or isinstance(value, (dict, list)):
                    continue

                # Do not leak internal UUID-ish foreign keys as stats.
                if key.endswith("_id"):
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
    owned_rows: list[dict[str, Any]] = []

    # Ownership tables usually store only character_id + trait_id. The public registry
    # needs to resolve those IDs through the trait catalog before rendering names.
    for table in ("character_traits", "oc_traits"):
        owned_rows.extend(_safe_select_for_ids(sb, table, "character_id", character_ids))

    if not owned_rows:
        legacy_rows = _safe_select_for_ids(sb, "traits", "character_id", character_ids)
        cleaned = []
        for row in legacy_rows:
            cleaned.append(
                {
                    "character_id": str(row.get("character_id") or row.get("oc_id") or ""),
                    "trait_id": row.get("trait_id"),
                    "slug": row.get("slug") or row.get("trait_slug") or row.get("trait_key"),
                    "name": row.get("name") or row.get("trait_name") or row.get("trait_key") or "Trait",
                    "description": row.get("description") or row.get("summary"),
                    "type": row.get("tier") or row.get("type") or row.get("trait_type"),
                    "tier": row.get("tier"),
                    "category": row.get("category") or row.get("trait_type"),
                    "cost": row.get("cost") or row.get("point_value"),
                }
            )
        return _group_by_character(cleaned)

    trait_ids = list(
        dict.fromkeys(
            str(row.get("trait_id"))
            for row in owned_rows
            if row.get("trait_id")
        )
    )
    slugs = list(
        dict.fromkeys(
            str(row.get(key))
            for row in owned_rows
            for key in ("slug", "trait_slug", "trait_key")
            if row.get(key)
        )
    )

    trait_by_id: dict[str, dict[str, Any]] = {}
    trait_by_slug: dict[str, dict[str, Any]] = {}

    def remember_trait(row: dict[str, Any]) -> None:
        if row.get("trait_id"):
            trait_by_id[str(row.get("trait_id"))] = row

        for key in ("slug", "trait_slug", "trait_key"):
            value = row.get(key)
            if value:
                trait_by_slug[str(value)] = row

    if trait_ids:
        catalog_rows = _safe_execute(
            sb.table("traits")
            .select("*")
            .eq("guild_id", get_guild_id())
            .in_("trait_id", trait_ids)
            .limit(1000)
        )

        if not catalog_rows:
            catalog_rows = _safe_execute(
                sb.table("traits")
                .select("*")
                .in_("trait_id", trait_ids)
                .limit(1000)
            )

        for trait in catalog_rows:
            remember_trait(trait)

    if slugs:
        catalog_rows = _safe_execute(
            sb.table("traits")
            .select("*")
            .eq("guild_id", get_guild_id())
            .in_("slug", slugs)
            .limit(1000)
        )

        if not catalog_rows:
            catalog_rows = _safe_execute(
                sb.table("traits")
                .select("*")
                .in_("slug", slugs)
                .limit(1000)
            )

        trait_key_rows = _safe_execute(
            sb.table("traits")
            .select("*")
            .eq("guild_id", get_guild_id())
            .in_("trait_key", slugs)
            .limit(1000)
        )

        for trait in [*catalog_rows, *trait_key_rows]:
            remember_trait(trait)

    cleaned = []
    seen: set[tuple[str, str]] = set()

    for row in owned_rows:
        cid = str(row.get("character_id") or row.get("oc_id") or "")
        if not cid:
            continue

        definition = None
        trait_id = str(row.get("trait_id")) if row.get("trait_id") else ""

        if trait_id:
            definition = trait_by_id.get(trait_id)

        if not definition:
            for key in ("slug", "trait_slug", "trait_key"):
                value = row.get(key)
                if value and str(value) in trait_by_slug:
                    definition = trait_by_slug[str(value)]
                    break

        source = definition or row
        slug = (
            source.get("slug")
            or source.get("trait_slug")
            or source.get("trait_key")
            or row.get("slug")
            or row.get("trait_slug")
            or row.get("trait_key")
        )
        name = (
            source.get("name")
            or source.get("display_name")
            or row.get("trait_name")
            or slug
            or "Trait"
        )
        marker = str(source.get("trait_id") or trait_id or slug or name)
        dedupe_key = (cid, marker)

        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        cleaned.append(
            {
                "character_id": cid,
                "trait_id": source.get("trait_id") or row.get("trait_id"),
                "slug": slug,
                "name": name,
                "description": source.get("description") or source.get("summary") or row.get("description"),
                "type": source.get("tier") or source.get("trait_type") or source.get("type") or row.get("type"),
                "tier": source.get("tier"),
                "category": source.get("category") or source.get("trait_type"),
                "cost": source.get("cost") or source.get("point_value"),
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


def _to_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _nice_number(value: float) -> int | float:
    rounded = round(float(value), 2)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _with_computed_derived_stats(stats: dict[str, Any]) -> dict[str, Any]:
    merged = dict(stats or {})

    strength = _to_float(merged.get("strength"))
    dexterity = _to_float(merged.get("dexterity"))
    stamina = _to_float(merged.get("stamina"))
    affinity = _to_float(merged.get("magic_affinity") or merged.get("affinity"))
    mana = _to_float(merged.get("mana"))

    fortitude = stamina * 1.25

    computed = {
        "reaction_score": dexterity * 1.5,
        "dodge": dexterity * 1.25,
        "fortitude": fortitude,
        "safe_output": fortitude * 1.15,
        "magic_safe_output": (fortitude * 0.6) + (mana * 0.8),
        "action_points": 1 + (fortitude / 150),
        "carry_capacity": 4 + (strength / 150),
        "heavy_attack_power": (strength * 1.1) + (dexterity * 0.35),
        "heavy_attack_speed": min(dexterity * 1.25, fortitude),
        "precision_attack_power": (dexterity * 0.65) + (strength * 0.4),
        "precision_attack_speed": min(dexterity * 1.25, fortitude),
        "magic_attack_power": (affinity * 0.9) + (mana * 0.6),
        "magic_attack_speed": min(affinity * 1.4, fortitude + (mana * 0.25)),
        "grapple_power": (strength * 1.2) + (stamina + 0.6),
        "escape_power": strength + stamina,
    }

    for key, value in computed.items():
        if key not in merged or merged.get(key) in (None, ""):
            merged[key] = _nice_number(value)

    return merged

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
    stats = _with_computed_derived_stats((stats_by_id or {}).get(cid) or _extract_stats_from_character(row))
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


PUBLIC_PROFILE_FIELDS = {
    "occupation": 80,
    "affiliation": 120,
    "sheet_url": 500,
    "portrait_url": 500,
    "blurb": 1200,
}


def _clean_public_profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    for key, max_len in PUBLIC_PROFILE_FIELDS.items():
        if key not in payload:
            continue

        value = payload.get(key)

        if value is None:
            cleaned[key] = None
            continue

        value = str(value).strip()

        if not value:
            cleaned[key] = None
            continue

        cleaned[key] = value[:max_len]

    return cleaned


@router.patch("/characters/{character_id}/profile")
def update_registry_character_profile(
    character_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()

    row = _safe_select_one(sb, "characters", "character_id", character_id)
    target_column = "character_id"

    if not row:
        row = _safe_select_one(sb, "characters", "id", character_id)
        target_column = "id"

    if not row:
        raise HTTPException(status_code=404, detail="Character not found.")

    owner_id = _owner_id(row)
    actor_is_owner = owner_id is not None and str(owner_id) == str(actor_discord_id)
    actor_is_staff = is_staff(int(actor_discord_id))

    if not actor_is_owner and not actor_is_staff:
        raise HTTPException(status_code=403, detail="You can only edit your own public OC profile.")

    cleaned = _clean_public_profile_payload(payload)

    if not cleaned:
        raise HTTPException(status_code=400, detail="No public profile fields were provided.")

    query = sb.table("characters").update(cleaned).eq(target_column, character_id)
    if row.get("guild_id") is not None:
        query = query.eq("guild_id", get_guild_id())

    updated_rows = _as_list(query.execute())

    updated = updated_rows[0] if updated_rows else _safe_select_one(sb, "characters", target_column, character_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Profile updated, but the updated character could not be reloaded.")

    cid = _character_id(updated)
    character_ids = [cid] if cid else [character_id]
    owner_id = _owner_id(updated)
    users_by_id = _user_lookup(sb, {str(owner_id)} if owner_id else set())

    stats_by_id = _public_stat_rows(sb, character_ids)
    skills_by_id = _public_skill_rows(sb, character_ids)
    traits_by_id = _public_trait_rows(sb, character_ids)
    inventory_by_id = _public_inventory_rows(sb, character_ids)
    recent_posts_by_id = _public_recent_posts(sb, character_ids)

    return {
        "character": _normalize_character(
            updated,
            stats_by_id=stats_by_id,
            skills_by_id=skills_by_id,
            traits_by_id=traits_by_id,
            inventory_by_id=inventory_by_id,
            recent_posts_by_id=recent_posts_by_id,
            users_by_id=users_by_id,
        )
    }


def _public_url_for_storage_path(sb, bucket: str, path: str) -> str:
    public_url = sb.storage.from_(bucket).get_public_url(path)

    if isinstance(public_url, str):
        return public_url

    if isinstance(public_url, dict):
        return str(public_url.get("publicUrl") or public_url.get("public_url") or public_url.get("signedURL") or "")

    return str(public_url)


@router.post("/characters/{character_id}/portrait")
async def upload_registry_character_portrait(
    character_id: str,
    file: UploadFile = File(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()

    row = _safe_select_one(sb, "characters", "character_id", character_id)
    target_column = "character_id"

    if not row:
        row = _safe_select_one(sb, "characters", "id", character_id)
        target_column = "id"

    if not row:
        raise HTTPException(status_code=404, detail="Character not found.")

    owner_id = _owner_id(row)
    actor_is_owner = owner_id is not None and str(owner_id) == str(actor_discord_id)
    actor_is_staff = is_staff(int(actor_discord_id))

    if not actor_is_owner and not actor_is_staff:
        raise HTTPException(status_code=403, detail="You can only edit your own public OC profile.")

    content_type = (file.content_type or "").lower()
    allowed_types = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }

    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Please upload a PNG, JPG, WEBP, or GIF image.")

    raw = await file.read()

    max_bytes = 5 * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=400, detail="Portrait image must be 5 MB or smaller.")

    bucket = os.getenv("CHARACTER_PORTRAIT_BUCKET") or os.getenv("SUPABASE_STORAGE_BUCKET") or "shop-images"
    ext = allowed_types[content_type]
    storage_path = f"character-portraits/{get_guild_id()}/{character_id}/{uuid.uuid4().hex}{ext}"

    try:
        sb.storage.from_(bucket).upload(
            storage_path,
            raw,
            {
                "content-type": content_type,
                "upsert": "true",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not upload portrait image: {exc}")

    portrait_url = _public_url_for_storage_path(sb, bucket, storage_path)
    if not portrait_url:
        raise HTTPException(status_code=500, detail="Portrait uploaded, but no public URL was returned.")

    query = sb.table("characters").update({"portrait_url": portrait_url}).eq(target_column, character_id)
    if row.get("guild_id") is not None:
        query = query.eq("guild_id", get_guild_id())

    updated_rows = _as_list(query.execute())
    updated = updated_rows[0] if updated_rows else _safe_select_one(sb, "characters", target_column, character_id)

    if not updated:
        raise HTTPException(status_code=500, detail="Portrait uploaded, but the character could not be reloaded.")

    cid = _character_id(updated)
    character_ids = [cid] if cid else [character_id]
    owner_id = _owner_id(updated)
    users_by_id = _user_lookup(sb, {str(owner_id)} if owner_id else set())

    stats_by_id = _public_stat_rows(sb, character_ids)
    skills_by_id = _public_skill_rows(sb, character_ids)
    traits_by_id = _public_trait_rows(sb, character_ids)
    inventory_by_id = _public_inventory_rows(sb, character_ids)
    recent_posts_by_id = _public_recent_posts(sb, character_ids)

    return {
        "portrait_url": portrait_url,
        "character": _normalize_character(
            updated,
            stats_by_id=stats_by_id,
            skills_by_id=skills_by_id,
            traits_by_id=traits_by_id,
            inventory_by_id=inventory_by_id,
            recent_posts_by_id=recent_posts_by_id,
            users_by_id=users_by_id,
        ),
    }
