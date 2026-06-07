from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

try:
    from app.utils.activity_logger import log_activity
except Exception:  # pragma: no cover
    def log_activity(**kwargs):
        return None


router = APIRouter(prefix="/api/shop-owner", tags=["shop-owner"])


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


def _shop_id(row: dict[str, Any]) -> str:
    return str(row.get("shop_id") or row.get("id") or "")


def _item_id(row: dict[str, Any]) -> str:
    return str(row.get("item_id") or row.get("shop_item_id") or row.get("id") or "")


def _owner_id(row: dict[str, Any]) -> str | None:
    for key in ("owner_discord_id", "user_id", "discord_id", "player_discord_id"):
        if row.get(key) is not None:
            return str(row.get(key))
    return None


def _is_shop_owner(row: dict[str, Any], actor: int) -> bool:
    owner = _owner_id(row)
    return owner is not None and str(owner) == str(actor)


def _can_manage_shop(row: dict[str, Any], actor: int) -> bool:
    return _is_shop_owner(row, actor) or is_staff(actor)


def _load_shop(sb, shop_id: str) -> tuple[dict[str, Any], str]:
    for column in ("shop_id", "id"):
        rows = _safe_rows(
            sb.table("shops")
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, shop_id)
            .limit(1)
        )

        if not rows:
            rows = _safe_rows(
                sb.table("shops")
                .select("*")
                .eq(column, shop_id)
                .limit(1)
            )

        if rows:
            return rows[0], column

    raise HTTPException(status_code=404, detail="Shop not found.")


def _load_item(sb, item_id: str) -> tuple[dict[str, Any], str]:
    for column in ("item_id", "shop_item_id", "id"):
        rows = _safe_rows(
            sb.table("shop_items")
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, item_id)
            .limit(1)
        )

        if not rows:
            rows = _safe_rows(
                sb.table("shop_items")
                .select("*")
                .eq(column, item_id)
                .limit(1)
            )

        if rows:
            return rows[0], column

    raise HTTPException(status_code=404, detail="Shop item not found.")


def _load_items_for_shop(sb, shop_id: str) -> list[dict[str, Any]]:
    rows = _safe_rows(
        sb.table("shop_items")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("shop_id", shop_id)
        .limit(500)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("shop_items")
            .select("*")
            .eq("shop_id", shop_id)
            .limit(500)
        )

    return rows


def _number(value: Any, default: int | float = 0) -> int | float:
    if value is None or value == "":
        return default
    try:
        amount = float(value)
        return int(amount) if amount.is_integer() else round(amount, 2)
    except Exception:
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "y", "on"}


def _clean(value: Any, max_len: int = 500) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _normalize_shop(row: dict[str, Any]) -> dict[str, Any]:
    enabled_value = row.get("enabled")
    is_active = bool(enabled_value) if enabled_value is not None else True
    return {
        "shop_id": _shop_id(row),
        "name": row.get("name") or row.get("shop_name") or "Unnamed Shop",
        "description": row.get("description") or row.get("blurb") or row.get("details"),
        "owner_discord_id": _owner_id(row),
        "owner_character_id": row.get("owner_character_id"),
        "status": "Open" if is_active else "Closed",
        "is_active": is_active,
        "enabled": is_active,
        "image_url": row.get("image_url") or row.get("banner_url"),
        "channel_id": row.get("channel_id"),
        "raw": row,
    }


def _normalize_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": _item_id(row),
        "shop_id": str(row.get("shop_id") or row.get("store_id") or ""),
        "name": row.get("name") or row.get("item_name") or row.get("title") or "Unnamed Item",
        "description": row.get("description") or row.get("details") or row.get("notes"),
        "category": row.get("category") or row.get("item_type") or row.get("type") or "General",
        "price": _number(row.get("price") if row.get("price") is not None else row.get("cost"), 0),
        "stock": row.get("stock") if row.get("stock") is not None else row.get("quantity"),
        "currency_id": row.get("currency_id"),
        "requires_approval": bool(row.get("requires_approval") or row.get("needs_approval")),
        "is_active": bool(row.get("is_active", True)) if row.get("is_active") is not None else str(row.get("status") or "").lower() not in {"inactive", "archived"},
        "image_url": row.get("image_url") or row.get("thumbnail_url"),
        "role_id": row.get("role_id"),
        "raw": row,
    }


