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
        "character_name": character.get("name") or row.get("character_name") or character_id,
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
        "table": "skill_purchase_requests",
        "status": _status(row),
        "title": f"{skill_name}",
        "summary": f"{skill_name}{f' • {cost} XP' if cost is not None else ''}",
        "amount": cost,
        "character_id": character_id,
        "character_name": character.get("name") or row.get("character_name") or character_id,
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
        return "skill_purchase_requests"
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
            sb.table("skill_purchase_requests")
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


# --- Skill Purchase Approval Apply v1 ---

def _apply_skill_purchase_approval(
    sb,
    request_row: dict[str, Any],
    actor_discord_id: int,
    staff_note: str | None = None,
    staff_override: bool = False,
) -> None:
    # Deduct XP, grant the skill, and log the XP spend for an approved skill_purchase_request.
    gid = get_guild_id()
    character_id = str(request_row.get("character_id") or "")
    skill_key = str(request_row.get("skill_key") or "")
    cost = int(request_row.get("cost") or 0)

    if not character_id or not skill_key:
        raise HTTPException(status_code=400, detail="Skill request is missing character or skill.")

    existing = sb_data(
        sb.table("oc_skills")
        .select("skill_key")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .eq("skill_key", skill_key)
        .limit(1)
        .execute()
    ) or []
    if existing:
        return

    wallet_rows = sb_data(
        sb.table("oc_xp_wallets")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .limit(1)
        .execute()
    ) or []
    wallet = wallet_rows[0] if wallet_rows else None

    available_xp = int((wallet or {}).get("available_xp") or 0)
    spent_xp = int((wallet or {}).get("total_spent_xp") or 0)

    if not staff_override and available_xp < cost:
        raise HTTPException(status_code=400, detail=f"OC does not have enough XP. Available: {available_xp}, cost: {cost}.")

    new_available = available_xp - cost if not staff_override else available_xp
    new_spent = spent_xp + cost if not staff_override else spent_xp

    if wallet:
        sb.table("oc_xp_wallets").update({
            "available_xp": new_available,
            "total_spent_xp": new_spent,
        }).eq("guild_id", gid).eq("character_id", character_id).execute()
    else:
        sb.table("oc_xp_wallets").insert({
            "guild_id": gid,
            "character_id": character_id,
            "available_xp": new_available,
            "total_earned_xp": available_xp,
            "total_spent_xp": new_spent,
        }).execute()

    xp_tx_id = None
    if cost > 0 and not staff_override:
        tx_rows = sb_data(
            sb.table("oc_xp_transactions")
            .insert({
                "guild_id": gid,
                "character_id": character_id,
                "direction": "spend",
                "amount": cost,
                "source": "skill_purchase",
                "reference_type": "skill_purchase_request",
                "reference_key": str(request_row.get("request_id") or ""),
                "reason": staff_note or f"Approved skill purchase: {skill_key}",
                "actor_discord_id": actor_discord_id,
                "metadata": {"skill_key": skill_key, "staff_override": staff_override},
            })
            .execute()
        ) or []
        if tx_rows:
            xp_tx_id = tx_rows[0].get("xp_tx_id")

    sb.table("oc_skills").insert({
        "guild_id": gid,
        "character_id": character_id,
        "skill_key": skill_key,
        "acquired_via": "staff_override" if staff_override else "skill_purchase",
        "xp_cost_paid": 0 if staff_override else cost,
        "xp_tx_id": xp_tx_id,
        "actor_discord_id": actor_discord_id,
        "notes": staff_note or ("Staff override approval." if staff_override else "Skill purchase approved."),
    }).execute()

