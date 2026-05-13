from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from postgrest.exceptions import APIError

from app.security import actor_from_header, require_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase, raise_clean_api_error

router = APIRouter(prefix="/api/activity", tags=["activity"])


def _first_value(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _activity_time(row: dict[str, Any]) -> str:
    return _safe_str(
        _first_value(
            row,
            [
                "paid_at",
                "reviewed_at",
                "approved_at",
                "denied_at",
                "updated_at",
                "created_at",
                "opened_at",
            ],
        )
    )


def _try_table_rows(sb, table_name: str, guild_id: int, limit: int) -> list[dict[str, Any]]:
    """
    Read a table if it exists. This makes Activity Log v1 tolerant while our schema evolves.
    Missing optional tables return [] instead of breaking the whole dashboard.
    """

    try:
        res = (
            sb.table(table_name)
            .select("*")
            .eq("guild_id", guild_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return sb_data(res) or []
    except APIError as e:
        message = str(e).lower()
        if "could not find the table" in message or "does not exist" in message or "schema cache" in message:
            return []
        raise_clean_api_error(e)


def _stat_activity(row: dict[str, Any]) -> dict[str, Any]:
    status = _safe_str(row.get("status") or "unknown").lower()
    total_cost = row.get("total_cost")

    if status in {"approved", "complete", "completed"}:
        title = "Stat request approved"
    elif status in {"denied", "rejected"}:
        title = "Stat request denied"
    elif status in {"cancelled", "canceled"}:
        title = "Stat request cancelled"
    else:
        title = "Stat request submitted"

    description_bits = []

    if total_cost is not None:
        description_bits.append(f"{total_cost} XP")

    character_id = row.get("character_id")
    if character_id:
        description_bits.append(f"Character: {character_id}")

    return {
        "id": f"stat:{row.get('request_id')}",
        "kind": "stat_request",
        "title": title,
        "status": row.get("status"),
        "description": " • ".join(description_bits) or "Stat upgrade request",
        "actor_discord_id": row.get("requested_by_discord_id") or row.get("created_by"),
        "time": _activity_time(row),
        "raw": row,
    }


def _shop_activity(row: dict[str, Any]) -> dict[str, Any]:
    status = _safe_str(row.get("review_status") or ("active" if row.get("is_active") else "draft")).lower()
    name = row.get("name") or "Unnamed listing"

    if status in {"approved", "active", "published"}:
        title = "Shop listing approved"
    elif status in {"denied", "rejected"}:
        title = "Shop listing denied"
    elif status in {"pending_staff_review", "pending", "submitted"}:
        title = "Shop listing submitted"
    else:
        title = "Shop listing updated"

    description_bits = [str(name)]

    if row.get("price") is not None:
        description_bits.append(f"{row.get('price')} coins")

    if row.get("stock") is not None:
        description_bits.append(f"Stock: {row.get('stock')}")

    return {
        "id": f"shop:{row.get('item_id')}",
        "kind": "shop_listing",
        "title": title,
        "status": row.get("review_status"),
        "description": " • ".join(description_bits),
        "actor_discord_id": row.get("submitted_by_discord_id") or row.get("reviewed_by"),
        "time": _activity_time(row),
        "raw": row,
    }


def _rp_claim_activity(row: dict[str, Any]) -> dict[str, Any]:
    status = _safe_str(row.get("status") or "unknown").lower()
    payout_status = _safe_str(row.get("payout_status") or "").lower()
    character_name = row.get("character_name") or "Unknown OC"

    if payout_status in {"paid", "complete", "completed"}:
        title = "RP XP claim paid"
    elif status in {"approved", "accepted"}:
        title = "RP XP claim approved"
    elif status in {"denied", "rejected"}:
        title = "RP XP claim denied"
    else:
        title = "RP XP claim submitted"

    description_bits = [
        str(character_name),
        f"{row.get('word_count') or 0} words",
        f"{row.get('post_count') or 0} posts",
        f"Estimated {row.get('estimated_xp') or 0} XP",
    ]

    if row.get("approved_xp") is not None:
        description_bits.append(f"Approved {row.get('approved_xp')} XP")

    return {
        "id": f"rp_claim:{row.get('claim_id')}",
        "kind": "rp_xp_claim",
        "title": title,
        "status": row.get("status"),
        "payout_status": row.get("payout_status"),
        "description": " • ".join(description_bits),
        "actor_discord_id": row.get("user_id") or row.get("created_by") or row.get("reviewed_by"),
        "time": _activity_time(row),
        "raw": row,
    }


def _skill_activity(table_name: str, row: dict[str, Any]) -> dict[str, Any]:
    status = _safe_str(row.get("status") or row.get("review_status") or "unknown").lower()
    skill_name = row.get("skill_name") or row.get("skill_key") or row.get("name") or "Unknown skill"

    if status in {"approved", "complete", "completed"}:
        title = "Skill request approved"
    elif status in {"denied", "rejected"}:
        title = "Skill request denied"
    else:
        title = "Skill request submitted"

    description_bits = [str(skill_name)]

    if row.get("cost") is not None:
        description_bits.append(f"{row.get('cost')} XP")
    elif row.get("xp_cost_paid") is not None:
        description_bits.append(f"{row.get('xp_cost_paid')} XP")

    return {
        "id": f"{table_name}:{row.get('request_id') or row.get('skill_key') or row.get('created_at')}",
        "kind": "skill_request",
        "title": title,
        "status": row.get("status") or row.get("review_status"),
        "description": " • ".join(description_bits),
        "actor_discord_id": row.get("requested_by_discord_id") or row.get("user_id") or row.get("actor_discord_id"),
        "time": _activity_time(row),
        "raw": row,
    }


@router.get("/recent")
def recent_activity(
    limit: int = Query(default=80, ge=1, le=250),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)

    sb = get_supabase()
    gid = get_guild_id()

    activities: list[dict[str, Any]] = []

    stat_rows = _try_table_rows(sb, "stat_upgrade_requests", gid, limit)
    activities.extend(_stat_activity(row) for row in stat_rows)

    shop_rows = _try_table_rows(sb, "shop_items", gid, limit)
    activities.extend(_shop_activity(row) for row in shop_rows)

    rp_claim_rows = _try_table_rows(sb, "rp_xp_claims", gid, limit)
    activities.extend(_rp_claim_activity(row) for row in rp_claim_rows)

    # Skill request table names have changed during development, so try common candidates.
    for table_name in ["skill_requests", "skill_upgrade_requests", "skill_purchase_requests"]:
        skill_rows = _try_table_rows(sb, table_name, gid, limit)
        activities.extend(_skill_activity(table_name, row) for row in skill_rows)

    activities = [activity for activity in activities if activity.get("time")]
    activities.sort(key=lambda item: _safe_str(item.get("time")), reverse=True)
    activities = activities[:limit]

    counts_by_kind: dict[str, int] = {}
    for activity in activities:
        kind = activity.get("kind") or "unknown"
        counts_by_kind[kind] = counts_by_kind.get(kind, 0) + 1

    return {
        "activities": activities,
        "totals": {
            "count": len(activities),
            "stat_requests": counts_by_kind.get("stat_request", 0),
            "shop_listings": counts_by_kind.get("shop_listing", 0),
            "rp_xp_claims": counts_by_kind.get("rp_xp_claim", 0),
            "skill_requests": counts_by_kind.get("skill_request", 0),
        },
    }
