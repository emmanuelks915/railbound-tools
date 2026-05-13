from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from postgrest.exceptions import APIError

from app.models import StaffActionRequest
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase, raise_clean_api_error

router = APIRouter(prefix="/api/staff", tags=["staff"])


@router.get("/stat-requests")
def list_stat_requests(
    status: str = Query(default="pending"),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)

    sb = get_supabase()

    try:
        req_res = (
            sb.table("stat_upgrade_requests")
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
    except APIError as e:
        raise_clean_api_error(e)

    requests = sb_data(req_res) or []

    out = []
    for req in requests:
        request_id = req["request_id"]

        try:
            items_res = (
                sb.table("stat_upgrade_request_items")
                .select("*")
                .eq("request_id", request_id)
                .order("created_at", desc=False)
                .execute()
            )

            char_res = (
                sb.table("characters")
                .select("character_id,name,user_id")
                .eq("character_id", req["character_id"])
                .limit(1)
                .execute()
            )
        except APIError as e:
            raise_clean_api_error(e)

        items = sb_data(items_res) or []
        char_rows = sb_data(char_res) or []
        character = char_rows[0] if char_rows else None

        out.append(
            {
                **req,
                "character": character,
                "items": items,
            }
        )

    return {"requests": out}


@router.post("/stat-requests/{request_id}/approve")
def approve_stat_request(
    request_id: UUID,
    payload: StaffActionRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = payload.staff_discord_id or actor_discord_id
    require_staff(staff_id)

    sb = get_supabase()

    try:
        rpc = sb.rpc(
            "approve_stat_upgrade_request",
            {
                "p_request_id": str(request_id),
                "p_staff_discord_id": int(staff_id),
                "p_staff_note": payload.staff_note,
            },
        ).execute()
    except APIError as e:
        raise_clean_api_error(e)

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    return {"result": result}


@router.post("/stat-requests/{request_id}/deny")
def deny_stat_request(
    request_id: UUID,
    payload: StaffActionRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = payload.staff_discord_id or actor_discord_id
    require_staff(staff_id)

    sb = get_supabase()

    try:
        rpc = sb.rpc(
            "deny_stat_upgrade_request",
            {
                "p_request_id": str(request_id),
                "p_staff_discord_id": int(staff_id),
                "p_staff_note": payload.staff_note,
            },
        ).execute()
    except APIError as e:
        raise_clean_api_error(e)

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    return {"result": result}


@router.get("/shop-items")
def list_shop_item_requests(
    status: str = Query(default="pending_staff_review"),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)

    sb = get_supabase()
    gid = get_guild_id()

    try:
        item_res = (
            sb.table("shop_items")
            .select("*")
            .eq("guild_id", gid)
            .eq("review_status", status)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
    except APIError as e:
        raise_clean_api_error(e)

    items = sb_data(item_res) or []
    out = []

    for item in items:
        company = None
        vendor_company_id = item.get("vendor_company_id")

        if vendor_company_id:
            try:
                company_res = (
                    sb.table("companies")
                    .select("company_id,name,owner_character_id,shop_status")
                    .eq("guild_id", gid)
                    .eq("company_id", str(vendor_company_id))
                    .limit(1)
                    .execute()
                )
                company_rows = sb_data(company_res) or []
                company = company_rows[0] if company_rows else None
            except APIError as e:
                raise_clean_api_error(e)

        out.append(
            {
                **item,
                "company": company,
            }
        )

    return {"items": out}


@router.post("/shop-items/{item_id}/approve")
def approve_shop_item(
    item_id: UUID,
    payload: StaffActionRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = payload.staff_discord_id or actor_discord_id
    require_staff(staff_id)

    sb = get_supabase()
    gid = get_guild_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    patch = {
        "review_status": "approved",
        "is_active": True,
        "reviewed_by": int(staff_id),
        "reviewed_at": now_iso,
        "staff_change_summary": payload.staff_note,
    }

    try:
        update_res = (
            sb.table("shop_items")
            .update(patch)
            .eq("guild_id", gid)
            .eq("item_id", str(item_id))
            .execute()
        )
    except APIError as e:
        raise_clean_api_error(e)

    rows = sb_data(update_res) or []
    item = rows[0] if rows else None

    return {
        "ok": True,
        "item": item,
        "message": "Shop listing approved and published.",
    }


@router.post("/shop-items/{item_id}/deny")
def deny_shop_item(
    item_id: UUID,
    payload: StaffActionRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = payload.staff_discord_id or actor_discord_id
    require_staff(staff_id)

    sb = get_supabase()
    gid = get_guild_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    patch = {
        "review_status": "denied",
        "is_active": False,
        "reviewed_by": int(staff_id),
        "reviewed_at": now_iso,
        "staff_change_summary": payload.staff_note,
    }

    try:
        update_res = (
            sb.table("shop_items")
            .update(patch)
            .eq("guild_id", gid)
            .eq("item_id", str(item_id))
            .execute()
        )
    except APIError as e:
        raise_clean_api_error(e)

    rows = sb_data(update_res) or []
    item = rows[0] if rows else None

    return {
        "ok": True,
        "item": item,
        "message": "Shop listing denied.",
    }