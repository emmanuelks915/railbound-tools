from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header, require_staff
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


def _safe_character_rows(sb, table: str, character_id: str, id_column: str = "character_id") -> list[dict[str, Any]]:
    rows = _safe_rows(
        sb.table(table)
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq(id_column, character_id)
        .limit(250)
    )

    if rows:
        return rows

    return _safe_rows(
        sb.table(table)
        .select("*")
        .eq(id_column, character_id)
        .limit(250)
    )


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
    for table in ("oc_xp_wallets", "character_xp_wallets", "xp_wallets", "oc_xp", "character_xp"):
        for id_column in ("character_id", "oc_id", "id"):
            rows = _safe_character_rows(sb, table, character_id, id_column=id_column)
            if not rows:
                continue

            row = rows[0]
            out = dict(fallback)
            out["source"] = table

            fields = {
                "available_xp": ["available_xp", "available", "balance", "current_xp", "xp"],
                "current_xp": ["current_xp", "current", "balance", "available_xp", "xp"],
                "total_xp": ["total_xp", "earned_xp", "lifetime_xp", "total"],
                "spent_xp": ["spent_xp", "spent"],
            }

            for out_key, possible_keys in fields.items():
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
    rows = _safe_character_rows(sb, "wallets", character_id)
    if not rows:
        rows = _safe_character_rows(sb, "character_wallets", character_id)

    currency_ids = [str(row.get("currency_id")) for row in rows if row.get("currency_id") is not None]
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

    return {
        "character_id": character_id,
        "xp": _xp_from_wallet_tables(sb, character_id, _xp_from_character(character)),
        "currencies": _currency_balances(sb, character_id),
    }


# --- Staff Resource Grants v1 ---

