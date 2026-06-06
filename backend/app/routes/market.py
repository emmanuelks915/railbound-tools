from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

try:
    from app.utils.activity_logger import log_activity
except Exception:  # pragma: no cover
    def log_activity(**kwargs):
        return None


router = APIRouter(prefix="/api/market", tags=["market"])


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


def _require_staff(actor_discord_id: int | None) -> int:
    actor = _require_login(actor_discord_id)
    if not is_staff(actor):
        raise HTTPException(status_code=403, detail="Staff only.")
    return actor


def _number(value: Any, default: int | float = 0) -> int | float:
    if value is None or value == "":
        return default
    try:
        amount = float(value)
        return int(amount) if amount.is_integer() else round(amount, 2)
    except Exception:
        return default


def _currency_lookup(sb, currency_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not currency_ids:
        return {}

    rows = _safe_rows(
        sb.table("currencies")
        .select("*")
        .eq("guild_id", get_guild_id())
        .in_("currency_id", list(currency_ids))
        .limit(500)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("currencies")
            .select("*")
            .in_("currency_id", list(currency_ids))
            .limit(500)
        )

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("currency_id") or row.get("id") or "")
        if cid:
            out[cid] = row
    return out


def _load_shops(sb) -> list[dict[str, Any]]:
    rows = _safe_rows(
        sb.table("shops")
        .select("*")
        .eq("guild_id", get_guild_id())
        .limit(500)
    )

    if not rows:
        rows = _safe_rows(sb.table("shops").select("*").limit(500))

    return rows


def _load_items(sb) -> list[dict[str, Any]]:
    rows = _safe_rows(
        sb.table("shop_items")
        .select("*")
        .eq("guild_id", get_guild_id())
        .limit(1000)
    )

    if not rows:
        rows = _safe_rows(sb.table("shop_items").select("*").limit(1000))

    return rows


def _shop_id(row: dict[str, Any]) -> str:
    return str(row.get("shop_id") or row.get("id") or "")


def _item_id(row: dict[str, Any]) -> str:
    return str(row.get("item_id") or row.get("shop_item_id") or row.get("id") or "")


def _item_name(row: dict[str, Any]) -> str:
    for key in ("item_name", "name", "title", "label"):
        if row.get(key):
            return str(row.get(key))
    return "Unnamed Item"


def _item_description(row: dict[str, Any]) -> str | None:
    for key in ("description", "details", "notes", "blurb"):
        if row.get(key):
            return str(row.get(key))
    return None


def _item_category(row: dict[str, Any]) -> str:
    for key in ("category", "item_type", "type", "rarity"):
        if row.get(key):
            return str(row.get(key))
    return "General"


def _price(row: dict[str, Any]) -> int | float:
    for key in ("price", "cost", "amount"):
        if row.get(key) is not None:
            return _number(row.get(key), 0)
    return 0


def _stock(row: dict[str, Any]) -> int | float | None:
    for key in ("stock", "quantity", "qty"):
        if row.get(key) is not None:
            return _number(row.get(key), 0)
    return None


def _is_active(row: dict[str, Any]) -> bool:
    if row.get("enabled") is not None:
        return bool(row.get("enabled"))
    if row.get("is_active") is not None:
        return bool(row.get("is_active"))
    if row.get("active") is not None:
        return bool(row.get("active"))
    if str(row.get("status") or "").lower() in {"inactive", "archived", "closed"}:
        return False
    return True


def _shop_owner(row: dict[str, Any]) -> str | None:
    for key in ("owner_discord_id", "user_id", "discord_id", "player_discord_id"):
        if row.get(key) is not None:
            return str(row.get(key))
    return None


