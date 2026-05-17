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
    return {
        "shop_id": _shop_id(row),
        "name": row.get("name") or row.get("shop_name") or "Unnamed Shop",
        "description": row.get("description") or row.get("blurb") or row.get("details"),
        "owner_discord_id": _owner_id(row),
        "status": row.get("status") or ("Open" if row.get("is_active", True) else "Closed"),
        "is_active": bool(row.get("is_active", True)) if row.get("is_active") is not None else str(row.get("status") or "").lower() not in {"closed", "archived", "inactive"},
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
        raise HTTPException(status_code=403, detail="You can only manage your own shop.")

    update_payload: dict[str, Any] = {}

    for source_key, dest_key, max_len in [
        ("name", "name", 120),
        ("description", "description", 1000),
        ("image_url", "image_url", 800),
        ("status", "status", 80),
    ]:
        if source_key in payload:
            update_payload[dest_key] = _clean(payload.get(source_key), max_len)

    if "is_active" in payload:
        update_payload["is_active"] = _bool(payload.get("is_active"), True)

    if not update_payload:
        raise HTTPException(status_code=400, detail="No shop fields provided.")

    rows = _as_list(
        sb.table("shops")
        .update(update_payload)
        .eq(id_column, shop_id)
        .execute()
    )

    updated = rows[0] if rows else {**shop, **update_payload}

    log_activity(
        event_type="shop_updated",
        label=f"Shop updated: {updated.get('name') or shop.get('name') or 'Shop'}",
        status="updated",
        actor_discord_id=actor,
        source="shop_owner_tools",
        details={"shop_id": shop_id, "updated_fields": list(update_payload.keys())},
        webhook_title="🏪 Shop Updated",
        webhook_description=f"{updated.get('name') or shop.get('name') or 'Shop'} was updated.",
    )

    return {"shop": _normalize_shop(updated), "message": "Shop updated."}


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
        raise HTTPException(status_code=403, detail="You can only manage your own shop.")

    name = _clean(payload.get("name") or payload.get("item_name"), 160)
    if not name:
        raise HTTPException(status_code=400, detail="Item name is required.")

    insert_payload: dict[str, Any] = {
        "guild_id": get_guild_id(),
        "shop_id": shop_id,
        "name": name,
        "description": _clean(payload.get("description"), 1000),
        "category": _clean(payload.get("category"), 80) or "General",
        "price": _number(payload.get("price"), 0),
        "stock": int(_number(payload.get("stock"), 0)),
        "requires_approval": _bool(payload.get("requires_approval"), False),
        "is_active": _bool(payload.get("is_active"), True),
    }

    if payload.get("currency_id"):
        insert_payload["currency_id"] = str(payload.get("currency_id"))

    if payload.get("image_url"):
        insert_payload["image_url"] = _clean(payload.get("image_url"), 800)

    try:
        rows = _as_list(sb.table("shop_items").insert(insert_payload).execute())
    except Exception:
        # Fallback for older schemas that use item_name instead of name/category.
        fallback = {
            "guild_id": get_guild_id(),
            "shop_id": shop_id,
            "item_name": name,
            "description": insert_payload["description"],
            "price": insert_payload["price"],
            "stock": insert_payload["stock"],
            "requires_approval": insert_payload["requires_approval"],
            "is_active": insert_payload["is_active"],
        }
        if insert_payload.get("currency_id"):
            fallback["currency_id"] = insert_payload["currency_id"]
        rows = _as_list(sb.table("shop_items").insert(fallback).execute())

    item = rows[0] if rows else insert_payload

    log_activity(
        event_type="shop_item_created",
        label=f"Shop item created: {name}",
        status="created",
        actor_discord_id=actor,
        source="shop_owner_tools",
        amount=insert_payload.get("price"),
        details={"shop_id": shop_id, "item": insert_payload},
        webhook_title="🧾 Shop Item Created",
        webhook_description=f"{name} was added to {shop.get('name') or 'a shop'}.",
    )

    return {"item": _normalize_item(item), "message": "Item created."}


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
