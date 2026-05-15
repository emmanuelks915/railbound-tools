from __future__ import annotations
from typing import Any

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import SkillPurchaseRequest, StaffActionRequest
from app.permissions import require_character_access, is_staff
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, get_wallet, sb_data
from app.supabase_client import get_supabase
from app.discord_webhook import notify_skill_reviewed, notify_skill_submitted

router = APIRouter(prefix="/api", tags=["skills"])

def _skill_request_for_webhook(sb, request_id: str | UUID) -> dict[str, Any] | None:
    """Fetch the full request row after RPC calls so webhook embeds have character/requester details."""

    gid = get_guild_id()

    req_res = (
        sb.table("skill_purchase_requests")
        .select("*")
        .eq("guild_id", gid)
        .eq("request_id", str(request_id))
        .limit(1)
        .execute()
    )
    req_rows = sb_data(req_res) or []

    if not req_rows:
        return None

    req = req_rows[0]

    char_res = (
        sb.table("characters")
        .select("character_id,name,user_id")
        .eq("guild_id", gid)
        .eq("character_id", req["character_id"])
        .limit(1)
        .execute()
    )
    char_rows = sb_data(char_res) or []
    character = char_rows[0] if char_rows else None

    skill_res = (
        sb.table("skill_definitions")
        .select("skill_key,name,tree,tier,cost")
        .eq("guild_id", gid)
        .eq("skill_key", req["skill_key"])
        .limit(1)
        .execute()
    )
    skill_rows = sb_data(skill_res) or []
    skill = skill_rows[0] if skill_rows else None

    return {
        **req,
        "character": character,
        "character_name": character.get("name") if character else None,
        "skill": skill,
        "skill_name": skill.get("name") if skill else req.get("skill_key"),
    }



