from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/me")
def me(actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Discord-Id header.")
    sb = get_supabase()
    gid = get_guild_id()
    staff = is_staff(actor_discord_id)

    chars_q = sb.table("characters").select("character_id,name,user_id,active_loadout_name").order("name", desc=False).limit(500)
    if not staff:
        chars_q = chars_q.eq("user_id", str(actor_discord_id))
    characters = sb_data(chars_q.execute()) or []

    if staff:
        shops = sb_data(sb.table("companies").select("company_id,name,shop_status").eq("guild_id", gid).order("name", desc=False).limit(500).execute()) or []
    else:
        memberships = sb_data(sb.table("company_members").select("company_id,role").eq("discord_id", int(actor_discord_id)).execute()) or []
        company_ids = [str(m["company_id"]) for m in memberships]
        shops = []
        if company_ids:
            shops = sb_data(sb.table("companies").select("company_id,name,shop_status").eq("guild_id", gid).in_("company_id", company_ids).order("name", desc=False).execute()) or []

    pending_stats_q = sb.table("stat_upgrade_requests").select("request_id,character_id,total_cost,status,created_at").eq("guild_id", gid).eq("status", "pending").order("created_at", desc=True).limit(100)
    pending_skills_q = sb.table("skill_purchase_requests").select("request_id,character_id,skill_key,cost,status,created_at").eq("guild_id", gid).eq("status", "pending").order("created_at", desc=True).limit(100)
    if not staff:
        pending_stats_q = pending_stats_q.eq("requested_by_discord_id", int(actor_discord_id))
        pending_skills_q = pending_skills_q.eq("requested_by_discord_id", int(actor_discord_id))

    return {
        "actor_discord_id": actor_discord_id,
        "is_staff": staff,
        "characters": characters,
        "shops": shops,
        "pending_stat_requests": sb_data(pending_stats_q.execute()) or [],
        "pending_skill_requests": sb_data(pending_skills_q.execute()) or [],
    }
