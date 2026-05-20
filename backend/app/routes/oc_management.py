from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase
from app.utils.activity_webhooks import send_staff_activity_webhook
from app.utils.activity_logger import log_activity

router = APIRouter(prefix="/api/characters", tags=["oc-management"])

PUBLIC_PROFILE_FIELDS = {
    "name": 64,
    "occupation": 80,
    "affiliation": 120,
    "sheet_url": 500,
    "portrait_url": 500,
    "blurb": 1200,
}


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _load_character(sb, character_id: str) -> tuple[dict[str, Any] | None, str]:
    for column in ("character_id", "id"):
        rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, character_id)
            .limit(1)
        )
        if rows:
            return rows[0], column

        rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq(column, character_id)
            .limit(1)
        )
        if rows:
            return rows[0], column

    return None, "character_id"


def _owner_id(character: dict[str, Any]) -> str | None:
    value = (
        character.get("user_id")
        or character.get("discord_id")
        or character.get("owner_discord_id")
        or character.get("player_discord_id")
    )
    return str(value) if value is not None else None


def _can_edit(character: dict[str, Any], actor_discord_id: int | None) -> bool:
    if actor_discord_id is None:
        return False

    owner_id = _owner_id(character)
    if owner_id is not None and str(owner_id) == str(actor_discord_id):
        return True

    return is_staff(int(actor_discord_id))


def _require_edit(character: dict[str, Any], actor_discord_id: int | None) -> None:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    if not _can_edit(character, actor_discord_id):
        raise HTTPException(status_code=403, detail="You can only edit your own OC.")


def _require_staff(actor_discord_id: int | None) -> None:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    if not is_staff(int(actor_discord_id)):
        raise HTTPException(status_code=403, detail="Staff only.")


def _clean_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
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

    if "name" in cleaned and not cleaned["name"]:
        raise HTTPException(status_code=400, detail="OC name cannot be blank.")

    return cleaned


def _delete_where(sb, table: str, column: str, character_id: str) -> int:
    try:
        result = sb.table(table).delete().eq(column, character_id).execute()
        return len(_as_list(result))
    except Exception:
        return 0



def _delete_owned_companies_and_stores(sb, character_id: str) -> dict[str, int]:
    """Delete companies/stores owned by an OC before hard-deleting the OC.

    This prevents FK errors like:
    companies.owner_character_id -> characters.character_id

    Best effort and schema-tolerant:
    - companies owned by this OC are found by owner_character_id
    - related shop/order/item/wallet/transaction rows are deleted first when tables exist
    - missing tables/columns are ignored by _delete_where/_safe_rows
    """
    deleted: dict[str, int] = {}

    companies = _safe_rows(
        sb.table("companies")
        .select("*")
        .eq("owner_character_id", character_id)
        .limit(1000)
    )

    if not companies:
        return deleted

    company_ids = [
        str(company.get("company_id") or company.get("id") or "")
        for company in companies
        if company.get("company_id") or company.get("id")
    ]

    shop_ids: list[str] = []
    item_ids: list[str] = []

    for company_id in company_ids:
        shops = _safe_rows(
            sb.table("shops")
            .select("*")
            .eq("company_id", company_id)
            .limit(1000)
        )
        for shop in shops:
            shop_id = str(shop.get("shop_id") or shop.get("id") or "")
            if shop_id:
                shop_ids.append(shop_id)

    for shop_id in shop_ids:
        items = _safe_rows(
            sb.table("shop_items")
            .select("*")
            .eq("shop_id", shop_id)
            .limit(1000)
        )
        for item in items:
            item_id = str(item.get("item_id") or item.get("id") or "")
            if item_id:
                item_ids.append(item_id)

    # Delete deepest children first.
    for item_id in item_ids:
        for table, column in (
            ("shop_orders", "item_id"),
            ("shop_order_items", "item_id"),
            ("shop_purchases", "item_id"),
        ):
            count = _delete_where(sb, table, column, item_id)
            if count:
                deleted[f"{table}.{column}"] = deleted.get(f"{table}.{column}", 0) + count

    for shop_id in shop_ids:
        for table, column in (
            ("shop_orders", "shop_id"),
            ("shop_order_items", "shop_id"),
            ("shop_purchases", "shop_id"),
            ("shop_items", "shop_id"),
            ("shop_channels", "shop_id"),
            ("shop_logs", "shop_id"),
        ):
            count = _delete_where(sb, table, column, shop_id)
            if count:
                deleted[f"{table}.{column}"] = deleted.get(f"{table}.{column}", 0) + count

    for company_id in company_ids:
        for table, column in (
            ("shop_orders", "company_id"),
            ("shop_purchases", "company_id"),
            ("shop_items", "company_id"),
            ("shops", "company_id"),
            ("company_wallets", "company_id"),
            ("company_transactions", "company_id"),
            ("company_members", "company_id"),
            ("company_logs", "company_id"),
            ("companies", "company_id"),
            ("companies", "id"),
        ):
            count = _delete_where(sb, table, column, company_id)
            if count:
                deleted[f"{table}.{column}"] = deleted.get(f"{table}.{column}", 0) + count

    # Fallback in case the companies table uses only owner_character_id for this relationship.
    count = _delete_where(sb, "companies", "owner_character_id", character_id)
    if count:
        deleted["companies.owner_character_id"] = deleted.get("companies.owner_character_id", 0) + count

    return deleted