@router.post("/{request_type}/{request_id}/approve")
def approve_request(
    request_type: str,
    request_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):

    payload = payload or {}
    staff_id = _require_staff(actor_discord_id)
    sb = get_supabase()

    table, id_column, row = _load_request(sb, request_type, request_id)

    update_payload = {
        "status": "approved",
        "reviewed_by": str(staff_id),
        "staff_note": payload.get("staff_note") or payload.get("note") or payload.get("override_reason"),
    }
    update_payload = _mark_skill_override(update_payload, payload, request_type)

    # Try common timestamp field if it exists; harmlessly ignored by fallback if schema rejects.
    updated_rows = []
    try:
        updated_rows = _safe_update_request(sb, table, id_column, request_id, {**update_payload, "approved_at": "now()"})
    except Exception:
        updated_rows = _safe_update_request(sb, table, id_column, request_id, update_payload)
        if table == "skill_purchase_requests":
            request_row = updated_rows[0] if updated_rows else None
            if not request_row:
                original_rows = sb_data(sb.table(table).select("*").eq(id_column, request_id).limit(1).execute()) or []
                request_row = original_rows[0] if original_rows else None
            if request_row:
                _apply_skill_purchase_approval(
                    sb,
                    request_row,
                    int(actor_discord_id),
                    update_payload.get("staff_note") or update_payload.get("note"),
                    bool(payload.get("staff_override") or payload.get("override_requirements") or payload.get("bypass_requirements")),
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
        details={
            "request_id": request_id,
            "request_type": request_type,
            "table": table,
            "staff_override": bool(payload.get("override_requirements") or payload.get("staff_override")),
            "override_reason": payload.get("override_reason"),
        },
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

    payload = payload or {}
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

    updated_rows = _safe_update_request(
        sb,
        table,
        id_column,
        request_id,
        {**update_payload, "denied_at": "now()"},
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

# --- Skill Staff Override v1 helpers ---

def _skill_override_payload(payload: dict[str, Any], request_type: str) -> tuple[bool, str | None]:
    if request_type != "skill":
        return False, None

    override = bool(payload.get("override_requirements") or payload.get("staff_override"))
    reason = payload.get("override_reason") or payload.get("staff_note") or payload.get("note")

    if override and not str(reason or "").strip():
        raise HTTPException(status_code=400, detail="Override reason is required when staff override is enabled.")

    return override, str(reason).strip() if reason is not None else None


def _mark_skill_override(update_payload: dict[str, Any], payload: dict[str, Any], request_type: str) -> dict[str, Any]:
    override, reason = _skill_override_payload(payload, request_type)

    if not override:
        return update_payload

    update_payload["staff_override"] = True
    update_payload["override_requirements"] = True
    update_payload["override_reason"] = reason
    update_payload["staff_note"] = reason

    return update_payload


# --- Skill Purchase Request Schema Compatibility v1 ---

def _normalize_request_update_payload(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    # Map legacy request-review fields to the real skill_purchase_requests schema.
    if table != "skill_purchase_requests":
        return payload

    out = dict(payload)

    if "approved_at" in out and "reviewed_at" not in out:
        out["reviewed_at"] = out.pop("approved_at")
    else:
        out.pop("approved_at", None)

    if "denied_at" in out and "reviewed_at" not in out:
        out["reviewed_at"] = out.pop("denied_at")
    else:
        out.pop("denied_at", None)

    for old_key in ("reviewed_by", "reviewer_id", "approved_by", "denied_by", "staff_id"):
        if old_key in out and "reviewed_by_discord_id" not in out:
            out["reviewed_by_discord_id"] = out.pop(old_key)
        else:
            out.pop(old_key, None)

    if "note" in out and "staff_note" not in out:
        out["staff_note"] = out.pop("note")

    if "denial_reason" in out and "staff_note" not in out:
        out["staff_note"] = out.pop("denial_reason")

    allowed = {"status", "staff_note", "reviewed_by_discord_id", "reviewed_at", "updated_at"}
    return {key: value for key, value in out.items() if key in allowed}

def _safe_update_request(sb, table: str, id_column: str, request_id: str, update_payload: dict[str, Any]) -> list[dict[str, Any]]:
    update_payload = _normalize_request_update_payload(table, update_payload)
    try:
        return _as_list(
            sb.table(table)
            .update(update_payload)
            .eq(id_column, request_id)
            .execute()
        )
    except Exception:
        allowed = {
            "status",
            "reviewed_by",
            "approved_by",
            "denied_by",
            "staff_discord_id",
            "staff_note",
            "denial_reason",
        }
        fallback = {key: value for key, value in update_payload.items() if key in allowed}
        return _as_list(
            sb.table(table)
            .update(fallback)
            .eq(id_column, request_id)
            .execute()
        )
