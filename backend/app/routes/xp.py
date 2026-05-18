from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.models import PreviewRequest, SubmitStatRequest
from app.security import actor_from_header
from app.services import build_preview, get_guild_id, sb_data
from app.supabase_client import get_supabase, raise_clean_api_error
from app.discord_webhook import notify_stat_submitted

router = APIRouter(prefix="/api", tags=["xp"])


@router.post("/xp/preview")
def preview_xp_purchase(payload: PreviewRequest):
    sb = get_supabase()

    try:
        return build_preview(sb, payload.character_id, dict(payload.target_stats))
    except APIError as e:
        raise_clean_api_error(e)

@router.post("/stat-requests")
def submit_stat_request(
    payload: SubmitStatRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    # Source of truth for submitter must be the authenticated actor/header.
    # The frontend can carry stale localStorage/dev Discord IDs, so rejecting mismatches here
    # caused valid stat/XP requests to 403 before reaching Supabase.
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    submitter_id = int(actor_discord_id)

    sb = get_supabase()

    try:
        rpc = sb.rpc(
            "submit_stat_upgrade_request",
            {
                "p_guild_id": get_guild_id(),
                "p_character_id": str(payload.character_id),
                "p_requested_by_discord_id": submitter_id,
                "p_target_stats": dict(payload.target_stats),
                "p_submitter_note": payload.submitter_note,
            },
        ).execute()
    except APIError as e:
        raise_clean_api_error(e)

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    if isinstance(result, dict):
        notify_stat_submitted(result)

    return {"request": result}