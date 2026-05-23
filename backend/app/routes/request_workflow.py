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
    for key in ("user_id", "discord_id", "submitted_by", "requested_by", "requested_by_discord_id", "actor_discord_id"):
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
    total_cost = row.get("total_cost") or row.get("cost") or row.get("amount")
    item_count = row.get("item_count") or row.get("items_count")
    stat_name = row.get("stat_key") or row.get("stat_name") or row.get("stat") or "Stat Upgrade"
    amount = row.get("amount") or row.get("delta") or row.get("new_value") or row.get("requested_value") or total_cost

    summary_bits = []
    if total_cost is not None:
        summary_bits.append(f"{total_cost} XP")
    if item_count is not None:
        summary_bits.append(f"{item_count} stat change(s)")

    return {
        "request_type": "stat",
        "request_id": str(row.get("request_id") or row.get("id") or row.get("stat_request_id") or ""),
        "table": "stat_upgrade_requests",
        "status": _status(row),
        "title": "Stat Upgrade",
        "summary": " • ".join(summary_bits) if summary_bits else f"{stat_name}: {amount if amount is not None else 'requested'}",
        "amount": amount,
        "character_id": character_id,
        "character_name": character.get("name") or row.get("character_name") or character_id,
        "actor_id": _actor_id(row),
        "reviewer_id": _reviewer_id(row),
        "reason": row.get("reason") or row.get("notes") or row.get("note") or row.get("submitter_note"),
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
        return "stat_upgrade_requests"
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


# --- Request Queue OC Name Enrichment v1 ---

def _enrich_request_oc_names(sb, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Attach readable OC names to request queue items using characters.character_id.
    if not items:
        return items

    character_ids: list[str] = []
    for item in items:
        cid = (
            item.get("character_id")
            or item.get("oc_id")
            or item.get("character")
            or item.get("target_character_id")
        )
        if cid is not None:
            cid_str = str(cid)
            if cid_str and cid_str not in character_ids:
                character_ids.append(cid_str)

    if not character_ids:
        return items

    try:
        character_rows = sb_data(
            sb.table("characters")
            .select("character_id,name,user_id")
            .eq("guild_id", get_guild_id())
            .in_("character_id", character_ids)
            .execute()
        ) or []
    except Exception:
        character_rows = []

    names_by_id = {
        str(row.get("character_id")): row.get("name")
        for row in character_rows
        if row.get("character_id") and row.get("name")
    }

    for item in items:
        cid = (
            item.get("character_id")
            or item.get("oc_id")
            or item.get("character")
            or item.get("target_character_id")
        )
        if cid is None:
            continue

        cid_str = str(cid)
        oc_name = names_by_id.get(cid_str)

        if oc_name:
            item["character_name"] = oc_name
            item["oc_name"] = oc_name

            if item.get("oc") == cid_str:
                item["oc"] = oc_name

    return items

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
            sb.table("stat_upgrade_requests")
            .select("*")
            .eq("guild_id", get_guild_id())
            .order("created_at", desc=True)
            .limit(250)
        )

        stat_request_ids = [
            str(row.get("request_id"))
            for row in raw_stat_rows
            if row.get("request_id")
        ]
        if stat_request_ids:
            stat_items = _safe_rows(
                sb.table("stat_upgrade_request_items")
                .select("request_id,stat_key,current_value,target_value,points_added,cost")
                .in_("request_id", stat_request_ids)
                .limit(1000)
            )
            items_by_request: dict[str, list[dict[str, Any]]] = {}
            for item in stat_items:
                rid = str(item.get("request_id") or "")
                if rid:
                    items_by_request.setdefault(rid, []).append(item)

            for row in raw_stat_rows:
                rid = str(row.get("request_id") or "")
                row["items"] = items_by_request.get(rid, [])
                row["item_count"] = len(row["items"])

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

    requests = _enrich_request_oc_names(sb, requests)
    return {
        "requests": requests,
        "is_staff": staff,
        "mine": mine,
        "status": status,
        "request_type": request_type,
    }


# --- Origin / Trait Free Skill Guardrail v1 ---

def _is_origin_trait_free_skill_request(row: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(row.get(key) or "")
        for key in (
            "request_source",
            "source",
            "source_type",
            "submitter_note",
            "reason",
            "notes",
            "note",
            "staff_note",
            "override_reason",
        )
    ).lower()

    positive_markers = (
        "origin / trait free skill",
        "origin/trait free skill",
        "origin trait free skill",
        "trait free skill",
        "free skill choice",
        "free skill request",
        "trait benefit",
        "origin benefit",
        "registration free skill",
        "submitted for staff review after registration",
    )

    return any(marker in haystack for marker in positive_markers)


def _origin_trait_free_skill_note(existing_note: str | None = None) -> str:
    note = str(existing_note or "").strip()
    if note:
        return note
    return "Origin / trait free skill choice approved. No XP charged."

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
    original_cost = int(request_row.get("cost") or 0)
    cost = original_cost
    discount_meta: dict[str, Any] = {"discount_applied": False, "base_cost": original_cost, "final_cost": original_cost}

    if not character_id or not skill_key:
        raise HTTPException(status_code=400, detail="Skill request is missing character or skill.")

    auto_free_skill = _is_origin_trait_free_skill_request(request_row)
    if auto_free_skill:
        staff_override = True
        staff_note = _origin_trait_free_skill_note(
            staff_note or request_row.get("staff_note") or request_row.get("submitter_note")
        )

    cost, discount_meta = _adjust_skill_purchase_cost(sb, character_id, skill_key, original_cost)

    if auto_free_skill:
        cost = 0
        discount_meta = {
            **(discount_meta or {}),
            "discount_applied": True,
            "base_cost": original_cost,
            "final_cost": 0,
            "discount_reason": "Origin / trait free skill choice.",
            "auto_free_skill_guardrail": True,
        }

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

    if not staff_override and cost > 0 and available_xp < cost:
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
                "metadata": {"skill_key": skill_key, "staff_override": staff_override, "cost_adjustment": discount_meta},
            })
            .execute()
        ) or []
        if tx_rows:
            xp_tx_id = tx_rows[0].get("xp_tx_id")

    sb.table("oc_skills").insert({
        "guild_id": gid,
        "character_id": character_id,
        "skill_key": skill_key,
        "acquired_via": "xp" if staff_override else "xp",
        "xp_cost_paid": 0 if staff_override else cost,
        "xp_tx_id": xp_tx_id,
        "actor_discord_id": actor_discord_id,
        "notes": staff_note or (
            discount_meta.get("discount_reason")
            or (
                "Origin / trait free skill choice approved. No XP charged."
                if discount_meta.get("auto_free_skill_guardrail")
                else None
            )
            or ("Origin / trait free skill approved. No XP charged." if auto_free_skill else ("Staff override approval." if staff_override else "Skill purchase approved."))
        ),
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
    was_already_approved = str(row.get("status") or "").lower() == "approved"

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
                request_row = {**row, **request_row}
                _apply_skill_purchase_approval(
                    sb,
                    request_row,
                    int(actor_discord_id),
                    update_payload.get("staff_note") or update_payload.get("note"),
                    bool(
                    payload.get("staff_override")
                    or payload.get("override_requirements")
                    or payload.get("bypass_requirements")
                    or _is_origin_trait_free_skill_request(request_row)
                ),
                    already_reviewed=was_already_approved,
                )

    updated = updated_rows[0] if updated_rows else {**row, **update_payload}

    # --- Stat Upgrade Approval Apply v1 ---
    if table == "stat_upgrade_requests":
        request_row = updated_rows[0] if updated_rows else None
        if not request_row:
            original_rows = sb_data(sb.table(table).select("*").eq(id_column, request_id).limit(1).execute()) or []
            request_row = original_rows[0] if original_rows else None
        if request_row:
            _apply_stat_upgrade_approval(
                sb,
                request_row,
                int(staff_id),
                update_payload.get("staff_note") or update_payload.get("note"),
                already_reviewed=was_already_approved,
            )

    # --- Skill Approval Always Apply v1 ---
    if table == "skill_purchase_requests":
        request_row = updated_rows[0] if updated_rows else None
        if not request_row:
            original_rows = sb_data(sb.table(table).select("*").eq(id_column, request_id).limit(1).execute()) or []
            request_row = original_rows[0] if original_rows else None
        if request_row:
            request_row = {**row, **request_row}
            _apply_skill_purchase_approval(
                sb,
                request_row,
                int(staff_id),
                update_payload.get("staff_note") or update_payload.get("note"),
                bool(
                    payload.get("staff_override")
                    or payload.get("override_requirements")
                    or payload.get("bypass_requirements")
                    or _is_origin_trait_free_skill_request(request_row)
                    or _is_origin_trait_free_skill_request(row)
                ),
                already_reviewed=was_already_approved,
            )


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
            "staff_override": bool(
                payload.get("override_requirements")
                or payload.get("staff_override")
                or (request_type == "skill" and _is_origin_trait_free_skill_request(row))
            ),
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
        reason = "Staff override approved."

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
    # Map legacy request-review fields to the real request table schemas.
    if table == "stat_upgrade_requests":
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

    attempts: list[dict[str, Any]] = [dict(update_payload)]

    # If schema is older/minimal, keep falling back until at least status can update.
    if "status" in update_payload:
        attempts.append({key: value for key, value in update_payload.items() if key in {"status", "staff_note", "reviewed_by_discord_id", "reviewed_at"}})
        attempts.append({key: value for key, value in update_payload.items() if key in {"status", "staff_note"}})
        attempts.append({"status": update_payload["status"]})

    last_error: Exception | None = None
    for attempt in attempts:
        if not attempt:
            continue
        try:
            return _as_list(
                sb.table(table)
                .update(attempt)
                .eq(id_column, request_id)
                .execute()
            )
        except Exception as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error
    return []


# --- Stat Upgrade Approval Apply v1 ---

def _apply_stat_upgrade_approval(
    sb,
    request_row: dict[str, Any],
    actor_discord_id: int,
    staff_note: str | None = None,
    already_reviewed: bool = False,
) -> None:
    gid = get_guild_id()
    request_id = str(request_row.get("request_id") or "")
    character_id = str(request_row.get("character_id") or "")
    total_cost = int(request_row.get("total_cost") or 0)

    if not request_id or not character_id:
        raise HTTPException(status_code=400, detail="Stat request is missing request or character id.")

    items = _safe_rows(
        sb.table("stat_upgrade_request_items")
        .select("*")
        .eq("request_id", request_id)
        .limit(1000)
    )

    if not items:
        raise HTTPException(status_code=400, detail="Stat request has no upgrade items to apply.")

    # Validate every stat_key before touching XP or oc_stats.
    # This prevents partial approvals where XP/stat rows update and then a later
    # item crashes on an oc_stats -> stat_definitions foreign key.
    requested_stat_keys = sorted({
        str(item.get("stat_key") or "").strip()
        for item in items
        if str(item.get("stat_key") or "").strip()
    })

    if requested_stat_keys:
        definition_rows = sb_data(
            sb.table("stat_definitions")
            .select("stat_key")
            .in_("stat_key", requested_stat_keys)
            .execute()
        ) or []
        defined_keys = {str(row.get("stat_key")) for row in definition_rows if row.get("stat_key")}
        missing_keys = [key for key in requested_stat_keys if key not in defined_keys]
        if missing_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve stat request because these stat keys are missing from stat_definitions: {', '.join(missing_keys)}",
            )

    should_charge_xp = not already_reviewed

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
    earned_xp = int((wallet or {}).get("total_earned_xp") or available_xp)

    if should_charge_xp and available_xp < total_cost:
        raise HTTPException(status_code=400, detail=f"OC does not have enough XP. Available: {available_xp}, cost: {total_cost}.")

    if should_charge_xp:
        new_available = available_xp - total_cost
        new_spent = spent_xp + total_cost

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
                "total_earned_xp": earned_xp,
                "total_spent_xp": new_spent,
            }).execute()

        try:
            sb.table("oc_xp_transactions").insert({
                "guild_id": gid,
                "character_id": character_id,
                "direction": "spend",
                "amount": total_cost,
                "source": "stat_upgrade",
                "reference_type": None,
                "reference_key": request_id,
                "reason": staff_note or "Approved stat upgrade request.",
                "actor_discord_id": actor_discord_id,
                "metadata": {
                    "request_id": request_id,
                    "items": items,
                },
            }).execute()
        except Exception:
            pass

    for item in items:
        stat_key = str(item.get("stat_key") or "").strip()
        target_value = int(item.get("target_value") or 0)
        current_value = int(item.get("current_value") or 0)
        cost = int(item.get("cost") or 0)

        if not stat_key:
            continue

        existing_rows = sb_data(
            sb.table("oc_stats")
            .select("*")
            .eq("guild_id", gid)
            .eq("character_id", character_id)
            .eq("stat_key", stat_key)
            .limit(1)
            .execute()
        ) or []

        if existing_rows:
            sb.table("oc_stats").update({
                "stat_value": target_value,
            }).eq("guild_id", gid).eq("character_id", character_id).eq("stat_key", stat_key).execute()
        else:
            sb.table("oc_stats").insert({
                "guild_id": gid,
                "character_id": character_id,
                "stat_key": stat_key,
                "stat_value": target_value,
            }).execute()

        try:
            sb.table("stat_ledger").insert({
                "guild_id": gid,
                "character_id": character_id,
                "stat_key": stat_key,
                "old_value": current_value,
                "new_value": target_value,
                "delta": target_value - current_value,
                "xp_cost": cost,
                "source": "stat_upgrade_request",
                "reference_key": request_id,
                "actor_discord_id": actor_discord_id,
                "note": staff_note or "Approved stat upgrade request.",
            }).execute()
        except Exception:
            pass

