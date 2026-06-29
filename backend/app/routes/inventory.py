from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _load_character(sb, character_id: str) -> dict[str, Any] | None:
    for column in ("character_id", "id"):
        rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, character_id)
            .limit(1)
        )
        if rows:
            return rows[0]

        rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq(column, character_id)
            .limit(1)
        )
        if rows:
            return rows[0]

    return None


def _owner_id(character: dict[str, Any]) -> str | None:
    value = (
        character.get("user_id")
        or character.get("discord_id")
        or character.get("owner_discord_id")
        or character.get("player_discord_id")
    )
    return str(value) if value is not None else None


def _can_view(character: dict[str, Any], actor_discord_id: int | None) -> bool:
    if actor_discord_id is None:
        return False

    owner_id = _owner_id(character)
    if owner_id is not None and str(owner_id) == str(actor_discord_id):
        return True

    return is_staff(int(actor_discord_id))


def _number(value: Any, default: int | float = 0) -> int | float:
    if value is None or value == "":
        return default

    try:
        amount = float(value)
        return int(amount) if amount.is_integer() else round(amount, 2)
    except Exception:
        return default


def _item_name(row: dict[str, Any]) -> str:
    for key in ("item_name", "name", "title", "label", "shop_item_name"):
        if row.get(key):
            return str(row.get(key))
    return "Unnamed Item"


def _item_type(row: dict[str, Any]) -> str:
    for key in ("item_type", "type", "category", "rarity", "slot"):
        if row.get(key):
            return str(row.get(key))
    return "Item"


def _quantity(row: dict[str, Any]) -> int | float:
    for key in ("quantity", "qty", "amount", "count", "stack"):
        if row.get(key) is not None:
            return _number(row.get(key), 1)
    return 1


def _normalize_item(row: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "inventory_id": str(row.get("inventory_id") or row.get("id") or row.get("item_id") or ""),
        "item_id": str(row.get("item_id") or row.get("shop_item_id") or ""),
        "name": _item_name(row),
        "type": _item_type(row),
        "quantity": _quantity(row),
        "description": row.get("description") or row.get("details") or row.get("notes") or row.get("note"),
        "image_url": row.get("image_url") or row.get("thumbnail_url"),
        "sheet_url": row.get("sheet_url"),
        "source": row.get("source") or row.get("origin") or source,
        "is_locked": bool(row.get("is_locked") or row.get("locked") or row.get("bound")),
        "is_equipped": bool(row.get("is_equipped") or row.get("equipped")),
        "is_public": row.get("is_public"),
        "metadata": row.get("metadata") or row.get("details_json") or row,
        "raw": row,
    }


