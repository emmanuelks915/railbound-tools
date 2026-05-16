from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["oc-balances"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _safe_table_rows(sb, table: str, *, character_id: str, id_column: str = "character_id", limit: int = 100) -> list[dict[str, Any]]:
    rows = _safe_rows(
        sb.table(table)
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq(id_column, character_id)
        .limit(limit)
    )

    if rows:
        return rows

    return _safe_rows(
        sb.table(table)
        .select("*")
        .eq(id_column, character_id)
        .limit(limit)
    )


def _load_character(sb, character_id: str) -> dict[str, Any] | None:
    rows = _safe_rows(
        sb.table("characters")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(1)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq("character_id", character_id)
            .limit(1)
        )

    if not rows:
        rows = _safe_rows(
            sb.table("characters")
            .select("*")
            .eq("id", character_id)
            .limit(1)
        )

    return rows[0] if rows else None


def _owner_id(character: dict[str, Any]) -> str | None:
    value = (
        character.get("user_id")
        or character.get("discord_id")
        or character.get("owner_discord_id")
        or character.get("player_discord_id")
    )
    return str(value) if value is not None else None


def _authorize(character: dict[str, Any], actor_discord_id: int | None) -> None:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    owner_id = _owner_id(character)
    if owner_id is not None and str(owner_id) == str(actor_discord_id):
        return

    if is_staff(int(actor_discord_id)):
        return

    raise HTTPException(status_code=403, detail="You can only view balances for your own OC.")


def _number(value: Any) -> int | float | None:
    if value is None or value == "":
        return None

    try:
        amount = float(value)
        if amount.is_integer():
            return int(amount)
        return round(amount, 2)
    except Exception:
        return None


def _xp_from_character(character: dict[str, Any]) -> dict[str, Any]:
    xp = {
        "available_xp": None,
        "current_xp": None,
        "total_xp": None,
        "spent_xp": None,
        "source": "characters",
    }

    for key in ("available_xp", "current_xp", "total_xp", "spent_xp", "xp"):
        if key in character:
            value = _number(character.get(key))
            if key == "xp":
                xp["available_xp"] = value
                xp["current_xp"] = value
            else:
                xp[key] = value

    return xp


def _xp_from_wallet_tables(sb, character_id: str, fallback: dict[str, Any]) -> dict[str, Any]:
    xp_tables = [
        "oc_xp_wallets",
        "character_xp_wallets",
        "xp_wallets",
        "oc_xp",
        "character_xp",
    ]

    id_columns = ["character_id", "oc_id", "id"]

    for table in xp_tables:
        for id_column in id_columns:
            rows = _safe_table_rows(sb, table, character_id=character_id, id_column=id_column, limit=5)
            if not rows:
                continue

            row = rows[0]
            out = dict(fallback)
            out["source"] = table

            value_map = {
                "available_xp": ["available_xp", "available", "balance", "current_xp", "xp"],
                "current_xp": ["current_xp", "current", "balance", "available_xp", "xp"],
                "total_xp": ["total_xp", "earned_xp", "lifetime_xp", "total"],
                "spent_xp": ["spent_xp", "spent"],
            }

            for out_key, possible_keys in value_map.items():
                for key in possible_keys:
                    if key in row and row.get(key) is not None:
                        out[out_key] = _number(row.get(key))
                        break

            return out

    return fallback


def _currency_lookup(sb, currency_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not currency_ids:
        return {}

    rows = _safe_rows(
        sb.table("currencies")
        .select("*")
        .eq("guild_id", get_guild_id())
        .in_("currency_id", currency_ids)
        .limit(250)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("currencies")
            .select("*")
            .in_("currency_id", currency_ids)
            .limit(250)
        )

    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("currency_id") or row.get("id") or "")
        if cid:
            lookup[cid] = row

    return lookup


def _currency_balances(sb, character_id: str) -> list[dict[str, Any]]:
    rows = _safe_table_rows(sb, "wallets", character_id=character_id, id_column="character_id", limit=250)

    if not rows:
        rows = _safe_table_rows(sb, "character_wallets", character_id=character_id, id_column="character_id", limit=250)

    currency_ids = [
        str(row.get("currency_id"))
        for row in rows
        if row.get("currency_id") is not None
    ]

    currencies = _currency_lookup(sb, currency_ids)

    balances: list[dict[str, Any]] = []
    for row in rows:
        currency_id = str(row.get("currency_id") or "")
        currency = currencies.get(currency_id, {})

        balance = (
            row.get("balance")
            if row.get("balance") is not None
            else row.get("amount")
            if row.get("amount") is not None
            else row.get("value")
        )

        balances.append(
            {
                "currency_id": currency_id or None,
                "name": currency.get("name") or row.get("currency") or row.get("currency_name") or "Currency",
                "ticker": currency.get("ticker") or currency.get("code") or row.get("ticker"),
                "emoji": currency.get("emoji") or row.get("emoji"),
                "balance": _number(balance) if balance is not None else 0,
            }
        )

    return balances


@router.get("/characters/{character_id}/balances")
def get_character_balances(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    character = _load_character(sb, character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    _authorize(character, actor_discord_id)

    xp = _xp_from_wallet_tables(sb, character_id, _xp_from_character(character))
    currencies = _currency_balances(sb, character_id)

    return {
        "character_id": character_id,
        "xp": xp,
        "currencies": currencies,
    }
