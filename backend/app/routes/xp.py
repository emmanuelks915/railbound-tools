from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.models import PreviewRequest, SubmitStatRequest
from app.security import actor_from_header
from app.services import build_preview, get_guild_id, sb_data
from app.supabase_client import get_supabase, raise_clean_api_error

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
    if actor_discord_id is not None and actor_discord_id != payload.requested_by_discord_id:
        raise HTTPException(status_code=403, detail="Header Discord ID does not match submitter.")

    sb = get_supabase()

    try:
        rpc = sb.rpc(
            "submit_stat_upgrade_request",
            {
                "p_guild_id": get_guild_id(),
                "p_character_id": str(payload.character_id),
                "p_requested_by_discord_id": int(payload.requested_by_discord_id),
                "p_target_stats": dict(payload.target_stats),
                "p_submitter_note": payload.submitter_note,
            },
        ).execute()
    except APIError as e:
        raise_clean_api_error(e)

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    return {"request": result}