def _enrich_with_item_names(sb, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For rows that have item_id, always look up name/class from the items table.
    inventory_entries only stores item_id+qty so enrichment is always needed."""
    if not rows:
        return rows

    # Build lookup for all unique item_ids in these rows
    item_lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        iid = str(row.get("item_id") or "")
        if not iid or iid in item_lookup:
            continue
        try:
            found = _safe_rows(
                sb.table("items")
                .select("item_id,name,item_class,description")
                .eq("item_id", iid)
                .limit(1)
            )
            if found:
                item_lookup[iid] = found[0]
        except Exception:
            pass

    enriched = []
    for row in rows:
        iid = str(row.get("item_id") or "")
        if iid and iid in item_lookup:
            meta = item_lookup[iid]
            row = {
                **row,
                "name": meta.get("name") or row.get("name") or "Unnamed Item",
                "item_type": meta.get("item_class") or row.get("item_type") or "Item",
                "description": row.get("description") or meta.get("description"),
            }
        enriched.append(row)
    return enriched


def _inventory_rows(sb, character_id: str) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Step 1: fetch inventory_entries rows
    inv_rows = _safe_rows(
        sb.table("inventory_entries")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(500)
    )
    if not inv_rows:
        inv_rows = _safe_rows(
            sb.table("inventory_entries")
            .select("*")
            .eq("character_id", character_id)
            .limit(500)
        )

    # Step 2: batch-fetch item metadata for all item_ids in one pass
    all_item_ids = [str(r.get("item_id") or "") for r in inv_rows if r.get("item_id")]

    # items table: name, item_class, notes, sheet_url (no description/image_url)
    items_meta: dict[str, dict] = {}
    if all_item_ids:
        meta_rows = _safe_rows(
            sb.table("items")
            .select("item_id,name,item_class,notes,sheet_url")
            .eq("guild_id", get_guild_id())
            .in_("item_id", all_item_ids)
            .limit(500)
        )
        if not meta_rows:
            meta_rows = _safe_rows(
                sb.table("items")
                .select("item_id,name,item_class,notes,sheet_url")
                .in_("item_id", all_item_ids)
                .limit(500)
            )
        for m in meta_rows:
            iid = str(m.get("item_id") or "")
            if iid:
                items_meta[iid] = m

    # shop_items table: description, image_url, usage_information, special_effects
    # keyed by grants_item_id (which equals inventory_entries.item_id)
    shop_meta: dict[str, dict] = {}
    if all_item_ids:
        shop_rows_meta = _safe_rows(
            sb.table("shop_items")
            .select("grants_item_id,description,image_url,thumbnail_url,usage_information,special_effects")
            .eq("guild_id", get_guild_id())
            .in_("grants_item_id", all_item_ids)
            .limit(500)
        )
        if not shop_rows_meta:
            shop_rows_meta = _safe_rows(
                sb.table("shop_items")
                .select("grants_item_id,description,image_url,thumbnail_url,usage_information,special_effects")
                .in_("grants_item_id", all_item_ids)
                .limit(500)
            )
        for s in shop_rows_meta:
            gid_key = str(s.get("grants_item_id") or "")
            if gid_key and gid_key not in shop_meta:
                shop_meta[gid_key] = s

    for row in inv_rows:
        iid = str(row.get("item_id") or "")
        item_info = items_meta.get(iid, {})
        shop_info = shop_meta.get(iid, {})

        name = item_info.get("name") or "Unnamed Item"
        item_class = item_info.get("item_class") or "Item"
        description = (
            shop_info.get("description")
            or shop_info.get("usage_information")
            or shop_info.get("special_effects")
            or item_info.get("notes")
        )
        image_url = shop_info.get("image_url") or shop_info.get("thumbnail_url")
        sheet_url = item_info.get("sheet_url")

        flat = {
            **row,
            "name": name,
            "item_type": item_class,
            "description": description,
            "image_url": image_url,
            "sheet_url": sheet_url,
            "quantity": row.get("qty") or row.get("quantity") or 1,
        }
        item = _normalize_item(flat, "inventory_entries")
        key = f"inv:{iid}:{character_id}"
        if key in seen:
            continue
        seen.add(key)
        all_items.append(item)

    # Fallback tables if inventory_entries had nothing
    if not all_items:
        for table, column in [
            ("character_inventory", "character_id"),
            ("oc_inventory", "character_id"),
            ("inventory", "character_id"),
            ("items_owned", "character_id"),
            ("character_items", "character_id"),
        ]:
            rows = _safe_rows(
                sb.table(table).select("*").eq("guild_id", get_guild_id()).eq(column, character_id).limit(500)
            )
            if not rows:
                rows = _safe_rows(sb.table(table).select("*").eq(column, character_id).limit(500))
            for row in rows:
                item = _normalize_item(row, table)
                key = item["inventory_id"] or f"{table}:{item['name']}:{item['type']}:{item['quantity']}"
                if key in seen:
                    continue
                seen.add(key)
                all_items.append(item)

    return all_items


def _currency_rows(sb, character_id: str) -> list[dict[str, Any]]:
    rows = _safe_rows(
        sb.table("wallets")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(250)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("wallets")
            .select("*")
            .eq("character_id", character_id)
            .limit(250)
        )

    if not rows:
        rows = _safe_rows(
            sb.table("character_wallets")
            .select("*")
            .eq("character_id", character_id)
            .limit(250)
        )

    currency_ids = [str(row.get("currency_id")) for row in rows if row.get("currency_id")]
    currencies: dict[str, dict[str, Any]] = {}

    if currency_ids:
        currency_rows = _safe_rows(
            sb.table("currencies")
            .select("*")
            .eq("guild_id", get_guild_id())
            .in_("currency_id", currency_ids)
            .limit(250)
        )

        if not currency_rows:
            currency_rows = _safe_rows(
                sb.table("currencies")
                .select("*")
                .in_("currency_id", currency_ids)
                .limit(250)
            )

        for row in currency_rows:
            cid = str(row.get("currency_id") or row.get("id") or "")
            if cid:
                currencies[cid] = row

    out: list[dict[str, Any]] = []
    for row in rows:
        currency_id = str(row.get("currency_id") or "")
        currency = currencies.get(currency_id, {})
        out.append(
            {
                "currency_id": currency_id or None,
                "name": currency.get("name") or row.get("currency") or row.get("currency_name") or "Currency",
                "ticker": currency.get("ticker") or currency.get("code") or row.get("ticker"),
                "emoji": currency.get("emoji") or row.get("emoji"),
                "balance": _number(row.get("balance") if row.get("balance") is not None else row.get("amount")),
            }
        )

    return out




@router.get("/characters/{character_id}")
def get_character_inventory(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
    search: str | None = Query(None),
    item_type: str | None = Query(None),
):
    sb = get_supabase()
    character = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    if not _can_view(character, actor_discord_id):
        raise HTTPException(status_code=403, detail="You can only view your own inventory.")

    items = _inventory_rows(sb, character_id)
    currencies = _currency_rows(sb, character_id)

    if search:
        q = search.lower().strip()
        items = [
            item for item in items
            if q in " ".join([
                item.get("name") or "",
                item.get("type") or "",
                item.get("description") or "",
                item.get("source") or "",
            ]).lower()
        ]

    if item_type and item_type != "all":
        items = [item for item in items if str(item.get("type") or "").lower() == item_type.lower()]

    types = sorted({str(item.get("type") or "Item") for item in items})

    # CC calculation
    import math as _math
    oc_stats_rows = _safe_rows(
        sb.table("oc_stats")
        .select("stat_key,stat_value")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(20)
    )
    strength = 0
    for sr in oc_stats_rows:
        if str(sr.get("stat_key") or "") == "strength":
            try:
                strength = int(sr.get("stat_value") or 0)
            except Exception:
                pass
    base_cc = 4 + _math.floor(strength / 150)

    # Active loadout CC
    active_name = str(character.get("active_loadout_name") or "")
    active_cc = None
    if active_name:
        lo_rows = _safe_rows(
            sb.table("inventory_loadouts")
            .select("items")
            .eq("guild_id", get_guild_id())
            .eq("character_id", character_id)
            .eq("loadout_name", active_name)
            .limit(1)
        )
        if lo_rows:
            raw_items = lo_rows[0].get("items") or {}
            cc_used = 0
            for iid, val in raw_items.items():
                worn = val.get("worn", False) if isinstance(val, dict) else False
                if worn:
                    continue
                qty = int(val.get("qty", val) if isinstance(val, dict) else val)
                meta = _safe_rows(sb.table("items").select("wu").eq("item_id", iid).limit(1))
                wu = int(meta[0].get("wu") or 0) if meta else 0
                cc_used += wu * qty
            active_cc = {
                "loadout_name": active_name,
                "base_cc": base_cc,
                "cc_used": cc_used,
                "total_cc": base_cc,
                "over_capacity": cc_used > base_cc,
            }

    return {
        "character": {
            "character_id": character.get("character_id") or character.get("id") or character_id,
            "name": character.get("name") or "Unnamed OC",
            "owner_discord_id": _owner_id(character),
            "active_loadout_name": active_name or None,
        },
        "items": items,
        "currencies": currencies,
        "types": types,
        "total_items": len(items),
        "total_quantity": sum(_number(item.get("quantity"), 0) for item in items),
        "strength": strength,
        "base_cc": base_cc,
        "active_loadout_cc": active_cc,
    }


