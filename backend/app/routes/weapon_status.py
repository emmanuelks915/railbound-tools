from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import require_character_access
from app.security import actor_from_header
from app.services import get_guild_id
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/weapon-status", tags=["weapon-status"])

FIREARM_CLASSES = {"firearm", "handgun", "rifle", "shotgun", "gun", "weapon"}


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        result = builder.execute()
        rows = getattr(result, "data", None) or []
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(row: dict[str, Any], item_name: str = "") -> dict[str, Any]:
    shots    = int(row.get("shots_fired") or 0)
    interval = int(row.get("upkeep_interval") or 10)
    needs    = bool(row.get("needs_upkeep") or shots >= interval)
    return {
        "id":               str(row.get("id") or ""),
        "character_id":     str(row.get("character_id") or ""),
        "item_id":          str(row.get("item_id") or ""),
        "item_name":        item_name or str(row.get("item_name") or "Firearm"),
        "rounds_loaded":    int(row.get("rounds_loaded") or 0),
        "capacity":         int(row.get("capacity") or 6),
        "shots_fired":      shots,
        "upkeep_interval":  interval,
        "needs_upkeep":     needs,
        "last_upkeep_at":   str(row.get("last_upkeep_at") or "") or None,
        "notes":            row.get("notes"),
        "updated_at":       str(row.get("updated_at") or ""),
    }


def _item_name_for(sb, item_id: str) -> str:
    try:
        rows = _safe_rows(sb.table("items").select("name").eq("item_id", item_id).limit(1))
        return rows[0].get("name") or "Firearm" if rows else "Firearm"
    except Exception:
        return "Firearm"


# ── GET — all weapon statuses for a character ─────────────────────────────────

@router.get("/{character_id}")
def get_weapon_status(
    character_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    gid = get_guild_id()

    # Get all inventory items for this character that are firearms
    inv_rows = _safe_rows(
        sb.table("inventory_entries")
        .select("item_id,qty")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
    )

    if not inv_rows:
        return {"weapons": []}

    item_ids = [str(r["item_id"]) for r in inv_rows if r.get("item_id")]

    # Filter to firearm item_class only
    firearm_rows = _safe_rows(
        sb.table("items")
        .select("item_id,name,item_class")
        .in_("item_id", item_ids)
        .in_("item_class", list(FIREARM_CLASSES))
    )

    if not firearm_rows:
        return {"weapons": []}

    firearm_ids = {str(r["item_id"]): r.get("name", "Firearm") for r in firearm_rows}

    # Get existing weapon_status rows
    existing = _safe_rows(
        sb.table("weapon_status")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .in_("item_id", list(firearm_ids.keys()))
    )
    existing_by_item = {str(r["item_id"]): r for r in existing}

    # Auto-create missing status rows
    weapons = []
    for item_id, item_name in firearm_ids.items():
        if item_id in existing_by_item:
            weapons.append(_normalize(existing_by_item[item_id], item_name))
        else:
            # Insert a default row
            insert = {
                "guild_id":       gid,
                "character_id":   character_id,
                "item_id":        item_id,
                "rounds_loaded":  0,
                "capacity":       6,
                "shots_fired":    0,
                "upkeep_interval": 10,
                "needs_upkeep":   False,
            }
            new_rows = _safe_rows(sb.table("weapon_status").insert(insert).execute() if False else
                                  sb.table("weapon_status").upsert(insert, on_conflict="guild_id,character_id,item_id"))
            if new_rows:
                weapons.append(_normalize(new_rows[0], item_name))
            else:
                weapons.append(_normalize({**insert, "id": ""}, item_name))

    return {"weapons": weapons}


# ── PATCH — update weapon status ──────────────────────────────────────────────

@router.patch("/{character_id}/{item_id}")
def update_weapon_status(
    character_id: str,
    item_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    gid = get_guild_id()

    existing = _safe_rows(
        sb.table("weapon_status")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .eq("item_id", item_id)
        .limit(1)
    )

    current = existing[0] if existing else {
        "guild_id": gid, "character_id": character_id, "item_id": item_id,
        "rounds_loaded": 0, "capacity": 6, "shots_fired": 0,
        "upkeep_interval": 10, "needs_upkeep": False,
    }

    update: dict[str, Any] = {"updated_at": _now_iso()}

    if "rounds_loaded" in payload:
        update["rounds_loaded"] = max(0, int(payload["rounds_loaded"]))

    if "capacity" in payload:
        update["capacity"] = max(1, int(payload["capacity"]))

    if "shots_fired" in payload:
        shots = max(0, int(payload["shots_fired"]))
        update["shots_fired"] = shots
        interval = int(payload.get("upkeep_interval") or current.get("upkeep_interval") or 10)
        update["needs_upkeep"] = shots >= interval

    if "upkeep_interval" in payload:
        update["upkeep_interval"] = max(1, int(payload["upkeep_interval"]))

    if "notes" in payload:
        update["notes"] = str(payload["notes"]).strip() or None

    # Performing upkeep — reset shot counter
    if payload.get("perform_upkeep"):
        update["shots_fired"] = 0
        update["needs_upkeep"] = False
        update["last_upkeep_at"] = _now_iso()

    if existing:
        rows = _safe_rows(
            sb.table("weapon_status")
            .update(update)
            .eq("guild_id", gid)
            .eq("character_id", character_id)
            .eq("item_id", item_id)
        )
        row = rows[0] if rows else {**current, **update}
    else:
        rows = _safe_rows(
            sb.table("weapon_status")
            .upsert({**current, **update}, on_conflict="guild_id,character_id,item_id")
        )
        row = rows[0] if rows else {**current, **update}

    item_name = _item_name_for(sb, item_id)
    return {"weapon": _normalize(row, item_name), "message": "Weapon status updated."}