@router.get("/skills")
def list_skill_catalog(
    tree: str | None = Query(default=None),
    active_only: bool = True,
    search: str | None = Query(default=None),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Discord-Id header.")

    sb = get_supabase()
    gid = get_guild_id()

    if not active_only and not is_staff(actor_discord_id):
        active_only = True

    q = (
        sb.table("skill_definitions")
        .select("*")
        .eq("guild_id", gid)
        .order("tree", desc=False)
        .order("tier", desc=False)
        .order("sort_order", desc=False)
        .limit(2000)
    )

    if tree and tree != "all":
        q = q.eq("tree", tree)

    if active_only:
        q = q.eq("is_active", True)

    skills = sb_data(q.execute()) or []

    if search:
        needle = search.strip().lower()
        if needle:
            skills = [
                skill
                for skill in skills
                if needle in str(skill.get("name") or "").lower()
                or needle in str(skill.get("skill_key") or "").lower()
                or needle in str(skill.get("tree") or "").lower()
                or needle in str(skill.get("description") or "").lower()
                or needle in str(skill.get("effects") or "").lower()
                or needle in str(skill.get("usage") or "").lower()
            ]

    trees = sorted({str(skill.get("tree") or "General") for skill in skills})

    return {
        "skills": skills,
        "trees": trees,
        "count": len(skills),
    }


@router.get("/characters/{character_id}/skills")
def character_skills(character_id: UUID, actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    require_character_access(sb, character_id, actor_discord_id)
    gid = get_guild_id()

    owned_res = (
        sb.table("oc_skills")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", str(character_id))
        .execute()
    )
    owned = sb_data(owned_res) or []
    owned_keys = [str(r.get("skill_key")) for r in owned if r.get("skill_key")]

    pending_res = (
        sb.table("skill_purchase_requests")
        .select("*")
        .eq("guild_id", gid)
        .eq("character_id", str(character_id))
        .order("created_at", desc=True)
        .limit(250)
        .execute()
    )

    requests = sb_data(pending_res) or []
    pending_keys = [
        str(r.get("skill_key"))
        for r in requests
        if str(r.get("status") or "").lower() == "pending" and r.get("skill_key")
    ]

    return {
        "owned": owned,
        "owned_keys": owned_keys,
        "pending_keys": pending_keys,
        "wallet": get_wallet(sb, character_id, gid),
        "requests": requests,
    }


@router.post("/skill-requests")
def submit_skill_request(payload: SkillPurchaseRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is not None and actor_discord_id != payload.requested_by_discord_id:
        raise HTTPException(status_code=403, detail="Header Discord ID does not match submitter.")

    sb = get_supabase()
    require_character_access(sb, payload.character_id, payload.requested_by_discord_id)

    rpc = sb.rpc(
        "submit_skill_purchase_request",
        {
            "p_guild_id": get_guild_id(),
            "p_character_id": str(payload.character_id),
            "p_skill_key": payload.skill_key,
            "p_requested_by_discord_id": int(payload.requested_by_discord_id),
            "p_submitter_note": payload.submitter_note,
        },
    ).execute()

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    if isinstance(result, dict):
        full_request = _skill_request_for_webhook(sb, result.get("request_id") or result.get("id"))
        notify_skill_submitted(full_request or result)

    return {"request": result}


def _skill_prereq_keys(prerequisites: Any) -> list[str]:
    if not prerequisites:
        return []

    if isinstance(prerequisites, list):
        out: list[str] = []

        for item in prerequisites:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                value = (
                    item.get("skill_key")
                    or item.get("skill")
                    or item.get("key")
                    or item.get("prereq_key")
                )
                if value:
                    out.append(str(value))

        return out

    if isinstance(prerequisites, dict):
        raw = (
            prerequisites.get("skills")
            or prerequisites.get("skill_keys")
            or prerequisites.get("requires")
            or prerequisites.get("prerequisites")
            or prerequisites.get("required_skills")
            or []
        )

        if isinstance(raw, str):
            return [raw]

        if isinstance(raw, list):
            out: list[str] = []

            for item in raw:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict):
                    value = (
                        item.get("skill_key")
                        or item.get("skill")
                        or item.get("key")
                        or item.get("prereq_key")
                    )
                    if value:
                        out.append(str(value))

            return out

    if isinstance(prerequisites, str):
        cleaned = prerequisites.strip()

        if not cleaned or cleaned.lower() in {"none", "n/a", "na"}:
            return []

        # Keep loose prose prereqs visible as text, but do not treat them as a skill_key.
        return []

    return []


@router.get("/staff/skill-requests")
def list_skill_requests(
    status: str = Query(default="pending"),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)

    sb = get_supabase()
    gid = get_guild_id()

    req_res = (
        sb.table("skill_purchase_requests")
        .select("*")
        .eq("guild_id", gid)
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    reqs = sb_data(req_res) or []
    out = []

    for req in reqs:
        character_id = req.get("character_id")
        skill_key = req.get("skill_key")

        char_res = (
            sb.table("characters")
            .select("character_id,name,user_id")
            .eq("guild_id", gid)
            .eq("character_id", character_id)
            .limit(1)
            .execute()
        )

        skill_res = (
            sb.table("skill_definitions")
            .select("*")
            .eq("guild_id", gid)
            .eq("skill_key", skill_key)
            .limit(1)
            .execute()
        )

        character = (sb_data(char_res) or [None])[0]
        skill = (sb_data(skill_res) or [None])[0]

        wallet = None
        owned_keys: list[str] = []
        missing_prereqs: list[str] = []
        prereq_keys: list[str] = []
        prereq_names: list[str] = []

        if character_id:
            try:
                wallet = get_wallet(sb, UUID(str(character_id)), gid)
            except Exception:
                wallet = None

            owned_res = (
                sb.table("oc_skills")
                .select("skill_key")
                .eq("guild_id", gid)
                .eq("character_id", character_id)
                .execute()
            )
            owned_rows = sb_data(owned_res) or []
            owned_keys = [
                str(row.get("skill_key"))
                for row in owned_rows
                if row.get("skill_key")
            ]

        if skill:
            prereq_keys = _skill_prereq_keys(skill.get("prerequisites"))
            missing_prereqs = [
                key
                for key in prereq_keys
                if key not in owned_keys
            ]

            if prereq_keys:
                prereq_res = (
                    sb.table("skill_definitions")
                    .select("skill_key,name")
                    .eq("guild_id", gid)
                    .in_("skill_key", prereq_keys)
                    .execute()
                )
                prereq_rows = sb_data(prereq_res) or []
                prereq_name_lookup = {
                    row.get("skill_key"): row.get("name")
                    for row in prereq_rows
                }
                prereq_names = [
                    prereq_name_lookup.get(key) or key
                    for key in prereq_keys
                ]

        available_xp = int((wallet or {}).get("available_xp") or 0)
        cost = int(req.get("cost") or (skill or {}).get("cost") or 0)
        already_owned = skill_key in owned_keys
        skill_active = bool((skill or {}).get("is_active", True))
        has_enough_xp = available_xp >= cost
        prerequisites_met = len(missing_prereqs) == 0

        review_checks = {
            "skill_active": skill_active,
            "already_owned": already_owned,
            "has_enough_xp": has_enough_xp,
            "available_xp": available_xp,
            "cost": cost,
            "prerequisites_met": prerequisites_met,
            "prereq_keys": prereq_keys,
            "prereq_names": prereq_names,
            "missing_prereq_keys": missing_prereqs,
            "owned_skill_count": len(owned_keys),
            "safe_to_approve": skill_active and not already_owned and has_enough_xp and prerequisites_met,
        }

        out.append(
            {
                **req,
                "character": character,
                "skill": skill,
                "wallet": wallet,
                "review_checks": review_checks,
            }
        )

    return {"requests": out}


@router.post("/staff/skill-requests/{request_id}/approve")
def approve_skill_request(request_id: UUID, payload: StaffActionRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = payload.staff_discord_id or actor_discord_id
    require_staff(staff_id)
    sb = get_supabase()

    rpc = sb.rpc(
        "approve_skill_purchase_request",
        {
            "p_request_id": str(request_id),
            "p_staff_discord_id": int(staff_id),
            "p_staff_note": payload.staff_note,
        },
    ).execute()

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    if isinstance(result, dict):
        full_request = _skill_request_for_webhook(sb, request_id)
        notify_skill_reviewed(
            request_id=request_id,
            action="approved",
            staff_id=staff_id,
            note=payload.staff_note,
            result=full_request or result,
        )

    return {"result": result}


@router.post("/staff/skill-requests/{request_id}/deny")
def deny_skill_request(request_id: UUID, payload: StaffActionRequest, actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = payload.staff_discord_id or actor_discord_id
    require_staff(staff_id)
    sb = get_supabase()

    rpc = sb.rpc(
        "deny_skill_purchase_request",
        {
            "p_request_id": str(request_id),
            "p_staff_discord_id": int(staff_id),
            "p_staff_note": payload.staff_note,
        },
    ).execute()

    result = sb_data(rpc)
    if isinstance(result, list) and result:
        result = result[0]

    if isinstance(result, dict):
        full_request = _skill_request_for_webhook(sb, request_id)
        notify_skill_reviewed(
            request_id=request_id,
            action="denied",
            staff_id=staff_id,
            note=payload.staff_note,
            result=full_request or result,
        )

    return {"result": result}