@router.get("/staff/resource-grants/options")
def staff_resource_grant_options(actor_discord_id: int | None = Depends(actor_from_header)):
    require_staff(actor_discord_id)

    sb = get_supabase()
    gid = get_guild_id()

    characters = _as_list(
        sb.table("characters")
        .select("character_id,name,user_id,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .order("name", desc=False)
        .limit(1000)
        .execute()
    )

    currencies = _as_list(
        sb.table("currencies")
        .select("currency_id,name,ticker,emoji,is_primary,is_enabled")
        .eq("guild_id", gid)
        .eq("is_enabled", True)
        .order("is_primary", desc=True)
        .order("name", desc=False)
        .limit(100)
        .execute()
    )

    primary_currency = next((row for row in currencies if row.get("is_primary")), currencies[0] if currencies else None)

    return {
        "characters": characters,
        "currencies": currencies,
        "primary_currency": primary_currency,
        "default_starting_xp": 600,
    }


def _load_resource_character(sb, character_id: str) -> dict[str, Any]:
    rows = _as_list(
        sb.table("characters")
        .select("character_id,name,user_id,guild_id,is_active")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(1)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found.")
    return rows[0]


def _primary_currency(sb) -> dict[str, Any]:
    gid = get_guild_id()
    rows = _as_list(
        sb.table("currencies")
        .select("*")
        .eq("guild_id", gid)
        .eq("is_primary", True)
        .eq("is_enabled", True)
        .limit(1)
        .execute()
    )
    if not rows:
        rows = _as_list(
            sb.table("currencies")
            .select("*")
            .eq("guild_id", gid)
            .eq("is_enabled", True)
            .limit(1)
            .execute()
        )
    if not rows:
        raise HTTPException(status_code=400, detail="No enabled currency found.")
    return rows[0]


def _grant_xp_to_oc(sb, character: dict[str, Any], amount: int, staff_id: int, reason: str) -> dict[str, Any]:
    gid = get_guild_id()
    character_id = str(character.get("character_id"))

    wallet_rows = _as_list(
        sb.table("oc_xp_wallets")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .limit(1)
        .execute()
    )

    if wallet_rows:
        wallet = wallet_rows[0]
        new_available = int(wallet.get("available_xp") or 0) + amount
        new_total = int(wallet.get("total_earned_xp") or 0) + amount
        updated = _as_list(
            sb.table("oc_xp_wallets")
            .update({"available_xp": new_available, "total_earned_xp": new_total})
            .eq("guild_id", gid)
            .eq("character_id", character_id)
            .execute()
        )
        wallet = updated[0] if updated else {**wallet, "available_xp": new_available, "total_earned_xp": new_total}
    else:
        inserted = _as_list(
            sb.table("oc_xp_wallets")
            .insert({"guild_id": gid, "character_id": character_id, "available_xp": amount, "total_earned_xp": amount, "total_spent_xp": 0})
            .execute()
        )
        wallet = inserted[0] if inserted else {"guild_id": gid, "character_id": character_id, "available_xp": amount, "total_earned_xp": amount, "total_spent_xp": 0}

    # XP transaction logging should never crash the staff grant after the wallet succeeds.
    # Some databases restrict oc_xp_transactions.source values; if "staff_grant"
    # is rejected, try safer legacy values, then continue with transaction=None.
    tx_rows = []
    tx_payload = {
        "guild_id": gid,
        "character_id": character_id,
        "direction": "earn",
        "amount": amount,
        "source": "staff_grant",
        "reference_type": None,
        "reference_key": "staff_resource_grant",
        "reason": reason,
        "actor_discord_id": staff_id,
        "metadata": {"resource_type": "xp", "staff_grant": True},
    }

    for source_value in ("staff_grant", "staff", "manual", "admin", "adjustment", None):
        try:
            payload = dict(tx_payload)
            payload["source"] = source_value
            tx_rows = _as_list(
                sb.table("oc_xp_transactions")
                .insert(payload)
                .execute()
            )
            break
        except Exception:
            tx_rows = []

    return {"wallet": wallet, "transaction": tx_rows[0] if tx_rows else None}


def _grant_currency_to_oc(sb, character: dict[str, Any], amount: int, staff_id: int, reason: str, currency_id: str | None) -> dict[str, Any]:
    gid = get_guild_id()
    character_id = str(character.get("character_id"))

    currency = None
    if currency_id:
        rows = _as_list(
            sb.table("currencies")
            .select("*")
            .eq("guild_id", gid)
            .eq("currency_id", currency_id)
            .limit(1)
            .execute()
        )
        currency = rows[0] if rows else None

    currency = currency or _primary_currency(sb)
    cid = str(currency.get("currency_id") or currency.get("id") or "")

    if not cid:
        raise HTTPException(status_code=400, detail="Currency ID could not be determined.")

    wallet_rows = _as_list(
        sb.table("wallets")
        .select("*")
        .eq("character_id", character_id)
        .eq("currency_id", cid)
        .limit(1)
        .execute()
    )

    if wallet_rows:
        wallet = wallet_rows[0]
        new_balance = int(wallet.get("balance") or 0) + amount
        updated = _as_list(
            sb.table("wallets")
            .update({"balance": new_balance})
            .eq("character_id", character_id)
            .eq("currency_id", cid)
            .execute()
        )
        wallet = updated[0] if updated else {**wallet, "balance": new_balance}
    else:
        inserted = _as_list(
            sb.table("wallets")
            .insert({"character_id": character_id, "currency_id": cid, "currency": currency.get("ticker") or currency.get("name"), "balance": amount})
            .execute()
        )
        wallet = inserted[0] if inserted else {"character_id": character_id, "currency_id": cid, "currency": currency.get("ticker") or currency.get("name"), "balance": amount}

    tx_rows = _as_list(
        sb.table("transactions")
        .insert({
            "guild_id": gid,
            "currency_id": cid,
            "from_character_id": None,
            "to_character_id": character_id,
            "amount": amount,
            "tx_type": "MINT",
            "reason": reason,
            "actor_discord_id": staff_id,
        })
        .execute()
    )

    return {"wallet": wallet, "transaction": tx_rows[0] if tx_rows else None, "currency": currency}


@router.post("/staff/resource-grants/grant")
def staff_resource_grant(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = int(actor_discord_id) if actor_discord_id is not None else None
    require_staff(staff_id)

    character_id = str(payload.get("character_id") or "").strip()
    grant_type = str(payload.get("grant_type") or payload.get("resource_type") or "").strip().lower()
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    currency_id = str(payload.get("currency_id") or "").strip() or None

    try:
        amount = int(payload.get("amount") or 0)
    except Exception:
        raise HTTPException(status_code=400, detail="Amount must be a whole number.")

    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC.")
    if grant_type not in {"xp", "currency"}:
        raise HTTPException(status_code=400, detail="Grant type must be xp or currency.")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0.")
    if not reason:
        raise HTTPException(status_code=400, detail="A staff reason is required.")

    sb = get_supabase()
    character = _load_resource_character(sb, character_id)

    if grant_type == "xp":
        result = _grant_xp_to_oc(sb, character, amount, int(staff_id), reason)
        label = "XP granted"
        event_type = "xp_granted"
    else:
        result = _grant_currency_to_oc(sb, character, amount, int(staff_id), reason, currency_id)
        currency = result.get("currency") or {}
        label = f"{currency.get('ticker') or currency.get('name') or 'Currency'} granted"
        event_type = "currency_granted"

    try:
        sb.table("activity_log").insert({
            "guild_id": get_guild_id(),
            "event_type": event_type,
            "label": label,
            "status": "approved",
            "actor_discord_id": int(staff_id),
            "character_id": character_id,
            "character_name": character.get("name"),
            "amount": amount,
            "note": reason,
            "source": "staff_resource_grant",
            "details": {"grant_type": grant_type, "amount": amount, "currency_id": currency_id, "staff_grant": True},
        }).execute()
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"Granted {amount} {'XP' if grant_type == 'xp' else 'currency'} to {character.get('name') or 'OC'}.",
        "character": character,
        "grant_type": grant_type,
        "amount": amount,
        "result": result,
    }

