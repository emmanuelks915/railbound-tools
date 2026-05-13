from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models import StaffActionRequest
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/staff", tags=["staff"])


@router.get("/stat-requests")
def list_stat_requests(
    status: str = Query(default="pending"),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)

    sb = get_supabase()
    req_res = (
        sb.table("stat_upgrade_requests")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    requests = sb_data(req_res) or []

    out = []
    for req in requests:
        request_id = req["request_id"]

        items_res = (
            sb.table("stat_upgrade_request_items")
            .select("*")
            .eq("request_id", request_id)
            .order("created_at", desc=False)
            .execute()
        )
        items = sb_data(items_res) or []

        char_res = (
            sb.table("characters")
            .select("character_id,name,user_id")
            .eq("character_id", req["character_id"])
            .limit(1)
            .execute()
        )
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
    rpc = sb.rpc(
        "approve_stat_upgrade_request",
        {
            "p_request_id": str(request_id),
            "p_staff_discord_id": int(staff_id),
            "p_staff_note": payload.staff_note,
        },
    ).execute()

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
    rpc = sb.rpc(
        "deny_stat_upgrade_request",
        {
            "p_request_id": str(request_id),
            "p_staff_discord_id": int(staff_id),
            "p_staff_note": payload.staff_note,
        },
    ).execute()

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    return {"result": result}
