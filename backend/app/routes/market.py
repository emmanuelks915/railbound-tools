from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

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


def _clean(value: Any, max_len: int = 500) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned[:max_len] if cleaned else None


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
    for key in ("category", "item_class", "item_type", "type", "rarity"):
        val = row.get(key)
        if val and str(val).lower() not in {"item", "material", "consumable", "equipment", "service", "role", "currency"}:
            return str(val)
    # Fall back to item_type if no human-readable category found
    for key in ("category", "item_class", "item_type", "type"):
        if row.get(key):
            return str(row.get(key)).title()
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
    owner_id = _shop_owner(row)

    return {
        "shop_id": sid,
        "name": row.get("name") or row.get("shop_name") or "Unnamed Shop",
        "description": row.get("description") or row.get("blurb") or row.get("details"),
        "owner_discord_id": owner_id,
        "shop_type": "player" if owner_id else "npc",
        "status": row.get("status") or ("Open" if _is_active(row) else "Closed"),
        "is_active": _is_active(row),
        "channel_id": row.get("channel_id"),
        "thread_id": row.get("thread_id"),
        "image_url": row.get("image_url") or row.get("banner_url") or row.get("shop_banner_url"),
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

    all_item_rows = _load_items(sb)
    categories = sorted({
        _item_category(row)
        for row in all_item_rows
        if _item_category(row)
    })

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


@router.post("/shops")
def create_npc_shop(
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    """Staff-only: create an NPC storefront (no owner_discord_id)."""
    actor = _require_staff(actor_discord_id)
    sb = get_supabase()

    name = _clean(payload.get("name") or payload.get("shop_name"), 120)
    if not name:
        raise HTTPException(status_code=400, detail="Storefront name is required.")

    base_payload: dict[str, Any] = {
        "guild_id": get_guild_id(),
        "name": name,
        "description": _clean(payload.get("description"), 1000),
        "enabled": True,
        "is_forum": False,
        "treasury_cut_bps": 0,
    }

    if payload.get("image_url"):
        base_payload["image_url"] = _clean(payload.get("image_url"), 800)

    last_error = None
    rows = []
    for attempt in [base_payload, {k: v for k, v in base_payload.items() if k not in {"is_forum", "treasury_cut_bps"}}]:
        try:
            rows = _as_list(sb.table("shops").insert(attempt).execute())
            if rows:
                break
        except Exception as exc:
            last_error = exc

    if not rows:
        raise HTTPException(status_code=400, detail=f"Could not create NPC storefront: {last_error}")

    shop = rows[0]

    log_activity(
        event_type="npc_shop_created",
        label=f"NPC shop created: {name}",
        status="created",
        actor_discord_id=actor,
        source="market_staff",
        details={"shop_id": _shop_id(shop), "name": name},
        webhook_title="🏪 NPC Shop Created",
        webhook_description=f'"{name}" was added as an NPC storefront.',
    )

    return {
        "shop": _normalize_shop(shop, []),
        "message": f'NPC shop "{name}" created.',
    }


@router.patch("/shops/{shop_id}")
def update_shop(
    shop_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    """Staff can update any shop; players can update their own."""
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    # Load shop
    shop = None
    for col in ("shop_id", "id"):
        rows = _safe_rows(sb.table("shops").select("*").eq(col, shop_id).limit(1))
        if rows:
            shop = rows[0]
            break

    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found.")

    owner_id = _shop_owner(shop)
    if not is_staff(actor) and (not owner_id or str(actor) != str(owner_id)):
        raise HTTPException(status_code=403, detail="You can only edit your own shop.")

    update: dict[str, Any] = {}
    if "name" in payload:
        update["name"] = _clean(payload["name"], 120)
    if "description" in payload:
        update["description"] = _clean(payload["description"], 1000)
    if "image_url" in payload:
        update["image_url"] = _clean(payload["image_url"], 800)
    if "status" in payload:
        status_val = str(payload["status"]).strip()
        update["enabled"] = status_val.lower() == "open"
        update["status"] = status_val
    if "is_active" in payload:
        update["enabled"] = bool(payload["is_active"])

    if not update:
        raise HTTPException(status_code=400, detail="No fields to update.")

    id_col = "shop_id" if shop.get("shop_id") else "id"
    rows = _safe_rows(sb.table("shops").update(update).eq(id_col, shop_id).execute())
    updated = rows[0] if rows else {**shop, **update}

    return {"shop": _normalize_shop(updated, []), "message": "Shop updated."}



# ---------------------------------------------------------------------------
# Full purchase flow — mirrors Keystone's _buy_internal exactly:
# 1. Validate item, stock, character
# 2. Deduct currency (rpc_apply_company_transaction)
# 3. Decrement stock
# 4. Insert order row
# 5. If no approval required: grant inventory immediately (apply_inventory_delta)
# ---------------------------------------------------------------------------

def _resolve_currency(sb, item: dict[str, Any]) -> str | None:
    cid = item.get("currency_id")
    if cid:
        return str(cid)
    for rows in [
        _safe_rows(sb.table("currencies").select("currency_id,id").eq("guild_id", get_guild_id()).order("created_at").limit(1)),
        _safe_rows(sb.table("currencies").select("currency_id,id").limit(1)),
    ]:
        if rows:
            return str(rows[0].get("currency_id") or rows[0].get("id") or "")
    return None


def _resolve_vendor_company(sb, item: dict[str, Any]) -> str | None:
    """Get the vendor company that receives payment.
    Priority: item.vendor_company_id → name contains 'treasury' → first company.
    (No is_treasury column exists in this schema.)
    """
    vid = item.get("vendor_company_id")
    if vid:
        return str(vid)

    guild_id = get_guild_id()

    # Find by treasury name — fetch all and filter in Python since ilike unavailable
    rows = _safe_rows(
        sb.table("companies")
        .select("company_id,name")
        .eq("guild_id", guild_id)
        .limit(50)
    )
    # Prefer name containing "treasury"
    for row in rows:
        if "treasury" in str(row.get("name") or "").lower():
            return str(row.get("company_id") or "")
    # Fall back to first company
    if rows:
        return str(rows[0].get("company_id") or "")

    return None


def _deduct_wallet(sb, *, character_id: str, currency_id: str, amount: int, actor: int,
                   vendor_company_id: str, reason: str) -> None:
    """Deduct from buyer character wallet → vendor company. Uses rpc_apply_company_transaction."""
    payload = {
        "p_guild_id": get_guild_id(),
        "p_currency_id": currency_id,
        "p_amount": amount,
        "p_actor_discord_id": actor,
        "p_tx_type": "DEPOSIT",
        "p_from_character_id": character_id,
        "p_to_company_id": vendor_company_id,
        "p_reason": reason,
    }
    try:
        res = sb.rpc("rpc_apply_company_transaction", payload).execute()
        data = getattr(res, "data", None) or []
        if not data:
            raise RuntimeError("Transaction returned no data")
    except Exception as exc:
        msg = str(exc)
        if "insufficient" in msg.lower() or "INSUFFICIENT" in msg:
            raise HTTPException(status_code=400, detail="Insufficient funds to complete this purchase.")
        raise HTTPException(status_code=400, detail=f"Payment failed: {exc}")


def _grant_inventory(sb, *, character_id: str, item_id: str, qty: int, actor: int,
                     context: str, note: str) -> tuple[bool, str]:
    """Grant inventory via apply_inventory_delta RPC. Returns (success, error_message)."""
    try:
        sb.rpc("apply_inventory_delta", {
            "p_guild_id": get_guild_id(),
            "p_character_id": character_id,
            "p_item_id": item_id,
            "p_delta": qty,
            "p_actor_discord_id": actor,
            "p_context": context,
            "p_note": note,
        }).execute()
        return True, ""
    except Exception as exc:
        return False, str(exc)


@router.post("/items/{item_id}/request")
def request_market_item(
    item_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    # Load item
    item_rows = []
    for column in ("item_id", "shop_item_id", "id"):
        item_rows = _safe_rows(sb.table("shop_items").select("*").eq(column, item_id).limit(1))
        if item_rows:
            break
    if not item_rows:
        raise HTTPException(status_code=404, detail="Shop item not found.")

    item = item_rows[0]
    item_name = _item_name(item)
    quantity = max(1, int(_number(payload.get("quantity"), 1)))
    character_id = str(payload.get("character_id") or "").strip() or None
    note = payload.get("note")

    requires_approval = bool(item.get("requires_approval") or item.get("needs_approval"))
    unit_price = int(_number(item.get("price") or item.get("cost"), 0))
    subtotal = unit_price * quantity

    # Validate
    if unit_price <= 0:
        raise HTTPException(status_code=400, detail="This item has an invalid price and cannot be purchased.")

    stock = item.get("stock")
    if stock is not None and int(stock) < quantity:
        raise HTTPException(status_code=400, detail=f"Not enough stock. Available: {int(stock)}.")

    currency_id = _resolve_currency(sb, item)
    if not currency_id:
        raise HTTPException(status_code=400, detail="No currency configured for this item.")

    shop_id = str(item.get("shop_id") or "")
    if not shop_id:
        raise HTTPException(status_code=400, detail="Item has no shop_id.")

    vendor_company_id = _resolve_vendor_company(sb, item)
    if not vendor_company_id:
        raise HTTPException(status_code=400, detail="No vendor company found to receive payment. Ask staff to configure a treasury company.")

    reason_base = f"shop purchase item={str(item_id)[:8]} qty={quantity} name={item_name}"

    # 1. Deduct currency from buyer wallet → vendor company
    if character_id:
        _deduct_wallet(
            sb,
            character_id=character_id,
            currency_id=currency_id,
            amount=subtotal,
            actor=actor,
            vendor_company_id=vendor_company_id,
            reason=reason_base,
        )

    # 2. Decrement stock
    if stock is not None:
        new_stock = max(0, int(stock) - quantity)
        try:
            sb.table("shop_items").update({"stock": new_stock}).eq("item_id", item_id).execute()
        except Exception:
            pass

    # 3. Insert order (status PAID if approval needed, FULFILLED if instant)
    order_status = "PAID" if requires_approval else "FULFILLED"
    order_payload: dict[str, Any] = {
        "guild_id": get_guild_id(),
        "item_id": item_id,
        "shop_id": shop_id,
        "buyer_discord_id": str(actor),
        "currency_id": currency_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "fee": 0,
        "total": subtotal,
        "status": order_status,
        "requires_approval": requires_approval,
        "vendor_company_id": vendor_company_id,
        "reason": note or reason_base,
    }
    if character_id:
        order_payload["buyer_character_id"] = character_id

    try:
        inserted = _as_list(sb.table("shop_orders").insert(order_payload).execute())
        order_row = inserted[0] if inserted else None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not create order: {exc}")

    if order_row is None:
        raise HTTPException(status_code=400, detail="Order insert returned no rows.")

    order_id = str(order_row.get("order_id") or "")

    # 4. Instant fulfillment — grant inventory immediately if no approval needed
    inv_granted = False
    inv_error = ""
    if not requires_approval and character_id:
        grants_item_id = item.get("grants_item_id")
        grants_qty = int(item.get("grants_qty") or 1)
        if grants_item_id and grants_qty > 0:
            inv_granted, inv_error = _grant_inventory(
                sb,
                character_id=character_id,
                item_id=str(grants_item_id),
                qty=grants_qty * quantity,
                actor=actor,
                context="shop_fulfill_instant",
                note=f"order={order_id[:8]} shop_item={str(item_id)[:8]}",
            )
        elif not grants_item_id:
            inv_error = f"grants_item_id not set on shop item {str(item_id)[:8]}"

    log_activity(
        event_type="market_item_purchased",
        label=f"Shop purchase: {item_name} ×{quantity}",
        status=order_status,
        actor_discord_id=actor,
        character_id=character_id,
        character_name=None,
        amount=quantity,
        note=note,
        source="market",
        details={"item_id": item_id, "item_name": item_name, "quantity": quantity,
                 "subtotal": subtotal, "inv_granted": inv_granted},
        webhook_title="🛒 Shop Purchase",
        webhook_description=f"{item_name} ×{quantity} — {subtotal} currency",
    )

    if requires_approval:
        message = f"Order submitted for {item_name} ×{quantity}. Awaiting staff approval."
    elif inv_granted:
        message = f"Purchase complete! {item_name} ×{quantity} delivered to inventory."
    else:
        message = f"Purchase complete! Inventory grant failed: {inv_error or 'unknown error'}"

    return {
        "order": order_row,
        "message": message,
        "inv_granted": inv_granted,
        "inv_error": inv_error,
        "requires_approval": requires_approval,
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
