from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.models import ActiveLoadoutRequest, LoadoutSaveRequest
from app.permissions import require_character_access
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["inventory"])


@router.get("/items")
def list_item_catalog(active_only: bool = True, actor_discord_id: int | None = Depends(actor_from_header)):
    # Any signed-in user can browse the item catalog; staff-only edit is handled elsewhere.
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Discord-Id header.")
    sb = get_supabase()
    q = sb.table("items").select("*").eq("guild_id", get_guild_id()).order("name", desc=False).limit(500)
    if active_only:
        q = q.eq("is_active", True)
    return {"items": sb_data(q.execute()) or []}


@router.get("/characters/{character_id}/inventory")
def character_inventory(character_id: UUID, actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    gid = get_guild_id()

    entries_res = (
        sb.table("inventory_entries")
        .select("item_id,qty,updated_at")
        .eq("guild_id", gid)
        .eq("character_id", str(character_id))
        .order("updated_at", desc=True)
        .limit(500)
        .execute()
    )
    entries = sb_data(entries_res) or []
    item_ids = [str(e["item_id"]) for e in entries if e.get("item_id")]

    items_by_id = {}
    if item_ids:
        item_res = (
            sb.table("items")
            .select("item_id,name,item_class,wu,sheet_url,notes,is_active")
            .eq("guild_id", gid)
            .in_("item_id", item_ids)
            .execute()
        )
        for row in sb_data(item_res) or []:
            items_by_id[str(row["item_id"])] = row

    out = []
    for entry in entries:
        iid = str(entry.get("item_id") or "")
        out.append({**entry, "item": items_by_id.get(iid)})

    return {"entries": out}


@router.get("/characters/{character_id}/loadouts")
def list_loadouts(character_id: UUID, actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    gid = get_guild_id()

    char_res = (
        sb.table("characters")
        .select("active_loadout_name")
        .eq("character_id", str(character_id))
        .limit(1)
        .execute()
    )
    char_rows = sb_data(char_res) or []
    active = char_rows[0].get("active_loadout_name") if char_rows else None

    res = (
        sb.table("inventory_loadouts")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", str(character_id))
        .order("updated_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"active_loadout_name": active, "loadouts": sb_data(res) or []}


@router.post("/characters/{character_id}/loadouts")
def save_loadout(character_id: UUID, payload: LoadoutSaveRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    gid = get_guild_id()

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Loadout name is required.")

    items_map = payload.items
    if items_map is None:
        inv = (
            sb.table("inventory_entries")
            .select("item_id,qty")
            .eq("guild_id", gid)
            .eq("character_id", str(character_id))
            .execute()
        )
        entries = sb_data(inv) or []
        items_map = {str(e["item_id"]): int(e.get("qty") or 0) for e in entries if int(e.get("qty") or 0) > 0}
    else:
        items_map = {str(k): int(v) for k, v in items_map.items() if int(v) > 0}

    existing = (
        sb.table("inventory_loadouts")
        .select("loadout_name")
        .eq("guild_id", gid)
        .eq("character_id", str(character_id))
        .eq("loadout_name", name)
        .limit(1)
        .execute()
    )
    if sb_data(existing):
        sb.table("inventory_loadouts").update({"items": items_map}).eq("guild_id", gid).eq("character_id", str(character_id)).eq("loadout_name", name).execute()
    else:
        sb.table("inventory_loadouts").insert({"guild_id": gid, "character_id": str(character_id), "loadout_name": name, "items": items_map}).execute()

    return {"ok": True, "loadout_name": name, "item_count": len(items_map)}


@router.patch("/characters/{character_id}/active-loadout")
def set_active_loadout(character_id: UUID, payload: ActiveLoadoutRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    name = payload.name.strip() if payload.name else None
    sb.table("characters").update({"active_loadout_name": name}).eq("character_id", str(character_id)).execute()
    return {"ok": True, "active_loadout_name": name}
