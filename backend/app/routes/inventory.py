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
        "source": row.get("source") or row.get("origin") or source,
        "is_locked": bool(row.get("is_locked") or row.get("locked") or row.get("bound")),
        "is_equipped": bool(row.get("is_equipped") or row.get("equipped")),
        "is_public": row.get("is_public"),
        "metadata": row.get("metadata") or row.get("details_json") or row,
        "raw": row,
    }


def _enrich_with_item_names(sb, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For rows that have item_id but no name, look up names from the items table."""
    needs_name = [r for r in rows if not _item_name(r).replace("Unnamed Item", "").strip() and r.get("item_id")]
    if not needs_name:
        return rows

    # Fetch each item individually using eq() — avoids in_() which may not be available
    item_lookup: dict[str, dict[str, Any]] = {}
    for row in needs_name:
        iid = str(row.get("item_id") or "")
        if not iid or iid in item_lookup:
            continue
        for id_col in ("item_id", "id"):
            try:
                found = _safe_rows(
                    sb.table("items")
                    .select("item_id,id,name,item_class,description")
                    .eq(id_col, iid)
                    .limit(1)
                )
                if found:
                    key = str(found[0].get("item_id") or found[0].get("id") or "")
                    if key:
                        item_lookup[key] = found[0]
                    break
            except Exception:
                pass

    enriched = []
    for row in rows:
        iid = str(row.get("item_id") or "")
        if iid and iid in item_lookup and not _item_name(row).replace("Unnamed Item", "").strip():
            meta = item_lookup[iid]
            row = {**row,
                   "name": meta.get("name") or "Unnamed Item",
                   "item_type": meta.get("item_class") or row.get("item_type"),
                   "description": row.get("description") or meta.get("description")}
        enriched.append(row)
    return enriched


def _inventory_rows(sb, character_id: str) -> list[dict[str, Any]]:
    candidates = [
        ("inventory_entries", "character_id"),  # primary table confirmed from live schema
        ("character_inventory", "character_id"),
        ("oc_inventory", "character_id"),
        ("inventory", "character_id"),
        ("items_owned", "character_id"),
        ("character_items", "character_id"),
    ]

    all_items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for table, column in candidates:
        rows = _safe_rows(
            sb.table(table)
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, character_id)
            .limit(500)
        )

        if not rows:
            rows = _safe_rows(
                sb.table(table)
                .select("*")
                .eq(column, character_id)
                .limit(500)
            )

        # Enrich rows that only have item_id (like inventory_entries) with names from items table
        rows = _enrich_with_item_names(sb, rows)

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

    return {
        "character": {
            "character_id": character.get("character_id") or character.get("id") or character_id,
            "name": character.get("name") or "Unnamed OC",
            "owner_discord_id": _owner_id(character),
        },
        "items": items,
        "currencies": currencies,
        "types": types,
        "total_items": len(items),
        "total_quantity": sum(_number(item.get("quantity"), 0) for item in items),
    }