# --- Mana Circuits Magecraft Discount v1 ---

def _character_has_trait_slug(sb, character_id: str, trait_slug: str) -> bool:
    gid = get_guild_id()

    trait_rows = sb_data(
        sb.table("traits")
        .select("trait_id,slug,name")
        .eq("guild_id", gid)
        .eq("slug", trait_slug)
        .limit(1)
        .execute()
    ) or []

    if not trait_rows:
        return False

    trait_id = str(trait_rows[0].get("trait_id") or "")
    if not trait_id:
        return False

    for table in ("character_traits", "oc_traits"):
        try:
            rows = sb_data(
                sb.table(table)
                .select("trait_id")
                .eq("guild_id", gid)
                .eq("character_id", character_id)
                .eq("trait_id", trait_id)
                .limit(1)
                .execute()
            ) or []
            if rows:
                return True
        except Exception:
            continue

    return False


def _skill_is_magecraft(sb, skill_key: str) -> bool:
    gid = get_guild_id()
    key = str(skill_key or "").lower()

    if key.startswith("magecraft_") or "magecraft" in key:
        return True

    try:
        rows = sb_data(
            sb.table("skill_definitions")
            .select("skill_key,name,tree")
            .eq("guild_id", gid)
            .eq("skill_key", skill_key)
            .limit(1)
            .execute()
        ) or []
    except Exception:
        rows = []

    if not rows:
        return False

    skill = rows[0]
    tree = str(skill.get("tree") or "").lower()
    name = str(skill.get("name") or "").lower()

    return "magecraft" in tree or "magecraft" in name


