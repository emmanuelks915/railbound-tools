from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

try:
    from app.utils.activity_logger import log_activity
except Exception:
    def log_activity(**kwargs):
        return None

router = APIRouter(prefix="/api/loadouts", tags=["loadouts"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _require_login(actor: int | None) -> int:
    if actor is None:
        raise HTTPException(status_code=401, detail="Login required.")
    return int(actor)


def _can_access(actor: int, character_id: str) -> bool:
    """Player can access own character; staff can access any."""
    if is_staff(actor):
        return True
    sb = get_supabase()
    rows = _safe_rows(
        sb.table("characters")
        .select("character_id,user_id,discord_id,owner_discord_id,player_discord_id")
        .eq("character_id", character_id)
        .limit(1)
    )
    if not rows:
        return False
    char = rows[0]
    owner = str(
        char.get("user_id") or char.get("discord_id") or
        char.get("owner_discord_id") or char.get("player_discord_id") or ""
    )
    return owner == str(actor)


def _get_core_stats(sb, character_id: str) -> dict[str, int]:
    keys = ["strength", "dexterity", "stamina", "magic_affinity", "mana"]
    rows = _safe_rows(
        sb.table("oc_stats")
        .select("stat_key,stat_value")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(100)
    )
    stats = {k: 0 for k in keys}
    for row in rows:
        k = str(row.get("stat_key") or "")
        if k in stats:
            try:
                stats[k] = int(row.get("stat_value") or 0)
            except Exception:
                pass
    return stats


def _base_cc(strength: int) -> int:
    """CC = 4 + floor(STR / 150)"""
    return 4 + math.floor(strength / 150)


def _get_items_meta(sb, item_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch wu, name, item_class, special_effects for a list of items table UUIDs."""
    if not item_ids:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for iid in item_ids:
        rows = _safe_rows(
            sb.table("items")
            .select("item_id,name,item_class,wu")
            .eq("item_id", iid)
            .limit(1)
        )
        if rows:
            lookup[iid] = rows[0]
    return lookup


def _parse_loadout_items(raw: Any) -> dict[str, dict[str, Any]]:
    """
    Parse items JSONB into normalized format.
    Supports both old format {item_id: qty} and new format {item_id: {qty, worn}}.
    Returns {item_id: {qty: int, worn: bool}}
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item_id, val in raw.items():
        if isinstance(val, dict):
            out[item_id] = {
                "qty": int(val.get("qty") or val.get("quantity") or 1),
                "worn": bool(val.get("worn", False)),
            }
        else:
            # Old format: just a number
            try:
                qty = int(val)
            except Exception:
                qty = 1
            out[item_id] = {"qty": qty, "worn": False}
    return out


def _cc_breakdown(sb, loadout_items: dict[str, dict[str, Any]], base_cc: int) -> dict[str, Any]:
    """
    Calculate CC breakdown for a loadout.
    WORN items: WU ignored for CC usage, but any carry_capacity_bonus in effects applies
    CARRIED items: WU × qty counts against CC
    Returns full breakdown dict.
    """
    # Get grants_item_ids for shop items (loadout stores grants_item_ids already)
    item_ids = list(loadout_items.keys())
    meta = _get_items_meta(sb, item_ids)

    cc_bonus = 0
    cc_used = 0
    worn_items: list[dict[str, Any]] = []
    carried_items: list[dict[str, Any]] = []

    for item_id, entry in loadout_items.items():
        qty = entry["qty"]
        worn = entry["worn"]
        m = meta.get(item_id, {})
        wu = int(m.get("wu") or 0)
        name = m.get("name") or "Unknown Item"
        item_class = m.get("item_class") or "misc"

        item_entry = {
            "item_id": item_id,
            "name": name,
            "item_class": item_class,
            "cc": wu,
            "qty": qty,
            "worn": worn,
            "cc_cost": 0 if worn else wu * qty,
        }

        if worn:
            # Worn items don't use CC — but check for CC bonus (backpacks etc.)
            # For now bonus comes from item description/effects — we store on shop_items
            # Look up the shop item to get cc_bonus
            shop_rows = _safe_rows(
                sb.table("shop_items")
                .select("item_id,special_effects,stat_limits")
                .eq("grants_item_id", item_id)
                .eq("guild_id", get_guild_id())
                .limit(1)
            )
            if shop_rows:
                effects = str(shop_rows[0].get("special_effects") or "")
                # Parse "+N CC" or "carry_capacity_bonus: N" from effects text
                import re
                cc_match = re.search(r'\+\s*(\d+)\s*CC', effects, re.IGNORECASE)
                if cc_match:
                    cc_bonus += int(cc_match.group(1)) * qty
            worn_items.append(item_entry)
        else:
            cc_used += wu * qty
            carried_items.append(item_entry)

    total_cc = base_cc + cc_bonus

    return {
        "base_cc": base_cc,
        "cc_bonus": cc_bonus,
        "total_cc": total_cc,
        "cc_used": cc_used,
        "cc_remaining": total_cc - cc_used,
        "over_capacity": cc_used > total_cc,
        "worn_items": worn_items,
        "carried_items": carried_items,
    }


def _normalize_loadout(row: dict[str, Any], sb=None, base_cc: int = 4) -> dict[str, Any]:
    items = _parse_loadout_items(row.get("items") or {})
    breakdown = _cc_breakdown(sb, items, base_cc) if sb else None
    return {
        "loadout_name": row.get("loadout_name") or "",
        "character_id": str(row.get("character_id") or ""),
        "items": items,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "cc": breakdown,
    }


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("/{character_id}")
def list_loadouts(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    sb = get_supabase()
    rows = _safe_rows(
        sb.table("inventory_loadouts")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .order("updated_at", desc=True)
        .limit(50)
    )

    # Get character's strength for CC
    stats = _get_core_stats(sb, character_id)
    base = _base_cc(stats.get("strength", 0))

    # Get active loadout name
    char_rows = _safe_rows(
        sb.table("characters")
        .select("active_loadout_name")
        .eq("character_id", character_id)
        .limit(1)
    )
    active_name = str(char_rows[0].get("active_loadout_name") or "") if char_rows else ""

    loadouts = []
    for row in rows:
        lo = _normalize_loadout(row, sb, base)
        lo["is_active"] = lo["loadout_name"] == active_name
        loadouts.append(lo)

    return {
        "loadouts": loadouts,
        "active_loadout_name": active_name,
        "base_cc": base,
        "strength": stats.get("strength", 0),
    }


@router.get("/{character_id}/{loadout_name}")
def get_loadout(
    character_id: str,
    loadout_name: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    sb = get_supabase()
    rows = _safe_rows(
        sb.table("inventory_loadouts")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .eq("loadout_name", loadout_name)
        .limit(1)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Loadout not found.")

    stats = _get_core_stats(sb, character_id)
    base = _base_cc(stats.get("strength", 0))
    lo = _normalize_loadout(rows[0], sb, base)

    char_rows = _safe_rows(
        sb.table("characters").select("active_loadout_name").eq("character_id", character_id).limit(1)
    )
    active_name = str(char_rows[0].get("active_loadout_name") or "") if char_rows else ""
    lo["is_active"] = lo["loadout_name"] == active_name

    # Also return full inventory so frontend can show what's available to add
    inv_rows = _safe_rows(
        sb.table("inventory_entries")
        .select("item_id,qty")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(500)
    )
    inventory: list[dict[str, Any]] = []
    for entry in inv_rows:
        iid = str(entry.get("item_id") or "")
        if not iid:
            continue
        meta_rows = _safe_rows(sb.table("items").select("name,item_class,wu").eq("item_id", iid).limit(1))
        meta = meta_rows[0] if meta_rows else {}
        inventory.append({
            "item_id": iid,
            "name": meta.get("name") or "Unknown Item",
            "item_class": meta.get("item_class") or "misc",
            "cc": int(meta.get("wu") or 0),
            "qty_owned": int(entry.get("qty") or 0),
        })

    return {**lo, "inventory": inventory, "base_cc": base, "strength": stats.get("strength", 0)}


@router.post("/{character_id}")
def create_loadout(
    character_id: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    name = str(payload.get("loadout_name") or payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Loadout name is required.")

    sb = get_supabase()

    # Check if name already exists
    existing = _safe_rows(
        sb.table("inventory_loadouts")
        .select("loadout_name")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .eq("loadout_name", name)
        .limit(1)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f'Loadout "{name}" already exists.')

    items_raw = payload.get("items") or {}
    items = _parse_loadout_items(items_raw)

    rows = _as_list(
        sb.table("inventory_loadouts").insert({
            "guild_id": get_guild_id(),
            "character_id": character_id,
            "loadout_name": name,
            "items": items,
        }).execute()
    )

    stats = _get_core_stats(sb, character_id)
    base = _base_cc(stats.get("strength", 0))
    lo = _normalize_loadout(rows[0] if rows else {"character_id": character_id, "loadout_name": name, "items": items}, sb, base)

    return {"loadout": lo, "message": f'Loadout "{name}" created.'}


@router.patch("/{character_id}/{loadout_name}")
def update_loadout(
    character_id: str,
    loadout_name: str,
    payload: dict[str, Any] = Body(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    sb = get_supabase()
    existing = _safe_rows(
        sb.table("inventory_loadouts")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .eq("loadout_name", loadout_name)
        .limit(1)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Loadout not found.")

    current_items = _parse_loadout_items(existing[0].get("items") or {})

    # Merge incoming changes
    changes = payload.get("items") or {}
    for item_id, entry in changes.items():
        if entry is None:
            # Remove item
            current_items.pop(item_id, None)
        elif isinstance(entry, dict):
            qty = int(entry.get("qty") or 0)
            if qty <= 0:
                current_items.pop(item_id, None)
            else:
                current_items[item_id] = {
                    "qty": qty,
                    "worn": bool(entry.get("worn", False)),
                }

    rows = _as_list(
        sb.table("inventory_loadouts")
        .update({"items": current_items})
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .eq("loadout_name", loadout_name)
        .execute()
    )

    stats = _get_core_stats(sb, character_id)
    base = _base_cc(stats.get("strength", 0))
    updated = rows[0] if rows else {**existing[0], "items": current_items}
    lo = _normalize_loadout(updated, sb, base)

    return {"loadout": lo, "message": "Loadout updated."}


@router.delete("/{character_id}/{loadout_name}")
def delete_loadout(
    character_id: str,
    loadout_name: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    sb = get_supabase()
    _safe_rows(
        sb.table("inventory_loadouts")
        .delete()
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .eq("loadout_name", loadout_name)
        .execute()
    )

    # Unset active if this was it
    char_rows = _safe_rows(
        sb.table("characters").select("active_loadout_name").eq("character_id", character_id).limit(1)
    )
    if char_rows and str(char_rows[0].get("active_loadout_name") or "") == loadout_name:
        try:
            sb.table("characters").update({"active_loadout_name": None}).eq("character_id", character_id).execute()
        except Exception:
            pass

    return {"ok": True, "message": f'Loadout "{loadout_name}" deleted.'}


@router.post("/{character_id}/{loadout_name}/activate")
def activate_loadout(
    character_id: str,
    loadout_name: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    sb = get_supabase()
    existing = _safe_rows(
        sb.table("inventory_loadouts")
        .select("loadout_name")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .eq("loadout_name", loadout_name)
        .limit(1)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Loadout not found.")

    try:
        sb.table("characters").update({"active_loadout_name": loadout_name}).eq("character_id", character_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not activate loadout: {exc}")

    return {"ok": True, "message": f'"{loadout_name}" is now your active loadout.'}


@router.post("/{character_id}/deactivate")
def deactivate_loadout(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not _can_access(actor, character_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    sb = get_supabase()
    try:
        sb.table("characters").update({"active_loadout_name": None}).eq("character_id", character_id).execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not deactivate: {exc}")

    return {"ok": True, "message": "Active loadout cleared."}
