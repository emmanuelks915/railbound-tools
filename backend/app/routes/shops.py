from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models import ShopItemPatchRequest, ShopPatchRequest
from app.permissions import company_member_rank, is_staff, require_actor, require_company_manager
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/shops", tags=["shops"])


def _shop_select() -> str:
    return "company_id,guild_id,name,owner_character_id,shop_description,shop_banner_url,shop_logo_url,shop_status,shop_category_id,shop_forum_channel_id,shop_storefront_thread_id"


@router.get("/mine")
def my_shops(actor_discord_id: int | None = Depends(actor_from_header)):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    if is_staff(actor):
        res = sb.table("companies").select(_shop_select()).eq("guild_id", gid).order("name", desc=False).limit(500).execute()
        return {"shops": sb_data(res) or [], "staff_view": True}

    memberships = (
        sb.table("company_members")
        .select("company_id,role")
        .eq("discord_id", actor)
        .execute()
    )
    member_rows = sb_data(memberships) or []
    company_ids = [str(r["company_id"]) for r in member_rows if company_member_rank(sb, str(r["company_id"]), actor) >= 1]
    if not company_ids:
        return {"shops": [], "staff_view": False}

    shops = sb.table("companies").select(_shop_select()).eq("guild_id", gid).in_("company_id", company_ids).order("name", desc=False).execute()
    role_by_company = {str(r["company_id"]): str(r.get("role") or "MEMBER") for r in member_rows}
    out = []
    for shop in sb_data(shops) or []:
        out.append({**shop, "member_role": role_by_company.get(str(shop["company_id"]))})
    return {"shops": out, "staff_view": False}


@router.get("/{company_id}")
def shop_detail(company_id: str, actor_discord_id: int | None = Depends(actor_from_header)):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    if not is_staff(actor) and company_member_rank(sb, company_id, actor) < 1:
        raise HTTPException(status_code=403, detail="You can only view shops you belong to.")

    shop_res = sb.table("companies").select("*").eq("guild_id", get_guild_id()).eq("company_id", str(company_id)).limit(1).execute()
    rows = sb_data(shop_res) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Shop not found.")
    return {"shop": rows[0]}


@router.patch("/{company_id}")
def update_shop(company_id: str, payload: ShopPatchRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    require_company_manager(sb, company_id, actor_discord_id, min_rank=2)

    patch = {}
    if payload.name is not None:
        patch["name"] = payload.name.strip()
    if payload.description is not None:
        patch["shop_description"] = payload.description.strip() or None
    if payload.banner_url is not None:
        patch["shop_banner_url"] = payload.banner_url.strip() or None
    if payload.logo_url is not None:
        patch["shop_logo_url"] = payload.logo_url.strip() or None

    if not patch:
        raise HTTPException(status_code=400, detail="No shop changes provided.")

    sb.table("companies").update(patch).eq("guild_id", get_guild_id()).eq("company_id", str(company_id)).execute()
    return {"ok": True, "updated_fields": sorted(patch.keys())}


@router.get("/{company_id}/items")
def shop_items(company_id: str, actor_discord_id: int | None = Depends(actor_from_header)):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    if not is_staff(actor) and company_member_rank(sb, company_id, actor) < 1:
        raise HTTPException(status_code=403, detail="You can only view shops you belong to.")

    res = (
        sb.table("shop_items")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("vendor_company_id", str(company_id))
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    return {"items": sb_data(res) or []}


@router.patch("/items/{item_id}")
def update_shop_item(item_id: str, payload: ShopItemPatchRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    item_res = sb.table("shop_items").select("*").eq("guild_id", gid).eq("item_id", str(item_id)).limit(1).execute()
    rows = sb_data(item_res) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Shop item not found.")
    item = rows[0]
    company_id = str(item.get("vendor_company_id") or "")
    if not is_staff(actor):
        if not company_id or company_member_rank(sb, company_id, actor) < 2:
            raise HTTPException(status_code=403, detail="You must be this shop's owner or manager to edit listings.")

    patch = {}
    if payload.name is not None:
        patch["name"] = payload.name.strip()
    if payload.description is not None:
        patch["description"] = payload.description.strip()
    if payload.price is not None:
        patch["price"] = int(payload.price)
    if payload.stock is not None:
        patch["stock"] = int(payload.stock)
    if payload.is_active is not None:
        # Non-staff can unpublish their own items, but staff approval should still control publishing.
        if payload.is_active and not is_staff(actor):
            raise HTTPException(status_code=403, detail="Staff approval is required to publish listings.")
        patch["is_active"] = bool(payload.is_active)
    if payload.review_status is not None:
        if not is_staff(actor):
            raise HTTPException(status_code=403, detail="Staff only can set review status directly.")
        patch["review_status"] = payload.review_status.strip()

    if not patch:
        raise HTTPException(status_code=400, detail="No item changes provided.")

    sb.table("shop_items").update(patch).eq("guild_id", gid).eq("item_id", str(item_id)).execute()
    return {"ok": True, "updated_fields": sorted(patch.keys())}