def _delete_related_rows(sb, character_id: str) -> dict[str, int]:
    deleted: dict[str, int] = {}

    deleted.update(_delete_owned_companies_and_stores(sb, character_id))

    targets = [
        ("character_traits", "character_id"),
        ("oc_traits", "character_id"),
        ("character_skills", "character_id"),
        ("oc_skills", "character_id"),
        ("character_inventory", "character_id"),
        ("oc_inventory", "character_id"),
        ("inventory", "character_id"),
        ("wallets", "character_id"),
        ("character_wallets", "character_id"),
        ("transactions", "character_id"),
        ("transactions", "from_character_id"),
        ("transactions", "to_character_id"),
        ("oc_xp_transactions", "character_id"),
        ("oc_xp_transactions", "from_character_id"),
        ("oc_xp_transactions", "to_character_id"),
        ("stat_requests", "character_id"),
        ("skill_requests", "character_id"),
        ("rp_posts", "character_id"),
        ("rp_messages", "character_id"),
        ("rp_activity", "character_id"),
        ("rp_logs", "character_id"),
    ]

    for table, column in targets:
        count = _delete_where(sb, table, column, character_id)
        if count:
            deleted[f"{table}.{column}"] = count

    return deleted


@router.get("/{character_id}/manage")
def get_character_management_info(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    character, _ = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    return {
        "character": character,
        "can_edit": _can_edit(character, actor_discord_id),
        "is_staff": is_staff(int(actor_discord_id)),
        "owner_discord_id": _owner_id(character),
    }


@router.patch("/{character_id}/manage")
def update_character_management_info(
    character_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    character, id_column = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    _require_edit(character, actor_discord_id)

    cleaned = _clean_update_payload(payload)
    if not cleaned:
        raise HTTPException(status_code=400, detail="No editable OC fields were provided.")

    try:
        query = sb.table("characters").update(cleaned).eq(id_column, character_id)
        if character.get("guild_id") is not None:
            query = query.eq("guild_id", get_guild_id())

        updated = _as_list(query.execute())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not update OC: {exc}")

    updated_character = updated[0] if updated else {**character, **cleaned}

    send_staff_activity_webhook(
        title="✏️ OC Updated",
        description="OC public profile edited.",
        event_type="oc_updated",
        status="updated",
        actor_id=actor_discord_id,
        character_id=character_id,
        character_name=updated_character.get("name") or character.get("name"),
        fields=[
            {"name": "Updated Fields", "value": ", ".join(cleaned.keys()) or "—", "inline": False},
        ],
    )

    log_activity(
        event_type="oc_updated",
        label=f"OC updated: {updated_character.get('name') or character.get('name') or 'OC'}",
        status="updated",
        actor_discord_id=actor_discord_id,
        character_id=character_id,
        character_name=updated_character.get("name") or character.get("name"),
        note="activity_log_hardening_v2_oc_updated",
        source="oc_management",
        details={
            "updated_fields": list(cleaned.keys()),
            "old_name": character.get("name"),
            "new_name": updated_character.get("name"),
        },
        webhook_title="✏️ OC Updated",
        webhook_description="OC public profile edited.",
        webhook_fields=[
            {"name": "Updated Fields", "value": ", ".join(cleaned.keys()) or "—", "inline": False},
        ],
    )

    return {
        "character": updated_character,
        "message": "OC updated.",
    }


@router.post("/{character_id}/archive")
def archive_character(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    character, id_column = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    _require_edit(character, actor_discord_id)

    # Support whichever visibility field exists. If one fails, try the next.
    attempts = [
        {"is_active": False},
        {"archived": True},
        {"status": "Archived"},
    ]

    last_error: Exception | None = None
    for payload in attempts:
        try:
            query = sb.table("characters").update(payload).eq(id_column, character_id)
            if character.get("guild_id") is not None:
                query = query.eq("guild_id", get_guild_id())

            rows = _as_list(query.execute())
            archived_character = rows[0] if rows else {**character, **payload}

            send_staff_activity_webhook(
                title="📦 OC Archived",
                description="OC archived from dashboard.",
                event_type="oc_archived",
                status="archived",
                actor_id=actor_discord_id,
                character_id=character_id,
                character_name=archived_character.get("name") or character.get("name"),
            )

            log_activity(
                event_type="oc_archived",
                label=f"OC archived: {archived_character.get('name') or character.get('name') or 'OC'}",
                status="archived",
                actor_discord_id=actor_discord_id,
                character_id=character_id,
                character_name=archived_character.get("name") or character.get("name"),
                note="activity_log_hardening_v2_oc_archived",
                source="oc_management",
                details={"payload": payload},
                webhook_title="📦 OC Archived",
                webhook_description="OC archived from dashboard.",
            )

            return {
                "character": archived_character,
                "message": "OC archived.",
            }
        except Exception as exc:
            last_error = exc
            continue

    raise HTTPException(status_code=500, detail=f"Could not archive OC: {last_error}")


@router.post("/{character_id}/restore")
def restore_character(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    character, id_column = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    _require_edit(character, actor_discord_id)

    attempts = [
        {"is_active": True},
        {"archived": False},
        {"status": "Active"},
    ]

    last_error: Exception | None = None
    for payload in attempts:
        try:
            query = sb.table("characters").update(payload).eq(id_column, character_id)
            if character.get("guild_id") is not None:
                query = query.eq("guild_id", get_guild_id())

            rows = _as_list(query.execute())
            restored_character = rows[0] if rows else {**character, **payload}

            send_staff_activity_webhook(
                title="♻️ OC Restored",
                description="OC restored from dashboard.",
                event_type="oc_restored",
                status="restored",
                actor_id=actor_discord_id,
                character_id=character_id,
                character_name=restored_character.get("name") or character.get("name"),
            )

            log_activity(
                event_type="oc_restored",
                label=f"OC restored: {restored_character.get('name') or character.get('name') or 'OC'}",
                status="restored",
                actor_discord_id=actor_discord_id,
                character_id=character_id,
                character_name=restored_character.get("name") or character.get("name"),
                note="activity_log_hardening_v2_oc_restored",
                source="oc_management",
                details={"payload": payload},
                webhook_title="♻️ OC Restored",
                webhook_description="OC restored from dashboard.",
            )

            return {
                "character": restored_character,
                "message": "OC restored.",
            }
        except Exception as exc:
            last_error = exc
            continue

    raise HTTPException(status_code=500, detail=f"Could not restore OC: {last_error}")


@router.delete("/{character_id}")
def delete_character_staff_only(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    _require_staff(actor_discord_id)

    sb = get_supabase()
    character, id_column = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    deleted_related = _delete_related_rows(sb, character_id)

    try:
        query = sb.table("characters").delete().eq(id_column, character_id)
        if character.get("guild_id") is not None:
            query = query.eq("guild_id", get_guild_id())

        deleted_character = _as_list(query.execute())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not delete OC: {exc}")

    return {
        "deleted": bool(deleted_character),
        "character_id": character_id,
        "name": character.get("name"),
        "related_rows": deleted_related,
        "message": f"Deleted {character.get('name') or 'OC'}.",
    }
