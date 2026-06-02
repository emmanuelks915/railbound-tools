from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from postgrest.exceptions import APIError

from app.models import StaffActionRequest
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase, raise_clean_api_error
from app.discord_webhook import notify_shop_listing_reviewed, notify_stat_reviewed
from app.utils.activity_webhooks import send_staff_activity_webhook

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

    if isinstance(result, dict):
        notify_stat_reviewed(
            request_id=request_id,
            action="approved",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

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

    if isinstance(result, dict):
        notify_stat_reviewed(
            request_id=request_id,
            action="denied",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

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

    notify_shop_listing_reviewed(
        item_id=item_id,
        action="approved",
        staff_id=staff_id,
        note=payload.staff_note,
        item=item,
    )

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

    notify_shop_listing_reviewed(
        item_id=item_id,
        action="denied",
        staff_id=staff_id,
        note=payload.staff_note,
        item=item,
    )

    return {
        "ok": True,
        "item": item,
        "message": "Shop listing denied.",
    }

@router.get("/trait-grants/options")
def staff_trait_grant_options(actor_discord_id: int | None = Depends(actor_from_header)):
    require_staff(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    errors: list[str] = []

    try:
        characters = _staff_trait_rows(
            sb.table("characters")
            .select("*")
            .eq("guild_id", gid)
            .order("name")
            .limit(1000)
            .execute()
        )
    except Exception as e:
        errors.append(f"characters:guild-filter:{e}")
        try:
            characters = _staff_trait_rows(
                sb.table("characters")
                .select("*")
                .order("name")
                .limit(1000)
                .execute()
            )
        except Exception as fallback_error:
            errors.append(f"characters:fallback:{fallback_error}")
            characters = []

    try:
        traits = _staff_trait_rows(
            sb.table("traits")
            .select("*")
            .eq("guild_id", gid)
            .order("name")
            .limit(1500)
            .execute()
        )
    except Exception as e:
        errors.append(f"traits:guild-filter:{e}")
        try:
            traits = _staff_trait_rows(
                sb.table("traits")
                .select("*")
                .order("name")
                .limit(1500)
                .execute()
            )
        except Exception as fallback_error:
            errors.append(f"traits:fallback:{fallback_error}")
            traits = []

    normalized_characters = []
    for character in characters:
        character_id = character.get("character_id")
        if not character_id:
            continue

        normalized_characters.append({
            "character_id": character_id,
            "name": character.get("name") or character.get("character_name") or str(character_id),
            "user_id": character.get("user_id") or character.get("discord_id") or character.get("player_discord_id"),
            "guild_id": character.get("guild_id"),
        })

    normalized_traits = []
    for trait in traits:
        trait_id = trait.get("trait_id")
        if not trait_id:
            continue

        is_active = trait.get("is_active")
        if is_active is False:
            continue

        normalized_traits.append({
            "trait_id": trait_id,
            "slug": trait.get("slug") or trait.get("trait_slug") or trait.get("trait_key") or "",
            "name": trait.get("name") or trait.get("display_name") or trait.get("slug") or str(trait_id),
            "category": trait.get("category") or trait.get("trait_type") or "",
            "tier": trait.get("tier"),
            "is_active": is_active,
        })

    return {
        "characters": normalized_characters,
        "traits": normalized_traits,
        "debug_errors": errors,
    }

@router.post("/trait-grants/grant")
def staff_grant_trait(payload: dict = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = actor_discord_id
    require_staff(staff_id)

    sb = get_supabase()
    gid = get_guild_id()

    character_id = _staff_clean_text(payload.get("character_id"), 80)
    reason = _staff_clean_text(payload.get("reason") or payload.get("staff_note"), 1000)

    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC.")
    if not reason:
        raise HTTPException(status_code=400, detail="Staff reason is required.")

    character = _character_for_staff_trait_grant(sb, gid, character_id)
    trait = _resolve_trait_for_staff_grant(sb, gid, payload)
    trait_id = str(trait.get("trait_id"))

    existing = _staff_trait_rows(
        sb.table("character_traits")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .eq("trait_id", trait_id)
        .limit(1)
        .execute()
    )

    if existing:
        return {
            "ok": True,
            "already_owned": True,
            "message": f"{character.get('name') or 'OC'} already has {trait.get('name') or trait.get('slug') or 'that trait'}.",
            "character": character,
            "trait": trait,
            "row": existing[0],
        }

    insert_row = {"guild_id": gid, "character_id": character_id, "trait_id": trait_id}

    try:
        result = sb.table("character_traits").insert(insert_row).execute()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    rows = _staff_trait_rows(result)
    row = rows[0] if rows else insert_row

    _log_staff_trait_grant(
        sb,
        {
            "guild_id": gid,
            "character_id": character_id,
            "trait_id": trait_id,
            "action": "grant",
            "staff_discord_id": int(staff_id) if staff_id is not None else None,
            "reason": reason,
        },
    )


    return {
        "ok": True,
        "message": f"Granted {trait.get('name') or trait.get('slug') or 'trait'} to {character.get('name') or 'OC'}.",
        "character": character,
        "trait": trait,
        "row": row,
    }


@router.post("/trait-grants/remove")
def staff_remove_trait(payload: dict = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = actor_discord_id
    require_staff(staff_id)

    sb = get_supabase()
    gid = get_guild_id()

    character_id = _staff_clean_text(payload.get("character_id"), 80)
    reason = _staff_clean_text(payload.get("reason") or payload.get("staff_note"), 1000)

    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC.")
    if not reason:
        raise HTTPException(status_code=400, detail="Staff reason is required.")

    character = _character_for_staff_trait_grant(sb, gid, character_id)
    trait = _resolve_trait_for_staff_grant(sb, gid, payload)
    trait_id = str(trait.get("trait_id"))

    try:
        result = (
            sb.table("character_traits")
            .delete()
            .eq("guild_id", gid)
            .eq("character_id", character_id)
            .eq("trait_id", trait_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    rows = _staff_trait_rows(result)

    _log_staff_trait_grant(
        sb,
        {
            "guild_id": gid,
            "character_id": character_id,
            "trait_id": trait_id,
            "action": "remove",
            "staff_discord_id": int(staff_id) if staff_id is not None else None,
            "reason": reason,
        },
    )


    return {
        "ok": True,
        "message": f"Removed {trait.get('name') or trait.get('slug') or 'trait'} from {character.get('name') or 'OC'}.",
        "character": character,
        "trait": trait,
        "removed": rows,
    }
