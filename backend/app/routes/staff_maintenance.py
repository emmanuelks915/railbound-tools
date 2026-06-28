
from __future__ import annotations
import re, uuid
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/staff/maintenance", tags=["staff-maintenance"])

def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []

def _safe_rows(builder) -> list[dict[str, Any]]:
    try: return _as_list(builder.execute())
    except Exception: return []

def _staff(actor_discord_id: int | None) -> int:
    staff_id = int(actor_discord_id) if actor_discord_id is not None else None
    require_staff(staff_id)
    return int(staff_id)

def _slugify(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return cleaned if cleaned.startswith(prefix + "_") else f"{prefix}_{cleaned or uuid.uuid4().hex[:8]}"

def _character(sb, character_id: str) -> dict[str, Any]:
    rows = _as_list(sb.table("characters").select("character_id,name,user_id,guild_id,is_active").eq("guild_id", get_guild_id()).eq("character_id", character_id).limit(1).execute())
    if not rows: raise HTTPException(status_code=404, detail="Character not found.")
    return rows[0]

def _log(sb, event_type: str, label: str, staff_id: int, character: dict[str, Any], note: str, details: dict[str, Any]) -> None:
    try:
        sb.table("activity_log").insert({"guild_id": get_guild_id(), "event_type": event_type, "label": label, "status": "approved", "actor_discord_id": staff_id, "character_id": character.get("character_id"), "character_name": character.get("name"), "note": note, "source": "staff_maintenance", "details": details}).execute()
    except Exception: pass

@router.get("/options")
def maintenance_options(actor_discord_id: int | None = Depends(actor_from_header)):
    _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    characters = _as_list(sb.table("characters").select("character_id,name,user_id,is_active").eq("guild_id", gid).eq("is_active", True).order("name", desc=False).limit(1000).execute())
    skills = _safe_rows(sb.table("skill_definitions").select("skill_key,name,tree,tier,cost,is_active").eq("guild_id", gid).order("tree", desc=False).order("tier", desc=False).order("name", desc=False).limit(2500))
    traits = _safe_rows(sb.table("traits").select("trait_id,slug,name,tier,cost,category,is_active").eq("guild_id", gid).order("tier", desc=False).order("name", desc=False).limit(2500))
    return {"characters": characters, "skills": skills, "traits": traits}

@router.post("/xp/remove")
def remove_xp(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    character_id = str(payload.get("character_id") or "").strip()
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    try: amount = int(payload.get("amount") or 0)
    except Exception: raise HTTPException(status_code=400, detail="Amount must be a whole number.")
    if not character_id: raise HTTPException(status_code=400, detail="Choose an OC.")
    if amount <= 0: raise HTTPException(status_code=400, detail="Amount must be greater than 0.")
    if not reason: raise HTTPException(status_code=400, detail="A staff reason is required.")
    character = _character(sb, character_id)
    rows = _as_list(sb.table("oc_xp_wallets").select("*").eq("guild_id", gid).eq("character_id", character_id).limit(1).execute())
    if not rows: raise HTTPException(status_code=400, detail="OC does not have an XP wallet yet.")
    wallet = rows[0]; available = int(wallet.get("available_xp") or 0); earned = int(wallet.get("total_earned_xp") or 0)
    if available < amount: raise HTTPException(status_code=400, detail=f"Cannot remove {amount} XP. OC only has {available} available XP.")
    new_available, new_earned = available - amount, max(0, earned - amount)
    updated = _as_list(sb.table("oc_xp_wallets").update({"available_xp": new_available, "total_earned_xp": new_earned}).eq("guild_id", gid).eq("character_id", character_id).execute())
    try: sb.table("oc_xp_transactions").insert({"guild_id": gid, "character_id": character_id, "direction": "spend", "amount": amount, "source": "staff_correction", "reference_type": None, "reference_key": "staff_xp_removal", "reason": reason, "actor_discord_id": staff_id, "metadata": {"correction_type": "remove_xp"}}).execute()
    except Exception: pass
    _log(sb, "xp_removed", "XP removed", staff_id, character, reason, {"amount": amount, "old_available_xp": available, "new_available_xp": new_available})
    return {"ok": True, "message": f"Removed {amount} XP from {character.get('name') or 'OC'}.", "wallet": updated[0] if updated else None}



def _maintenance_currency(sb, currency_id: str | None) -> dict[str, Any]:
    gid = get_guild_id()
    rows: list[dict[str, Any]] = []

    if currency_id:
        rows = _as_list(
            sb.table("currencies")
            .select("*")
            .eq("guild_id", gid)
            .eq("currency_id", currency_id)
            .limit(1)
            .execute()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Currency not found.")
    else:
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


@router.post("/currency/remove")
def remove_currency(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id)
    sb = get_supabase()

    character_id = str(payload.get("character_id") or "").strip()
    currency_id = str(payload.get("currency_id") or "").strip() or None
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()

    try:
        amount = int(payload.get("amount") or 0)
    except Exception:
        raise HTTPException(status_code=400, detail="Amount must be a whole number.")

    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC.")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0.")
    if not reason:
        raise HTTPException(status_code=400, detail="A staff reason is required.")

    character = _character(sb, character_id)
    currency = _maintenance_currency(sb, currency_id)

    cid = str(currency.get("currency_id") or currency.get("id") or "")
    ticker = currency.get("ticker") or currency.get("name") or "currency"

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

    if not wallet_rows:
        raise HTTPException(status_code=400, detail=f"OC does not have a {ticker} wallet yet.")

    wallet = wallet_rows[0]
    old_balance = int(wallet.get("balance") or 0)

    if old_balance < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot remove {amount} {ticker}. OC only has {old_balance}.",
        )

    new_balance = old_balance - amount

    updated = _as_list(
        sb.table("wallets")
        .update({"balance": new_balance})
        .eq("character_id", character_id)
        .eq("currency_id", cid)
        .execute()
    )

    tx_rows = []
    tx_payload = {
        "guild_id": get_guild_id(),
        "currency_id": cid,
        "from_character_id": character_id,
        "to_character_id": None,
        "amount": amount,
        "reason": reason,
        "actor_discord_id": staff_id,
    }

    for tx_type in ("BURN", "WITHDRAW", "ADJUSTMENT", "STAFF_REMOVE"):
        try:
            tx_rows = _as_list(
                sb.table("transactions")
                .insert({**tx_payload, "tx_type": tx_type})
                .execute()
            )
            break
        except Exception:
            tx_rows = []

    _log(
        sb,
        "currency_removed",
        f"{ticker} removed",
        staff_id,
        character,
        reason,
        {
            "amount": amount,
            "currency_id": cid,
            "currency": ticker,
            "old_balance": old_balance,
            "new_balance": new_balance,
        },
    )

    return {
        "ok": True,
        "message": f"Removed {amount} {ticker} from {character.get('name') or 'OC'}.",
        "character": character,
        "currency": currency,
        "wallet": updated[0] if updated else {**wallet, "balance": new_balance},
        "transaction": tx_rows[0] if tx_rows else None,
    }


@router.post("/skill/remove")
def remove_skill(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    character_id = str(payload.get("character_id") or "").strip(); skill_key = str(payload.get("skill_key") or "").strip()
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    if not character_id: raise HTTPException(status_code=400, detail="Choose an OC.")
    if not skill_key: raise HTTPException(status_code=400, detail="Choose a skill to remove.")
    if not reason: raise HTTPException(status_code=400, detail="A staff reason is required.")
    character = _character(sb, character_id)
    existing = _as_list(sb.table("oc_skills").select("*").eq("guild_id", gid).eq("character_id", character_id).eq("skill_key", skill_key).limit(1).execute())
    if not existing: raise HTTPException(status_code=404, detail="This OC does not currently own that skill.")
    sb.table("oc_skills").delete().eq("guild_id", gid).eq("character_id", character_id).eq("skill_key", skill_key).execute()
    _log(sb, "skill_removed", "Skill removed", staff_id, character, reason, {"skill_key": skill_key, "removed_row": existing[0]})
    return {"ok": True, "message": f"Removed {skill_key} from {character.get('name') or 'OC'}."}

@router.post("/trait/remove")
def remove_trait(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    character_id = str(payload.get("character_id") or "").strip(); slug = str(payload.get("trait_slug") or payload.get("slug") or "").strip()
    trait_id = str(payload.get("trait_id") or "").strip(); reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    if not character_id: raise HTTPException(status_code=400, detail="Choose an OC.")
    if not slug and not trait_id: raise HTTPException(status_code=400, detail="Choose a trait to remove.")
    if not reason: raise HTTPException(status_code=400, detail="A staff reason is required.")
    character = _character(sb, character_id)
    if not trait_id:
        rows = _as_list(sb.table("traits").select("trait_id,slug,name").eq("guild_id", gid).eq("slug", slug).limit(1).execute())
        if not rows: raise HTTPException(status_code=404, detail="Trait not found.")
        trait_id = str(rows[0].get("trait_id"))
    removed = False
    for table in ("character_traits", "oc_traits"):
        try:
            sb.table(table).delete().eq("guild_id", gid).eq("character_id", character_id).eq("trait_id", trait_id).execute()
            removed = True
        except Exception: continue
    if not removed: raise HTTPException(status_code=500, detail="Could not remove trait from known trait tables.")
    _log(sb, "trait_removed", "Trait removed", staff_id, character, reason, {"trait_id": trait_id, "trait_slug": slug})
    return {"ok": True, "message": f"Removed trait from {character.get('name') or 'OC'}."}

def _ensure_skill(sb, skill_key: str, name: str, tree: str, tier: int, cost: int, description: str) -> dict[str, Any]:
    gid = get_guild_id()
    rows = _safe_rows(sb.table("skill_definitions").select("*").eq("guild_id", gid).eq("skill_key", skill_key).limit(1))
    if rows: return rows[0]
    payloads = [
        {"skill_id": str(uuid.uuid4()), "guild_id": gid, "skill_key": skill_key, "name": name, "tree": tree, "tier": tier, "cost": cost, "description": description, "prerequisites": {"raw": "Staff custom / hidden skill", "skills": []}, "is_active": False, "sort_order": 9999},
        {"skill_id": str(uuid.uuid4()), "guild_id": gid, "skill_key": skill_key, "name": name, "tree": tree, "tier": tier, "cost": cost, "prerequisites": {"raw": "Staff custom / hidden skill", "skills": []}, "is_active": False},
        {"skill_id": str(uuid.uuid4()), "guild_id": gid, "skill_key": skill_key, "name": name, "tree": tree, "tier": tier, "cost": cost, "is_active": False},
    ]
    last = None
    for payload in payloads:
        try:
            out = _as_list(sb.table("skill_definitions").insert(payload).execute())
            return out[0] if out else payload
        except Exception as exc: last = exc
    raise HTTPException(status_code=500, detail=f"Could not create custom skill definition: {last}")

@router.post("/custom-skill/grant")
def grant_custom_skill(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    character_id = str(payload.get("character_id") or "").strip(); name = str(payload.get("name") or "").strip()
    skill_key = str(payload.get("skill_key") or "").strip() or _slugify(name, "custom_skill")
    tree = str(payload.get("tree") or "Staff Custom").strip(); description = str(payload.get("description") or "").strip()
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    try: tier, cost = int(payload.get("tier") or 0), int(payload.get("cost") or 0)
    except Exception: raise HTTPException(status_code=400, detail="Tier and cost must be whole numbers.")
    if not character_id: raise HTTPException(status_code=400, detail="Choose an OC.")
    if not name: raise HTTPException(status_code=400, detail="Custom skill name is required.")
    if not reason: raise HTTPException(status_code=400, detail="A staff reason is required.")
    character = _character(sb, character_id); skill = _ensure_skill(sb, skill_key, name, tree, tier, cost, description)
    existing = _safe_rows(sb.table("oc_skills").select("skill_key").eq("guild_id", gid).eq("character_id", character_id).eq("skill_key", skill_key).limit(1))
    if not existing:
        sb.table("oc_skills").insert({"guild_id": gid, "character_id": character_id, "skill_key": skill_key, "acquired_via": "xp", "xp_cost_paid": 0, "xp_tx_id": None, "actor_discord_id": staff_id, "notes": reason}).execute()
    _log(sb, "custom_skill_granted", "Custom skill granted", staff_id, character, reason, {"skill_key": skill_key, "name": name, "hidden_from_portal": True})
    return {"ok": True, "message": f"Granted custom skill {name} to {character.get('name') or 'OC'}.", "skill": skill}

def _ensure_trait(sb, slug: str, name: str, tier: str, cost: int, category: str, description: str) -> dict[str, Any]:
    gid = get_guild_id()
    rows = _safe_rows(sb.table("traits").select("*").eq("guild_id", gid).eq("slug", slug).limit(1))
    if rows: return rows[0]
    payloads = [
        {"trait_id": str(uuid.uuid4()), "guild_id": gid, "name": name, "slug": slug, "tier": tier, "cost": cost, "category": category, "description": description, "effects_json": {"staff_custom": True}, "requirements_json": {}, "is_active": False},
        {"trait_id": str(uuid.uuid4()), "guild_id": gid, "name": name, "slug": slug, "tier": tier, "cost": cost, "category": category, "effects_json": {}, "requirements_json": {}, "is_active": False},
    ]
    last = None
    for payload in payloads:
        try:
            out = _as_list(sb.table("traits").insert(payload).execute())
            return out[0] if out else payload
        except Exception as exc: last = exc
    raise HTTPException(status_code=500, detail=f"Could not create custom trait definition: {last}")

@router.post("/custom-trait/grant")
def grant_custom_trait(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    character_id = str(payload.get("character_id") or "").strip(); name = str(payload.get("name") or "").strip()
    slug = str(payload.get("slug") or "").strip() or _slugify(name, "custom_trait")
    tier = str(payload.get("tier") or "reliable").strip().lower(); category = str(payload.get("category") or "custom").strip().lower()
    description = str(payload.get("description") or "").strip(); reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    try: cost = int(payload.get("cost") or 0)
    except Exception: raise HTTPException(status_code=400, detail="Cost must be a whole number.")
    if tier not in {"origin", "minor", "reliable", "keystone", "negative"}: tier = "reliable"
    if not character_id: raise HTTPException(status_code=400, detail="Choose an OC.")
    if not name: raise HTTPException(status_code=400, detail="Custom trait name is required.")
    if not reason: raise HTTPException(status_code=400, detail="A staff reason is required.")
    character = _character(sb, character_id); trait = _ensure_trait(sb, slug, name, tier, cost, category, description)
    trait_id = str(trait.get("trait_id") or "")
    if not trait_id: raise HTTPException(status_code=500, detail="Trait definition did not return trait_id.")
    assignment = {"guild_id": gid, "character_id": character_id, "trait_id": trait_id, "approved_by": staff_id, "notes": reason}
    attached = False
    for table in ("character_traits", "oc_traits"):
        try:
            sb.table(table).upsert(assignment).execute()
            attached = True
            break
        except Exception: continue
    if not attached: raise HTTPException(status_code=500, detail="Could not attach trait to known trait tables.")
    _log(sb, "custom_trait_granted", "Custom trait granted", staff_id, character, reason, {"trait_id": trait_id, "slug": slug, "name": name, "hidden_from_portal": True})
    return {"ok": True, "message": f"Granted custom trait {name} to {character.get('name') or 'OC'}.", "trait": trait}

@router.post("/item/remove")
def remove_item(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id); sb = get_supabase(); gid = get_guild_id()
    character_id = str(payload.get("character_id") or "").strip()
    inventory_id = str(payload.get("inventory_id") or "").strip()
    item_id = str(payload.get("item_id") or "").strip()
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()
    if not character_id: raise HTTPException(status_code=400, detail="Choose an OC.")
    if not inventory_id and not item_id: raise HTTPException(status_code=400, detail="Item reference is required.")
    if not reason: raise HTTPException(status_code=400, detail="A staff reason is required.")
    character = _character(sb, character_id)
    removed = False
    removed_row: dict[str, Any] = {}
    # Try inventory_id first (the inventory_entries row pk)
    if inventory_id:
        for id_col in ("inventory_id", "id"):
            try:
                existing = _as_list(sb.table("inventory_entries").select("*").eq("guild_id", gid).eq("character_id", character_id).eq(id_col, inventory_id).limit(1).execute())
                if existing:
                    removed_row = existing[0]
                    sb.table("inventory_entries").delete().eq("guild_id", gid).eq("character_id", character_id).eq(id_col, inventory_id).execute()
                    removed = True
                    break
            except Exception:
                continue
    # Fallback: remove by item_id (removes one matching row)
    if not removed and item_id:
        try:
            existing = _as_list(sb.table("inventory_entries").select("*").eq("guild_id", gid).eq("character_id", character_id).eq("item_id", item_id).limit(1).execute())
            if existing:
                removed_row = existing[0]
                row_pk = str(existing[0].get("inventory_id") or existing[0].get("id") or "")
                if row_pk:
                    sb.table("inventory_entries").delete().eq("guild_id", gid).eq("character_id", character_id).eq("inventory_id", row_pk).execute()
                    removed = True
        except Exception:
            pass
    if not removed:
        raise HTTPException(status_code=404, detail="Item not found in this OC's inventory.")
    _log(sb, "item_removed", "Item removed by staff", staff_id, character, reason, {"inventory_id": inventory_id, "item_id": item_id, "removed_row": removed_row})
    return {"ok": True, "message": f"Removed item from {character.get('name') or 'OC'}."}