@router.post("/shops")
def create_my_shop(
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    name = _clean(payload.get("name") or payload.get("shop_name"), 120)
    if not name:
        raise HTTPException(status_code=400, detail="Storefront name is required.")
    enabled = _bool(payload.get("enabled") if "enabled" in payload else payload.get("is_active"), True)
    base_payload = {
        "guild_id": get_guild_id(),
        "name": name,
        "description": _clean(payload.get("description"), 1000),
        "enabled": enabled,
        "is_forum": False,
        "treasury_cut_bps": int(_number(payload.get("treasury_cut_bps"), 0)),
        "owner_discord_id": int(actor),
    }
    if payload.get("owner_character_id"):
        base_payload["owner_character_id"] = str(payload.get("owner_character_id"))
    if payload.get("image_url"):
        base_payload["image_url"] = _clean(payload.get("image_url"), 800)
    insert_attempts = [
        base_payload,
        {k: v for k, v in base_payload.items() if k not in {"owner_character_id"}},
        {k: v for k, v in base_payload.items() if k not in {"owner_discord_id", "owner_character_id"}},
    ]
    last_error = None
    rows = []
    for attempt in insert_attempts:
        try:
            rows = _as_list(sb.table("shops").insert(attempt).execute())
            if rows:
                break
        except Exception as exc:
            last_error = exc
            rows = []
    if not rows:
        raise HTTPException(status_code=400, detail=f"Could not create storefront. {last_error}")
    shop = rows[0]
    return {"shop": _normalize_shop(shop), "message": "Storefront created."}

@router.get("/shops")
def get_my_shops(actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    rows = _safe_rows(
        sb.table("shops")
        .select("*")
        .eq("guild_id", get_guild_id())
        .limit(500)
    )

    if not rows:
        rows = _safe_rows(sb.table("shops").select("*").limit(500))

    if not is_staff(actor):
        rows = [row for row in rows if _is_shop_owner(row, actor)]

    shops = []
    for row in rows:
        sid = _shop_id(row)
        items = _load_items_for_shop(sb, sid) if sid else []
        normalized = _normalize_shop(row)
        normalized["item_count"] = len(items)
        shops.append(normalized)

    return {"shops": shops, "is_staff": is_staff(actor)}


@router.get("/shops/{shop_id}")
def get_shop_management(shop_id: str, actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    shop, _ = _load_shop(sb, shop_id)

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only manage your own shop.")

    items = [_normalize_item(row) for row in _load_items_for_shop(sb, _shop_id(shop))]

    currencies = _safe_rows(
        sb.table("currencies")
        .select("*")
        .eq("guild_id", get_guild_id())
        .limit(100)
    )

    if not currencies:
        currencies = _safe_rows(sb.table("currencies").select("*").limit(100))

    return {
        "shop": _normalize_shop(shop),
        "items": items,
        "currencies": currencies,
        "can_manage": True,
        "is_staff": is_staff(actor),
    }


@router.patch("/shops/{shop_id}")
def update_shop(
    shop_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    shop, id_column = _load_shop(sb, shop_id)
    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only manage your own storefront.")
    update_payload = {}
    for source_key, dest_key, max_len in [
        ("name", "name", 120),
        ("description", "description", 1000),
        ("image_url", "image_url", 800),
        ("item_type", "item_type", 80),
    ]:
        if source_key in payload:
            update_payload[dest_key] = _clean(payload.get(source_key), max_len)
    if "enabled" in payload:
        update_payload["enabled"] = _bool(payload.get("enabled"), True)
    elif "is_active" in payload:
        update_payload["enabled"] = _bool(payload.get("is_active"), True)
    if "owner_character_id" in payload:
        update_payload["owner_character_id"] = str(payload.get("owner_character_id")) if payload.get("owner_character_id") else None
    if not update_payload:
        raise HTTPException(status_code=400, detail="No storefront fields provided.")
    try:
        rows = _as_list(sb.table("shops").update(update_payload).eq(id_column, shop_id).execute())
    except Exception:
        fallback = {k: v for k, v in update_payload.items() if k not in {"owner_character_id"}}
        rows = _as_list(sb.table("shops").update(fallback).eq(id_column, shop_id).execute())
    updated = rows[0] if rows else {**shop, **update_payload}
    return {"shop": _normalize_shop(updated), "message": "Storefront updated."}

@router.post("/shops/{shop_id}/items")
def create_shop_item(
    shop_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    shop, _ = _load_shop(sb, shop_id)

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only manage your own storefront.")

    name = _clean(payload.get("name") or payload.get("item_name"), 160)
    if not name:
        raise HTTPException(status_code=400, detail="Item name is required.")

    category_value = _clean(payload.get("category"), 80)
    raw_item_type = (_clean(payload.get("item_type"), 80) or "item").lower().strip()

    allowed_item_types = {
        "item",
        "material",
        "consumable",
        "equipment",
        "service",
        "role",
        "currency",
    }

    # Never use category as item_type. Values like "General" violate the DB check constraint.
    item_type_value = raw_item_type if raw_item_type in allowed_item_types else "item"

    insert_payload: dict[str, Any] = {
        "guild_id": get_guild_id(),
        "shop_id": shop_id,
        "name": name,
        "description": _clean(payload.get("description"), 1000),
        "price": _number(payload.get("price"), 0),
        "stock": int(_number(payload.get("stock"), 0)),
        "requires_approval": _bool(payload.get("requires_approval"), False),
        "is_active": _bool(payload.get("is_active"), True),
        "purchasable": _bool(payload.get("purchasable"), True),
        "review_status": "approved" if not _bool(payload.get("requires_approval"), False) else "PENDING_STAFF_REVIEW",
        "item_type": item_type_value,
        "grants_qty": int(_number(payload.get("grants_qty"), 1)),
    }

    # Live databases have varied here. Do not rely on category being present.
    # Use category as item_class when available; if the DB has category, the
    # schema-safe insert below can still accept it later if we add it back.
    if category_value:
        insert_payload["item_class"] = category_value

    optional_text_fields = [
        ("image_url", "image_url", 800),
        ("recipe_link", "recipe_link", 800),
        ("unique_owner", "unique_owner", 160),
        ("stat_limits", "stat_limits", 1000),
        ("special_effects", "special_effects", 2000),
        ("usage_information", "usage_information", 2000),
        ("staff_change_summary", "staff_change_summary", 1000),
        ("owner_change_notes", "owner_change_notes", 1000),
    ]

    for source_key, dest_key, max_len in optional_text_fields:
        if payload.get(source_key):
            insert_payload[dest_key] = _clean(payload.get(source_key), max_len)

    optional_int_fields = [
        "max_per_order",
        "max_per_user_per_day",
        "max_per_day",
        "max_per_week",
        "max_per_user",
        "weight",
        "cc",
    ]

    for key in optional_int_fields:
        if payload.get(key) not in (None, ""):
            insert_payload[key] = int(_number(payload.get(key), 0))

    if payload.get("weight_unit"):
        insert_payload["weight_unit"] = _clean(payload.get("weight_unit"), 40)

    if payload.get("tag"):
        insert_payload["tag"] = _clean(payload.get("tag"), 120)

    if payload.get("grants_item_id"):
        insert_payload["grants_item_id"] = str(payload.get("grants_item_id"))

    if payload.get("currency_id"):
        insert_payload["currency_id"] = str(payload.get("currency_id"))
    else:
        currencies = _safe_rows(sb.table("currencies").select("*").eq("guild_id", get_guild_id()).limit(1))
        if not currencies:
            currencies = _safe_rows(sb.table("currencies").select("*").limit(1))
        if currencies:
            insert_payload["currency_id"] = str(currencies[0].get("currency_id") or currencies[0].get("id"))

    def _missing_column_from_error(error: Exception) -> str | None:
        message = str(error)
        marker = "Could not find the '"
        if marker not in message:
            return None

        after = message.split(marker, 1)[1]
        if "'" not in after:
            return None

        return after.split("'", 1)[0]

    attempt_payload = dict(insert_payload)

    if str(attempt_payload.get("item_type") or "").lower().strip() not in allowed_item_types:
        attempt_payload["item_type"] = "item"

    last_error: Exception | None = None

    for _ in range(20):
        try:
            rows = _as_list(sb.table("shop_items").insert(attempt_payload).execute())
            item = rows[0] if rows else attempt_payload

            log_activity(
                event_type="shop_item_created",
                label=f"Shop item created: {name}",
                status="created",
                actor_discord_id=actor,
                source="shop_owner_tools",
                amount=attempt_payload.get("price"),
                details={"shop_id": shop_id, "item": attempt_payload},
                webhook_title="🧾 Shop Item Created",
                webhook_description=f"{name} was added to {shop.get('name') or 'a storefront'}.",
            )

            return {"item": _normalize_item(item), "message": "Item created."}
        except Exception as exc:
            last_error = exc
            missing_column = _missing_column_from_error(exc)

            if missing_column and missing_column in attempt_payload:
                attempt_payload.pop(missing_column, None)
                continue

            break

    raise HTTPException(status_code=400, detail=f"Could not create item: {last_error}")

@router.delete("/items/{item_id}")
def delete_shop_item(
    item_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    item_rows = _as_list(
        sb.table("shop_items")
        .select("*")
        .eq("item_id", item_id)
        .limit(1)
        .execute()
    )

    if not item_rows:
        raise HTTPException(status_code=404, detail="Item not found.")

    item = item_rows[0]
    shop_id = item.get("shop_id")

    if not shop_id:
        raise HTTPException(status_code=400, detail="This item is not attached to a storefront.")

    shop, _ = _load_shop(sb, str(shop_id))

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only delete items from your own storefront.")

    # Try hard delete first. If orders reference this item (FK constraint),
    # fall back to soft delete — mark it inactive and unpurchasable so it
    # disappears from the shop but order history stays intact.
    try:
        deleted_rows = _as_list(
            sb.table("shop_items")
            .delete()
            .eq("item_id", item_id)
            .execute()
        )
        return {
            "ok": True,
            "message": f"Deleted {item.get('name') or 'item'}.",
            "deleted": deleted_rows or [item],
        }
    except Exception as exc:
        err = str(exc)
        if "23503" in err or "foreign key" in err.lower() or "shop_orders" in err:
            # Item has order history — soft delete instead
            try:
                _as_list(
                    sb.table("shop_items")
                    .update({
                        "is_active": False,
                        "purchasable": False,
                        "stock": 0,
                    })
                    .eq("item_id", item_id)
                    .execute()
                )
            except Exception:
                # Some schemas don't have all three columns — try minimal
                _as_list(
                    sb.table("shop_items")
                    .update({"is_active": False})
                    .eq("item_id", item_id)
                    .execute()
                )
            log_activity(
                event_type="shop_item_soft_deleted",
                label=f"Shop item hidden (has order history): {item.get('name') or 'Item'}",
                status="soft_deleted",
                actor_discord_id=actor,
                source="shop_owner_tools",
                details={"item_id": item_id},
            )
            return {
                "ok": True,
                "message": f"{item.get('name') or 'Item'} has order history and was hidden instead of deleted. It won't appear in your shop.",
                "soft_deleted": True,
            }
        raise HTTPException(status_code=400, detail=f"Could not delete item: {exc}")


@router.delete("/items/{item_id}/force-delete")
def force_delete_shop_item(
    item_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    """Staff-only: delete an item and its order history so the FK constraint clears."""
    actor = _require_login(actor_discord_id)
    if not is_staff(actor):
        raise HTTPException(status_code=403, detail="Staff only.")

    sb = get_supabase()

    item_rows = _as_list(
        sb.table("shop_items").select("*").eq("item_id", item_id).limit(1).execute()
    )
    if not item_rows:
        raise HTTPException(status_code=404, detail="Item not found.")

    item = item_rows[0]
    item_name = item.get("name") or item.get("item_name") or "Item"

    # Delete referencing orders first, then the item
    try:
        for col in ("item_id", "shop_item_id"):
            try:
                _as_list(sb.table("shop_orders").delete().eq(col, item_id).execute())
            except Exception:
                pass

        _as_list(sb.table("shop_items").delete().eq("item_id", item_id).execute())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Force delete failed: {exc}")

    log_activity(
        event_type="shop_item_force_deleted",
        label=f"Shop item force deleted (with order history): {item_name}",
        status="force_deleted",
        actor_discord_id=actor,
        source="shop_owner_tools",
        details={"item_id": item_id, "item_name": item_name},
        webhook_title="🗑️ Item Force Deleted",
        webhook_description=f'"{item_name}" and its order history were permanently deleted by staff.',
    )

    return {"ok": True, "message": f'"{item_name}" and its order history permanently deleted.'}


@router.patch("/items/{item_id}")
def update_shop_item(
    item_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    item, id_column = _load_item(sb, item_id)
    shop, _ = _load_shop(sb, str(item.get("shop_id") or item.get("store_id") or ""))

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only manage your own shop items.")

    update_payload: dict[str, Any] = {}

    field_map = [
        ("name", "name", 160),
        ("description", "description", 1000),
        ("category", "category", 80),
        ("image_url", "image_url", 800),
    ]

    for source_key, dest_key, max_len in field_map:
        if source_key in payload:
            update_payload[dest_key] = _clean(payload.get(source_key), max_len)

    if "price" in payload:
        update_payload["price"] = _number(payload.get("price"), 0)

    if "stock" in payload:
        update_payload["stock"] = int(_number(payload.get("stock"), 0))

    if "currency_id" in payload:
        update_payload["currency_id"] = str(payload.get("currency_id")) if payload.get("currency_id") else None

    if "requires_approval" in payload:
        update_payload["requires_approval"] = _bool(payload.get("requires_approval"), False)

    if "is_active" in payload:
        update_payload["is_active"] = _bool(payload.get("is_active"), True)

    if not update_payload:
        raise HTTPException(status_code=400, detail="No item fields provided.")

    try:
        rows = _as_list(
            sb.table("shop_items")
            .update(update_payload)
            .eq(id_column, item_id)
            .execute()
        )
    except Exception:
        # Fallback for older schemas that use item_name instead of name.
        fallback = dict(update_payload)
        if "name" in fallback:
            fallback["item_name"] = fallback.pop("name")
        rows = _as_list(
            sb.table("shop_items")
            .update(fallback)
            .eq(id_column, item_id)
            .execute()
        )

    updated = rows[0] if rows else {**item, **update_payload}

    log_activity(
        event_type="shop_item_updated",
        label=f"Shop item updated: {updated.get('name') or updated.get('item_name') or 'Item'}",
        status="updated",
        actor_discord_id=actor,
        source="shop_owner_tools",
        amount=updated.get("price") or updated.get("cost"),
        details={"item_id": item_id, "updated_fields": list(update_payload.keys())},
        webhook_title="✏️ Shop Item Updated",
        webhook_description=f"{updated.get('name') or updated.get('item_name') or 'Item'} was updated.",
    )

    return {"item": _normalize_item(updated), "message": "Item updated."}


@router.post("/items/{item_id}/toggle")
def toggle_shop_item(
    item_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    item, id_column = _load_item(sb, item_id)
    shop, _ = _load_shop(sb, str(item.get("shop_id") or item.get("store_id") or ""))

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only manage your own shop items.")

    next_active = not bool(item.get("is_active", True))

    try:
        rows = _as_list(sb.table("shop_items").update({"is_active": next_active}).eq(id_column, item_id).execute())
    except Exception:
        rows = _as_list(sb.table("shop_items").update({"status": "active" if next_active else "inactive"}).eq(id_column, item_id).execute())

    updated = rows[0] if rows else {**item, "is_active": next_active}

    log_activity(
        event_type="shop_item_toggled",
        label=f"Shop item {'activated' if next_active else 'deactivated'}: {updated.get('name') or updated.get('item_name') or 'Item'}",
        status="active" if next_active else "inactive",
        actor_discord_id=actor,
        source="shop_owner_tools",
        details={"item_id": item_id, "is_active": next_active},
    )

    return {"item": _normalize_item(updated), "message": "Item activated." if next_active else "Item deactivated."}


def _order_id(row: dict[str, Any]) -> str:
    return str(row.get("order_id") or row.get("id") or "")


def _load_order(sb, order_id: str) -> tuple[dict[str, Any], str]:
    for column in ("order_id", "id"):
        rows = _safe_rows(
            sb.table("shop_orders")
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, order_id)
            .limit(1)
        )

        if not rows:
            rows = _safe_rows(
                sb.table("shop_orders")
                .select("*")
                .eq(column, order_id)
                .limit(1)
            )

        if rows:
            return rows[0], column

    raise HTTPException(status_code=404, detail="Order not found.")


def _load_shop_for_order(sb, order: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    item_id = str(order.get("item_id") or order.get("shop_item_id") or "")
    if not item_id:
        raise HTTPException(status_code=400, detail="Order is missing item_id.")

    item, _ = _load_item(sb, item_id)
    shop_id = str(item.get("shop_id") or item.get("store_id") or "")
    shop, _ = _load_shop(sb, shop_id)
    return shop, item


def _normalize_order(row: dict[str, Any], items_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item_id = str(row.get("item_id") or row.get("shop_item_id") or "")
    item = items_by_id.get(item_id, {})

    return {
        "order_id": _order_id(row),
        "item_id": item_id,
        "item_name": item.get("name") or item.get("item_name") or row.get("item_name") or "Unknown Item",
        "shop_id": str(item.get("shop_id") or item.get("store_id") or row.get("shop_id") or ""),
        "quantity": int(_number(row.get("quantity") or row.get("qty"), 1)),
        "status": str(row.get("status") or "pending").lower(),
        "user_id": str(row.get("user_id") or row.get("discord_id") or row.get("buyer_discord_id") or ""),
        "character_id": str(row.get("character_id") or row.get("oc_id") or "") if row.get("character_id") or row.get("oc_id") else None,
        "note": row.get("note") or row.get("notes") or row.get("reason"),
        "staff_note": row.get("staff_note") or row.get("denial_reason") or row.get("review_note"),
        "created_at": row.get("created_at") or row.get("timestamp"),
        "approved_by": row.get("approved_by") or row.get("reviewed_by"),
        "fulfilled_by": row.get("fulfilled_by"),
        "raw": row,
    }


def _items_by_id(sb, item_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not item_ids:
        return {}

    rows: list[dict[str, Any]] = []
    for column in ("item_id", "shop_item_id", "id"):
        rows = _safe_rows(
            sb.table("shop_items")
            .select("*")
            .eq("guild_id", get_guild_id())
            .in_(column, list(item_ids))
            .limit(500)
        )
        if rows:
            break

        rows = _safe_rows(
            sb.table("shop_items")
            .select("*")
            .in_(column, list(item_ids))
            .limit(500)
        )
        if rows:
            break

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in ("item_id", "shop_item_id", "id"):
            if row.get(key):
                out[str(row.get(key))] = row
    return out


@router.get("/shops/{shop_id}/orders")
def get_shop_orders(
    shop_id: str,
    status: str = "pending",
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    shop, _ = _load_shop(sb, shop_id)

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only view orders for your own shop.")

    item_rows = _load_items_for_shop(sb, shop_id)
    item_ids = {
        str(row.get("item_id") or row.get("shop_item_id") or row.get("id"))
        for row in item_rows
        if row.get("item_id") or row.get("shop_item_id") or row.get("id")
    }
    items_by_id = _items_by_id(sb, item_ids)

    rows: list[dict[str, Any]] = []
    for column in ("item_id", "shop_item_id"):
        for item_id in item_ids:
            found = _safe_rows(
                sb.table("shop_orders")
                .select("*")
                .eq("guild_id", get_guild_id())
                .eq(column, item_id)
                .limit(500)
            )
            if not found:
                found = _safe_rows(
                    sb.table("shop_orders")
                    .select("*")
                    .eq(column, item_id)
                    .limit(500)
                )
            rows.extend(found)

        if rows:
            break

    seen: set[str] = set()
    orders: list[dict[str, Any]] = []
    for row in rows:
        oid = _order_id(row) or f"{row.get('item_id')}:{row.get('user_id')}:{row.get('created_at')}"
        if oid in seen:
            continue
        seen.add(oid)
        normalized = _normalize_order(row, items_by_id)
        if status != "all" and normalized["status"] != status.lower():
            continue
        orders.append(normalized)

    orders.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {"orders": orders, "shop": _normalize_shop(shop)}


def _update_order_status(sb, order_id: str, status: str, actor: int, note: str | None = None) -> dict[str, Any]:
    order, id_column = _load_order(sb, order_id)

    # Confirmed columns from live shop_orders schema — no reviewed_by
    update_payload: dict[str, Any] = {"status": status}
    if status == "APPROVED":
        update_payload["approved_by"] = str(actor)
        update_payload["approved_at"] = "now()"
    if status == "DENIED":
        update_payload["denied_by"] = str(actor)
        update_payload["denied_at"] = "now()"
        update_payload["denial_reason"] = note
    if status == "FULFILLED":
        update_payload["fulfilled_by"] = str(actor)
        update_payload["fulfilled_at"] = "now()"

    rows = _as_list(sb.table("shop_orders").update(update_payload).eq(id_column, order_id).execute())
    return rows[0] if rows else {**order, **update_payload}


@router.post("/orders/{order_id}/approve")
def approve_shop_order(
    order_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    order, _ = _load_order(sb, order_id)
    shop, item = _load_shop_for_order(sb, order)

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only approve orders for your own shop.")

    updated = _update_order_status(sb, order_id, "APPROVED", actor, payload.get("note") or payload.get("staff_note"))

    # Grant inventory on approval — mirrors Keystone's approve flow
    quantity = int(_number(order.get("quantity") or order.get("qty"), 1))
    inventory_row = _insert_inventory_item(sb, order, item, quantity)

    log_activity(
        event_type="shop_order_approved",
        label=f"Shop order approved: {item.get('name') or item.get('item_name') or 'Item'}",
        status="approved",
        actor_discord_id=actor,
        character_id=order.get("buyer_character_id") or order.get("character_id") or order.get("oc_id"),
        note=payload.get("note") or payload.get("staff_note"),
        source="shop_owner_orders",
        details={"order_id": order_id, "shop_id": _shop_id(shop), "item_id": order.get("item_id"),
                 "inventory_granted": bool(inventory_row)},
        webhook_title="✅ Shop Order Approved",
    )

    msg = "Order approved."
    if inventory_row:
        msg += " Inventory delivered."
    elif not (order.get("buyer_character_id") or order.get("character_id")):
        msg += " No character attached — inventory not granted automatically."
    else:
        msg += " Inventory grant failed — check grants_item_id on the shop item."

    return {"order": updated, "message": msg, "inventory_granted": bool(inventory_row)}


@router.post("/orders/{order_id}/deny")
def deny_shop_order(
    order_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="A denial reason is required.")

    sb = get_supabase()
    order, _ = _load_order(sb, order_id)
    shop, item = _load_shop_for_order(sb, order)

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only deny orders for your own shop.")

    updated = _update_order_status(sb, order_id, "DENIED", actor, reason)

    log_activity(
        event_type="shop_order_denied",
        label=f"Shop order denied: {item.get('name') or item.get('item_name') or 'Item'}",
        status="denied",
        actor_discord_id=actor,
        character_id=order.get("character_id") or order.get("oc_id"),
        note=reason,
        source="shop_owner_orders",
        details={"order_id": order_id, "shop_id": _shop_id(shop), "item_id": order.get("item_id")},
        webhook_title="❌ Shop Order Denied",
        webhook_description=reason,
    )

    return {"order": updated, "message": "Order denied."}


def _insert_inventory_item(sb, order: dict[str, Any], item: dict[str, Any], quantity: int) -> dict[str, Any] | None:
    """
    Grant inventory using the same logic as Keystone:
    - Uses grants_item_id (the items table UUID) not the shop_items UUID
    - Multiplies grants_qty * order quantity
    - Falls back gracefully if grants_item_id is not set
    """
    character_id = (
        order.get("buyer_character_id")
        or order.get("character_id")
        or order.get("oc_id")
    )
    if not character_id:
        return None

    # Keystone uses grants_item_id, not the shop_item item_id
    grants_item_id = item.get("grants_item_id")
    grants_qty = int(item.get("grants_qty") or 1)
    item_name = item.get("name") or item.get("item_name") or "Shop Item"
    actor = int(order.get("buyer_discord_id") or order.get("discord_id") or 0)
    shop_item_id_short = str(item.get("item_id") or "")[:8]
    order_id_short = str(order.get("order_id") or "")[:8]

    if not grants_item_id:
        # Item has no grants_item_id set — nothing to grant
        return None

    total_qty = grants_qty * quantity

    rpc_payload = {
        "p_guild_id": get_guild_id(),
        "p_character_id": str(character_id),
        "p_item_id": str(grants_item_id),
        "p_delta": total_qty,
        "p_actor_discord_id": actor,
        "p_context": "shop_fulfill_approved",
        "p_note": f"order={order_id_short} shop_item={shop_item_id_short}",
    }
    try:
        res = _as_list(sb.rpc("apply_inventory_delta", rpc_payload).execute())
        return res[0] if res else {"ok": True, "granted": total_qty}
    except Exception as rpc_exc:
        rpc_err = str(rpc_exc)
        if "INSUFFICIENT_QTY" in rpc_err:
            raise HTTPException(status_code=400, detail="Insufficient quantity in inventory.")
        if "DELTA_ZERO" in rpc_err:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero.")
        # RPC failed for other reason — surface it
        raise HTTPException(status_code=500, detail=f"Inventory grant failed: {rpc_exc}")

    # (unreachable but kept for fallback clarity)
    for table in ("character_inventory", "oc_inventory", "inventory"):
        for payload in [{"character_id": str(character_id), "item_id": str(grants_item_id), "quantity": total_qty, "source": "market"}]:
            try:
                rows = _as_list(sb.table(table).insert(payload).execute())
                if rows:
                    return rows[0]
            except Exception:
                continue

    return None


def _decrease_stock(sb, item: dict[str, Any], quantity: int) -> dict[str, Any]:
    current_stock = item.get("stock") if item.get("stock") is not None else item.get("quantity")
    if current_stock is None:
        return item

    new_stock = max(0, int(_number(current_stock, 0)) - quantity)

    for column in ("item_id", "shop_item_id", "id"):
        if not item.get(column):
            continue

        try:
            rows = _as_list(sb.table("shop_items").update({"stock": new_stock}).eq(column, str(item.get(column))).execute())
            if rows:
                return rows[0]
        except Exception:
            try:
                rows = _as_list(sb.table("shop_items").update({"quantity": new_stock}).eq(column, str(item.get(column))).execute())
                if rows:
                    return rows[0]
            except Exception:
                continue

    return {**item, "stock": new_stock}


@router.post("/orders/{order_id}/fulfill")
def fulfill_shop_order(
    order_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    order, _ = _load_order(sb, order_id)
    shop, item = _load_shop_for_order(sb, order)

    if not _can_manage_shop(shop, actor):
        raise HTTPException(status_code=403, detail="You can only fulfill orders for your own shop.")

    quantity = int(_number(order.get("quantity") or order.get("qty"), 1))
    stock = item.get("stock") if item.get("stock") is not None else item.get("quantity")

    if stock is not None and int(_number(stock, 0)) < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock to fulfill this order.")

    updated_item = _decrease_stock(sb, item, quantity)
    inventory_row = _insert_inventory_item(sb, order, item, quantity)
    updated_order = _update_order_status(sb, order_id, "FULFILLED", actor, payload.get("note") or payload.get("staff_note"))

    log_activity(
        event_type="shop_order_fulfilled",
        label=f"Shop order fulfilled: {item.get('name') or item.get('item_name') or 'Item'}",
        status="fulfilled",
        actor_discord_id=actor,
        character_id=order.get("character_id") or order.get("oc_id"),
        amount=quantity,
        note=payload.get("note") or payload.get("staff_note"),
        source="shop_owner_orders",
        details={
            "order_id": order_id,
            "shop_id": _shop_id(shop),
            "item_id": order.get("item_id") or order.get("shop_item_id"),
            "inventory_inserted": bool(inventory_row),
        },
        webhook_title="📦 Shop Order Fulfilled",
        webhook_description=f"{item.get('name') or item.get('item_name') or 'Item'} ×{quantity}",
    )

    return {
        "order": updated_order,
        "item": updated_item,
        "inventory_row": inventory_row,
        "message": (
            "Order fulfilled and inventory updated."
            if inventory_row else
            "Order fulfilled. Inventory was skipped — either no character was attached to this order, "
            "or this shop item has no grants_item_id set (link it to an item in the Items table in Supabase)."
        ),
        "inventory_granted": bool(inventory_row),
        "grants_item_id": item.get("grants_item_id"),
    }
