from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

try:
    from app.utils.activity_logger import log_activity
except Exception:  # pragma: no cover
    def log_activity(**kwargs):
        return None


router = APIRouter(prefix="/api/requests", tags=["requests"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _require_login(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")
    return int(actor_discord_id)


def _require_staff(actor_discord_id: int | None) -> int:
    actor = _require_login(actor_discord_id)
    if not is_staff(actor):
        raise HTTPException(status_code=403, detail="Staff only.")
    return actor


def _status(row: dict[str, Any]) -> str:
    value = str(row.get("status") or row.get("state") or "pending").lower()
    if value in {"approved", "accepted", "complete", "completed"}:
        return "approved"
    if value in {"denied", "rejected", "declined"}:
        return "denied"
    return "pending"


def _created_at(row: dict[str, Any]) -> str | None:
    for key in ("created_at", "submitted_at", "requested_at", "timestamp"):
        if row.get(key):
            return str(row.get(key))
    return None


def _actor_id(row: dict[str, Any]) -> str | None:
    for key in ("user_id", "discord_id", "submitted_by", "requested_by", "actor_discord_id"):
        if row.get(key) is not None:
            return str(row.get(key))
    return None


def _reviewer_id(row: dict[str, Any]) -> str | None:
    for key in ("approved_by", "denied_by", "reviewed_by", "staff_discord_id"):
        if row.get(key) is not None:
            return str(row.get(key))
    return None


def _character_id(row: dict[str, Any]) -> str | None:
    for key in ("character_id", "oc_id", "target_character_id"):
        if row.get(key) is not None:
            return str(row.get(key))
    return None


def _character_lookup(sb, ids: set[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}

    rows = _safe_rows(
        sb.table("characters")
        .select("character_id,id,name,user_id,discord_id,owner_discord_id,player_discord_id")
        .eq("guild_id", get_guild_id())
        .in_("character_id", list(ids))
        .limit(500)
    )

    if not rows:
        rows = _safe_rows(
            sb.table("characters")
            .select("character_id,id,name,user_id,discord_id,owner_discord_id,player_discord_id")
            .in_("character_id", list(ids))
            .limit(500)
        )

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in ("character_id", "id"):
            if row.get(key):
                out[str(row.get(key))] = row
    return out


def _normalize_stat_request(row: dict[str, Any], characters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    character_id = _character_id(row)
    character = characters.get(character_id or "", {})
    stat_name = row.get("stat_key") or row.get("stat_name") or row.get("stat") or "Stat"
    amount = row.get("amount") or row.get("delta") or row.get("new_value") or row.get("requested_value")

    return {
        "request_type": "stat",
        "request_id": str(row.get("request_id") or row.get("id") or row.get("stat_request_id") or ""),
        "table": "stat_requests",
        "status": _status(row),
        "title": f"{stat_name}",
        "summary": f"{stat_name}: {amount if amount is not None else 'requested'}",
        "amount": amount,
        "character_id": character_id,
        "character_name": character.get("name") or row.get("character_name"),
        "actor_id": _actor_id(row),
        "reviewer_id": _reviewer_id(row),
        "reason": row.get("reason") or row.get("notes") or row.get("note"),
        "staff_note": row.get("staff_note") or row.get("review_note") or row.get("denial_reason"),
        "created_at": _created_at(row),
        "raw": row,
    }


def _normalize_skill_request(row: dict[str, Any], characters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    character_id = _character_id(row)
    character = characters.get(character_id or "", {})
    skill_name = row.get("skill_name") or row.get("name") or row.get("skill_key") or row.get("skill_id") or "Skill"
    cost = row.get("cost") or row.get("xp_cost")

    return {
        "request_type": "skill",
        "request_id": str(row.get("request_id") or row.get("id") or row.get("skill_request_id") or ""),
        "table": "skill_requests",
        "status": _status(row),
        "title": f"{skill_name}",
        "summary": f"{skill_name}{f' • {cost} XP' if cost is not None else ''}",
        "amount": cost,
        "character_id": character_id,
        "character_name": character.get("name") or row.get("character_name"),
        "actor_id": _actor_id(row),
        "reviewer_id": _reviewer_id(row),
        "reason": row.get("reason") or row.get("notes") or row.get("note"),
        "staff_note": row.get("staff_note") or row.get("review_note") or row.get("denial_reason"),
        "created_at": _created_at(row),
        "raw": row,
    }


def _id_column(row: dict[str, Any], request_type: str) -> str:
    candidates = ["request_id", "id", f"{request_type}_request_id"]
    for key in candidates:
        if row.get(key) is not None:
            return key
    return "id"


def _table_for_request_type(request_type: str) -> str:
    if request_type == "stat":
        return "stat_requests"
    if request_type == "skill":
        return "skill_requests"
    raise HTTPException(status_code=400, detail="request_type must be stat or skill.")


def _load_request(sb, request_type: str, request_id: str) -> tuple[str, str, dict[str, Any]]:
    table = _table_for_request_type(request_type)

    for column in ("request_id", "id", f"{request_type}_request_id"):
        rows = _safe_rows(
            sb.table(table)
            .select("*")
            .eq("guild_id", get_guild_id())
            .eq(column, request_id)
            .limit(1)
        )

        if not rows:
            rows = _safe_rows(
                sb.table(table)
                .select("*")
                .eq(column, request_id)
                .limit(1)
            )

        if rows:
            return table, column, rows[0]

    raise HTTPException(status_code=404, detail="Request not found.")


@router.get("/queue")
def get_request_queue(
    actor_discord_id: int | None = Depends(actor_from_header),
    status: str = Query("pending"),
    request_type: str = Query("all"),
    mine: bool = Query(False),
):
    actor = _require_login(actor_discord_id)
    staff = is_staff(actor)

    if not staff and not mine:
        mine = True

    sb = get_supabase()
    wanted_status = status.lower()

    raw_stat_rows: list[dict[str, Any]] = []
    raw_skill_rows: list[dict[str, Any]] = []

    if request_type in {"all", "stat"}:
        raw_stat_rows = _safe_rows(
            sb.table("stat_requests")
            .select("*")
            .eq("guild_id", get_guild_id())
            .order("created_at", desc=True)
            .limit(250)
        )

    if request_type in {"all", "skill"}:
        raw_skill_rows = _safe_rows(
            sb.table("skill_requests")
            .select("*")
            .eq("guild_id", get_guild_id())
            .order("created_at", desc=True)
            .limit(250)
        )

    character_ids = {_character_id(row) for row in raw_stat_rows + raw_skill_rows if _character_id(row)}
    characters = _character_lookup(sb, {str(cid) for cid in character_ids if cid})

    requests = [
        *[_normalize_stat_request(row, characters) for row in raw_stat_rows],
        *[_normalize_skill_request(row, characters) for row in raw_skill_rows],
    ]

    if wanted_status != "all":
        requests = [row for row in requests if row["status"] == wanted_status]

    if mine:
        requests = [
            row
            for row in requests
            if str(row.get("actor_id")) == str(actor)
            or str(characters.get(row.get("character_id") or "", {}).get("user_id")) == str(actor)
            or str(characters.get(row.get("character_id") or "", {}).get("discord_id")) == str(actor)
            or str(characters.get(row.get("character_id") or "", {}).get("owner_discord_id")) == str(actor)
        ]

    requests.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)

    return {
        "requests": requests,
        "is_staff": staff,
        "mine": mine,
        "status": status,
        "request_type": request_type,
    }


@router.post("/{request_type}/{request_id}/approve")
def approve_request(
    request_type: str,
    request_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = _require_staff(actor_discord_id)
    sb = get_supabase()

    table, id_column, row = _load_request(sb, request_type, request_id)

    update_payload = {
        "status": "approved",
        "reviewed_by": str(staff_id),
        "staff_note": payload.get("staff_note") or payload.get("note"),
    }

    # Try common timestamp field if it exists; harmlessly ignored by fallback if schema rejects.
    updated_rows = []
    try:
        updated_rows = _as_list(
            sb.table(table)
            .update({**update_payload, "approved_at": "now()"})
            .eq(id_column, request_id)
            .execute()
        )
    except Exception:
        updated_rows = _as_list(
            sb.table(table)
            .update(update_payload)
            .eq(id_column, request_id)
            .execute()
        )

    updated = updated_rows[0] if updated_rows else {**row, **update_payload}

    log_activity(
        event_type=f"{request_type}_request_approved",
        label=f"{request_type.title()} request approved",
        status="approved",
        actor_discord_id=staff_id,
        character_id=_character_id(row),
        character_name=row.get("character_name"),
        note=payload.get("staff_note") or payload.get("note"),
        source="request_workflow",
        details={"request_id": request_id, "request_type": request_type, "table": table},
        webhook_title=f"✅ {request_type.title()} Request Approved",
        webhook_description=payload.get("staff_note") or payload.get("note"),
    )

    return {"request": updated, "message": f"{request_type.title()} request approved."}


@router.post("/{request_type}/{request_id}/deny")
def deny_request(
    request_type: str,
    request_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = _require_staff(actor_discord_id)
    reason = str(payload.get("reason") or payload.get("staff_note") or "").strip()

    if not reason:
        raise HTTPException(status_code=400, detail="A denial reason is required.")

    sb = get_supabase()
    table, id_column, row = _load_request(sb, request_type, request_id)

    update_payload = {
        "status": "denied",
        "reviewed_by": str(staff_id),
        "denial_reason": reason,
        "staff_note": reason,
    }

    updated_rows = []
    try:
        updated_rows = _as_list(
            sb.table(table)
            .update({**update_payload, "denied_at": "now()"})
            .eq(id_column, request_id)
            .execute()
        )
    except Exception:
        updated_rows = _as_list(
            sb.table(table)
            .update(update_payload)
            .eq(id_column, request_id)
            .execute()
        )

    updated = updated_rows[0] if updated_rows else {**row, **update_payload}

    log_activity(
        event_type=f"{request_type}_request_denied",
        label=f"{request_type.title()} request denied",
        status="denied",
        actor_discord_id=staff_id,
        character_id=_character_id(row),
        character_name=row.get("character_name"),
        note=reason,
        source="request_workflow",
        details={"request_id": request_id, "request_type": request_type, "table": table},
        webhook_title=f"❌ {request_type.title()} Request Denied",
        webhook_description=reason,
    )

    return {"request": updated, "message": f"{request_type.title()} request denied."}