def _normalize_shop(row: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    sid = _shop_id(row)
    shop_items = [item for item in items if str(item.get("shop_id") or item.get("store_id") or "") == sid]
    active_items = [item for item in shop_items if _is_active(item)]

    return {
        "shop_id": sid,
        "name": row.get("name") or row.get("shop_name") or "Unnamed Shop",
        "description": row.get("description") or row.get("blurb") or row.get("details"),
        "owner_discord_id": _shop_owner(row),
        "status": row.get("status") or ("Open" if _is_active(row) else "Closed"),
        "is_active": _is_active(row),
        "channel_id": row.get("channel_id"),
        "thread_id": row.get("thread_id"),
        "image_url": row.get("image_url") or row.get("banner_url"),
        "item_count": len(active_items),
        "raw": row,
    }


def _normalize_item(row: dict[str, Any], shops: dict[str, dict[str, Any]], currencies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sid = str(row.get("shop_id") or row.get("store_id") or "")
    currency_id = str(row.get("currency_id") or "")
    currency = currencies.get(currency_id, {})

    return {
        "item_id": _item_id(row),
        "shop_id": sid,
        "shop_name": shops.get(sid, {}).get("name") or shops.get(sid, {}).get("shop_name") or "Market",
        "name": _item_name(row),
        "description": _item_description(row),
        "category": _item_category(row),
        "price": _price(row),
        "stock": _stock(row),
        "currency_id": currency_id or None,
        "currency_name": currency.get("name") or row.get("currency") or row.get("currency_name") or "Currency",
        "currency_ticker": currency.get("ticker") or currency.get("code") or row.get("ticker"),
        "currency_emoji": currency.get("emoji") or row.get("emoji"),
        "requires_approval": bool(row.get("requires_approval") or row.get("needs_approval")),
        "is_active": _is_active(row),
        "image_url": row.get("image_url") or row.get("thumbnail_url"),
        "role_id": row.get("role_id"),
        "raw": row,
    }


@router.get("/overview")
def get_market_overview(
    actor_discord_id: int | None = Depends(actor_from_header),
    search: str | None = Query(None),
    category: str = Query("all"),
    shop_id: str = Query("all"),
    active_only: bool = Query(True),
):
    _require_login(actor_discord_id)
    sb = get_supabase()

    shop_rows = _load_shops(sb)
    item_rows = _load_items(sb)

    if active_only:
        shop_rows = [row for row in shop_rows if _is_active(row)]
        item_rows = [
            row for row in item_rows
            if _is_active(row)
            and bool(row.get("purchasable", True))
            and (
                not bool(row.get("requires_approval"))
                or str(row.get("review_status") or "").lower() == "approved"
            )
        ]

    shops_by_id = {_shop_id(row): row for row in shop_rows if _shop_id(row)}
    currency_ids = {str(row.get("currency_id")) for row in item_rows if row.get("currency_id")}
    currencies = _currency_lookup(sb, currency_ids)

    shops = [_normalize_shop(row, item_rows) for row in shop_rows]
    items = [_normalize_item(row, shops_by_id, currencies) for row in item_rows]

    if shop_id != "all":
        items = [item for item in items if str(item.get("shop_id")) == str(shop_id)]

    if category != "all":
        items = [item for item in items if str(item.get("category") or "").lower() == category.lower()]

    if search:
        q = search.lower().strip()
        items = [
            item for item in items
            if q in " ".join([
                item.get("name") or "",
                item.get("description") or "",
                item.get("category") or "",
                item.get("shop_name") or "",
            ]).lower()
        ]
        shops = [
            shop for shop in shops
            if q in " ".join([
                shop.get("name") or "",
                shop.get("description") or "",
                shop.get("status") or "",
            ]).lower()
        ]

    categories = sorted({item.get("category") or "General" for item in [_normalize_item(row, shops_by_id, currencies) for row in item_rows]})

    return {
        "shops": shops,
        "items": items,
        "categories": categories,
        "summary": {
            "shops": len(shops),
            "items": len(items),
            "approval_required": len([item for item in items if item.get("requires_approval")]),
            "out_of_stock": len([item for item in items if item.get("stock") == 0]),
        },
        "is_staff": is_staff(int(actor_discord_id)) if actor_discord_id is not None else False,
    }


@router.post("/items/{item_id}/request")
def request_market_item(
    item_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    item_rows = []
    for column in ("item_id", "shop_item_id", "id"):
        item_rows = _safe_rows(
            sb.table("shop_items")
            .select("*")
            .eq(column, item_id)
            .limit(1)
        )
        if item_rows:
            break

    if not item_rows:
        raise HTTPException(status_code=404, detail="Shop item not found.")

    item = item_rows[0]
    quantity = max(1, int(_number(payload.get("quantity"), 1)))
    character_id = payload.get("character_id")
    note = payload.get("note")

    order_payload = {
        "guild_id": get_guild_id(),
        "item_id": item_id,
        "quantity": quantity,
        "user_id": str(actor),
        "status": "pending" if bool(item.get("requires_approval") or item.get("needs_approval")) else "approved",
    }

    if character_id:
        order_payload["character_id"] = str(character_id)

    if note:
        order_payload["note"] = str(note)

    order_row = None
    try:
        inserted = _as_list(sb.table("shop_orders").insert(order_payload).execute())
        if inserted:
            order_row = inserted[0]
    except Exception:
        # Some schemas use shop_item_id or different optional columns. Fall back minimal.
        fallback = {
            "guild_id": get_guild_id(),
            "item_id": item_id,
            "quantity": quantity,
            "user_id": str(actor),
            "status": order_payload["status"],
        }
        inserted = _as_list(sb.table("shop_orders").insert(fallback).execute())
        if inserted:
            order_row = inserted[0]

    log_activity(
        event_type="market_item_requested",
        label=f"Market item requested: {_item_name(item)}",
        status=order_payload["status"],
        actor_discord_id=actor,
        character_id=character_id,
        character_name=None,
        amount=quantity,
        note=note,
        source="market",
        details={"item_id": item_id, "item_name": _item_name(item), "quantity": quantity},
        webhook_title="🛒 Market Item Requested",
        webhook_description=f"{_item_name(item)} ×{quantity}",
    )

    return {
        "order": order_row or order_payload,
        "message": "Purchase request submitted." if order_payload["status"] == "pending" else "Purchase recorded.",
    }


@router.get("/orders")
def get_market_orders(
    actor_discord_id: int | None = Depends(actor_from_header),
    status: str = Query("pending"),
):
    actor = _require_login(actor_discord_id)
    staff = is_staff(actor)
    sb = get_supabase()

    rows = _safe_rows(
        sb.table("shop_orders")
        .select("*")
        .eq("guild_id", get_guild_id())
        .order("created_at", desc=True)
        .limit(250)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("shop_orders")
            .select("*")
            .order("created_at", desc=True)
            .limit(250)
        )

    if status != "all":
        rows = [row for row in rows if str(row.get("status") or "pending").lower() == status.lower()]

    if not staff:
        rows = [row for row in rows if str(row.get("user_id") or row.get("discord_id") or "") == str(actor)]

    return {"orders": rows, "is_staff": staff}