def _adjust_skill_purchase_cost(sb, character_id: str, skill_key: str, base_cost: int) -> tuple[int, dict[str, Any]]:
    base_cost = int(base_cost or 0)

    if base_cost <= 0:
        return base_cost, {"discount_applied": False, "base_cost": base_cost, "final_cost": base_cost}

    has_mana_circuits = _character_has_trait_slug(sb, character_id, "mana_circuits_mage")
    is_magecraft = _skill_is_magecraft(sb, skill_key)

    if has_mana_circuits and is_magecraft:
        # Mana Circuits Mage benefit: Magecraft skills cost 1/4.
        # Use ceiling math so odd costs like 265 become 67, not 66.
        final_cost = max(0, (base_cost + 3) // 4)
        return final_cost, {
            "discount_applied": True,
            "discount_reason": "Mana Circuits (Mage): Magecraft skills cost 1/4 XP.",
            "base_cost": base_cost,
            "final_cost": final_cost,
            "discount_multiplier": 0.25,
        }

    return base_cost, {
        "discount_applied": False,
        "base_cost": base_cost,
        "final_cost": base_cost,
        "has_mana_circuits_mage": has_mana_circuits,
        "is_magecraft_skill": is_magecraft,
    }

# --- Skill Purchase Approval Apply v2 Idempotent ---

def _apply_skill_purchase_approval(
    sb,
    request_row: dict[str, Any],
    actor_discord_id: int,
    staff_note: str | None = None,
    staff_override: bool = False,
    already_reviewed: bool = False,
) -> None:
    gid = get_guild_id()
    character_id = str(request_row.get("character_id") or "")
    skill_key = str(request_row.get("skill_key") or "")
    request_id = str(request_row.get("request_id") or "")
    original_cost = int(request_row.get("cost") or 0)
    cost = original_cost
    discount_meta: dict[str, Any] = {
        "discount_applied": False,
        "base_cost": original_cost,
        "final_cost": original_cost,
    }

    if not character_id or not skill_key:
        raise HTTPException(status_code=400, detail="Skill request is missing character or skill.")

    cost, discount_meta = _adjust_skill_purchase_cost(sb, character_id, skill_key, original_cost)

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

    should_charge_xp = (not staff_override) and (not already_reviewed)

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

    if should_charge_xp and available_xp < cost:
        raise HTTPException(status_code=400, detail=f"OC does not have enough XP. Available: {available_xp}, cost: {cost}.")

    xp_tx_id = None

    if should_charge_xp:
        new_available = available_xp - cost
        new_spent = spent_xp + cost

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

        try:
            tx_rows = sb_data(
                sb.table("oc_xp_transactions")
                .insert({
                    "guild_id": gid,
                    "character_id": character_id,
                    "direction": "spend",
                    "amount": cost,
                    "source": "skill_purchase",
                    "reference_type": None,
                    "reference_key": request_id or "skill_purchase_request",
                    "reason": staff_note or discount_meta.get("discount_reason") or f"Approved skill purchase: {skill_key}",
                    "actor_discord_id": actor_discord_id,
                    "metadata": {"skill_key": skill_key, "staff_override": staff_override, "cost_adjustment": discount_meta},
                })
                .execute()
            ) or []
            if tx_rows:
                xp_tx_id = tx_rows[0].get("xp_tx_id")
        except Exception:
            xp_tx_id = None

    sb.table("oc_skills").insert({
        "guild_id": gid,
        "character_id": character_id,
        "skill_key": skill_key,
        "acquired_via": "xp" if staff_override else "xp",
        "xp_cost_paid": 0 if (staff_override or already_reviewed) else cost,
        "xp_tx_id": xp_tx_id,
        "actor_discord_id": actor_discord_id,
        "notes": staff_note or (
            discount_meta.get("discount_reason")
            or ("Backfilled from already-approved skill request." if already_reviewed else "Skill purchase approved.")
        ),
    }).execute()
