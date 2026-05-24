from __future__ import annotations
from typing import Any

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.models import SkillPurchaseRequest, StaffActionRequest
from app.permissions import require_character_access, is_staff
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, get_wallet, sb_data
from app.supabase_client import get_supabase
from app.utils.activity_webhooks import send_staff_activity_webhook
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
    # Source of truth for submitter must be the authenticated actor/header.
    # The frontend can carry stale localStorage/dev Discord IDs, so rejecting mismatches here
    # caused real requests to 403 before reaching Supabase.
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    submitter_id = int(actor_discord_id)

    sb = get_supabase()
    require_character_access(sb, payload.character_id, submitter_id)

    rpc = sb.rpc(
        "submit_skill_purchase_request",
        {
            "p_guild_id": get_guild_id(),
            "p_character_id": str(payload.character_id),
            "p_skill_key": payload.skill_key,
            "p_requested_by_discord_id": submitter_id,
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
    if not reqs:
        return {"requests": []}

    character_ids = sorted({
        str(req.get("character_id"))
        for req in reqs
        if req.get("character_id")
    })
    skill_keys = sorted({
        str(req.get("skill_key"))
        for req in reqs
        if req.get("skill_key")
    })

    character_lookup: dict[str, dict[str, Any]] = {}
    if character_ids:
        char_rows = sb_data(
            sb.table("characters")
            .select("character_id,name,user_id")
            .eq("guild_id", gid)
            .in_("character_id", character_ids)
            .execute()
        ) or []
        character_lookup = {
            str(row.get("character_id")): row
            for row in char_rows
            if row.get("character_id")
        }

    skill_lookup: dict[str, dict[str, Any]] = {}
    if skill_keys:
        skill_rows = sb_data(
            sb.table("skill_definitions")
            .select("*")
            .eq("guild_id", gid)
            .in_("skill_key", skill_keys)
            .execute()
        ) or []
        skill_lookup = {
            str(row.get("skill_key")): row
            for row in skill_rows
            if row.get("skill_key")
        }

    owned_by_character: dict[str, list[str]] = {
        character_id: []
        for character_id in character_ids
    }
    if character_ids:
        owned_rows = sb_data(
            sb.table("oc_skills")
            .select("character_id,skill_key")
            .eq("guild_id", gid)
            .in_("character_id", character_ids)
            .execute()
        ) or []

        for row in owned_rows:
            character_id = str(row.get("character_id") or "")
            skill_key = row.get("skill_key")
            if character_id and skill_key:
                owned_by_character.setdefault(character_id, []).append(str(skill_key))

    prereq_keys_all: set[str] = set()
    prereq_keys_by_skill: dict[str, list[str]] = {}

    for skill_key, skill in skill_lookup.items():
        prereq_keys = _skill_prereq_keys(skill.get("prerequisites"))
        prereq_keys_by_skill[skill_key] = prereq_keys
        prereq_keys_all.update(prereq_keys)

    prereq_name_lookup: dict[str, str] = {}
    if prereq_keys_all:
        prereq_rows = sb_data(
            sb.table("skill_definitions")
            .select("skill_key,name")
            .eq("guild_id", gid)
            .in_("skill_key", sorted(prereq_keys_all))
            .execute()
        ) or []
        prereq_name_lookup = {
            str(row.get("skill_key")): row.get("name") or str(row.get("skill_key"))
            for row in prereq_rows
            if row.get("skill_key")
        }

    wallet_lookup: dict[str, dict[str, Any] | None] = {}
    for character_id in character_ids:
        try:
            wallet_lookup[character_id] = get_wallet(sb, UUID(str(character_id)), gid)
        except Exception:
            wallet_lookup[character_id] = None

    out = []

    for req in reqs:
        character_id = str(req.get("character_id") or "")
        skill_key = str(req.get("skill_key") or "")

        character = character_lookup.get(character_id)
        skill = skill_lookup.get(skill_key)
        wallet = wallet_lookup.get(character_id)

        owned_keys = owned_by_character.get(character_id, [])
        prereq_keys = prereq_keys_by_skill.get(skill_key, [])

        missing_prereqs = [
            key
            for key in prereq_keys
            if key not in owned_keys
        ]

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


# --- Staff Direct Skill Override Grant v1 ---

@router.get("/staff/skill-overrides/options")
def staff_skill_override_options(actor_discord_id: int | None = Depends(actor_from_header)):
    # Return OC + skill options for the staff direct skill override form.
    require_staff(actor_discord_id)

    sb = get_supabase()
    gid = get_guild_id()

    characters = sb_data(
        sb.table("characters")
        .select("character_id,name,user_id,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .order("name", desc=False)
        .limit(1000)
        .execute()
    ) or []

    skills = sb_data(
        sb.table("skill_definitions")
        .select("skill_key,name,tree,cost,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .order("tree", desc=False)
        .order("name", desc=False)
        .limit(1000)
        .execute()
    ) or []

    return {"characters": characters, "skills": skills}


@router.post("/staff/skill-overrides/grant")
def grant_staff_skill_override(
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    # Directly grant a skill to an OC as a staff override.
    staff_id = actor_discord_id
    require_staff(staff_id)

    character_id = str(payload.get("character_id") or "").strip()
    skill_key = str(payload.get("skill_key") or "").strip()
    reason = str(payload.get("reason") or payload.get("override_reason") or payload.get("staff_note") or "").strip()
    source_trait = str(payload.get("source_trait") or "Staff override").strip()

    if not character_id:
        raise HTTPException(status_code=400, detail="character_id is required.")
    if not skill_key:
        raise HTTPException(status_code=400, detail="skill_key is required.")
    if not reason:
        raise HTTPException(status_code=400, detail="A staff override reason is required.")

    sb = get_supabase()
    gid = get_guild_id()

    character_rows = sb_data(
        sb.table("characters")
        .select("character_id,name,user_id,guild_id,is_active")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .limit(1)
        .execute()
    ) or []
    if not character_rows:
        raise HTTPException(status_code=404, detail="Character not found.")

    character = character_rows[0]

    skill_rows = sb_data(
        sb.table("skill_definitions")
        .select("skill_key,name,tree,cost,is_active")
        .eq("guild_id", gid)
        .eq("skill_key", skill_key)
        .limit(1)
        .execute()
    ) or []
    if not skill_rows:
        raise HTTPException(status_code=404, detail="Skill not found.")

    skill = skill_rows[0]
    if skill.get("is_active") is False:
        raise HTTPException(status_code=400, detail="Cannot grant an inactive skill.")

    existing_rows = sb_data(
        sb.table("oc_skills")
        .select("skill_key")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .eq("skill_key", skill_key)
        .limit(1)
        .execute()
    ) or []

    if existing_rows:
        return {
            "ok": True,
            "already_owned": True,
            "message": "This OC already owns that skill.",
            "character": character,
            "skill": skill,
        }

    note = f"Staff override grant via {source_trait}. Reason: {reason}"

    grant_rows = sb_data(
        sb.table("oc_skills")
        .insert({
            "guild_id": gid,
            "character_id": character_id,
            "skill_key": skill_key,
            "acquired_via": "xp",
            "xp_cost_paid": 0,
            "actor_discord_id": int(staff_id),
            "notes": note,
        })
        .execute()
    ) or []

    grant = grant_rows[0] if grant_rows else {
        "guild_id": gid,
        "character_id": character_id,
        "skill_key": skill_key,
        "acquired_via": "xp",
        "xp_cost_paid": 0,
        "actor_discord_id": int(staff_id),
        "notes": note,
    }

    try:
        sb.table("activity_log").insert({
            "guild_id": gid,
            "event_type": "skill_override_granted",
            "label": f"Skill override granted: {skill.get('name') or skill_key}",
            "status": "approved",
            "actor_discord_id": int(staff_id),
            "character_id": character_id,
            "character_name": character.get("name"),
            "amount": 0,
            "note": note,
            "source": "staff_skill_override",
            "details": {
                "skill_key": skill_key,
                "skill_name": skill.get("name"),
                "source_trait": source_trait,
                "override_reason": reason,
                "bypassed_requirements": True,
                "xp_cost_paid": 0,
            },
        }).execute()
    except Exception:
        pass

    try:
        send_staff_activity_webhook(
            title="Skill Override Granted",
            description=note,
            event_type="skill_override_granted",
            status="approved",
            actor_id=staff_id,
            character_id=character_id,
            character_name=character.get("name"),
            details={
                "skill_key": skill_key,
                "skill_name": skill.get("name"),
                "source_trait": source_trait,
                "bypassed_requirements": True,
                "xp_cost_paid": 0,
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "already_owned": False,
        "message": f"Granted {skill.get('name') or skill_key} to {character.get('name') or 'OC'} as a staff override.",
        "grant": grant,
        "character": character,
        "skill": skill,
    }
# --- Staff Trait Benefit Resolver v1 ---

def _trait_grant_config(trait: dict[str, Any]) -> dict[str, Any]:
    effects = trait.get("effects_json") or {}
    if not isinstance(effects, dict):
        effects = {}

    grants = (
        effects.get("grants")
        or effects.get("grant")
        or effects.get("benefit")
        or effects.get("benefits")
        or {}
    )

    if isinstance(grants, list):
        grants = {"type": "skill_choice", "skills": grants}
    if not isinstance(grants, dict):
        grants = {}

    raw_skills = (
        grants.get("skills")
        or grants.get("skill_keys")
        or grants.get("choices")
        or grants.get("allowed_skills")
        or grants.get("eligible_skills")
        or []
    )

    if isinstance(raw_skills, str):
        raw_skills = [raw_skills]
    if not isinstance(raw_skills, list):
        raw_skills = []

    skill_keys: list[str] = []
    for item in raw_skills:
        if isinstance(item, str):
            key = item
        elif isinstance(item, dict):
            key = item.get("skill_key") or item.get("key") or item.get("skill")
        else:
            key = None

        if key and str(key) not in skill_keys:
            skill_keys.append(str(key))

    return {
        "type": grants.get("type") or ("skill_choice" if skill_keys else "manual_skill_choice"),
        "count": int(grants.get("count") or 1),
        "skill_keys": skill_keys,
        "reason_label": grants.get("reason_label") or "Trait Benefit",
        "raw": grants,
    }


@router.get("/staff/trait-benefits/options")
def staff_trait_benefit_options(actor_discord_id: int | None = Depends(actor_from_header)):
    require_staff(actor_discord_id)

    sb = get_supabase()
    gid = get_guild_id()

    characters = sb_data(
        sb.table("characters")
        .select("character_id,name,user_id,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .order("name", desc=False)
        .limit(1000)
        .execute()
    ) or []

    traits = sb_data(
        sb.table("traits")
        .select("trait_id,slug,name,tier,cost,category,description,effects_json,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .order("tier", desc=False)
        .order("name", desc=False)
        .limit(1000)
        .execute()
    ) or []

    skills = sb_data(
        sb.table("skill_definitions")
        .select("skill_key,name,tree,tier,cost,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .order("tree", desc=False)
        .order("tier", desc=False)
        .order("name", desc=False)
        .limit(2000)
        .execute()
    ) or []

    trait_options = []
    for trait in traits:
        trait_options.append({
            **trait,
            "grant_config": _trait_grant_config(trait),
        })

    return {"characters": characters, "traits": trait_options, "skills": skills}


@router.post("/staff/trait-benefits/apply")
def apply_staff_trait_benefit(
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    staff_id = actor_discord_id
    require_staff(staff_id)

    character_id = str(payload.get("character_id") or "").strip()
    trait_slug = str(payload.get("trait_slug") or payload.get("slug") or "").strip()
    trait_id = str(payload.get("trait_id") or "").strip()
    skill_key = str(payload.get("skill_key") or "").strip()
    reason = str(payload.get("reason") or "").strip()

    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC first.")
    if not trait_slug and not trait_id:
        raise HTTPException(status_code=400, detail="Choose a trait/origin first.")
    if not skill_key:
        raise HTTPException(status_code=400, detail="Choose the free skill to grant.")

    sb = get_supabase()
    gid = get_guild_id()

    character_rows = sb_data(
        sb.table("characters")
        .select("character_id,name,user_id,guild_id,is_active")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .limit(1)
        .execute()
    ) or []
    if not character_rows:
        raise HTTPException(status_code=404, detail="Character not found.")

    character = character_rows[0]

    trait_query = (
        sb.table("traits")
        .select("trait_id,slug,name,tier,cost,category,description,effects_json,is_active")
        .eq("guild_id", gid)
        .limit(1)
    )
    if trait_id:
        trait_query = trait_query.eq("trait_id", trait_id)
    else:
        trait_query = trait_query.eq("slug", trait_slug)

    trait_rows = sb_data(trait_query.execute()) or []
    if not trait_rows:
        raise HTTPException(status_code=404, detail="Trait/origin not found.")

    trait = trait_rows[0]
    grant_config = _trait_grant_config(trait)
    allowed_skill_keys = grant_config.get("skill_keys") or []

    if allowed_skill_keys and skill_key not in allowed_skill_keys:
        raise HTTPException(status_code=400, detail="That skill is not listed as an eligible benefit for this trait.")

    skill_rows = sb_data(
        sb.table("skill_definitions")
        .select("skill_key,name,tree,tier,cost,is_active")
        .eq("guild_id", gid)
        .eq("skill_key", skill_key)
        .limit(1)
        .execute()
    ) or []
    if not skill_rows:
        raise HTTPException(status_code=404, detail="Skill not found.")

    skill = skill_rows[0]
    if skill.get("is_active") is False:
        raise HTTPException(status_code=400, detail="Cannot grant an inactive skill.")

    existing_rows = sb_data(
        sb.table("oc_skills")
        .select("skill_key")
        .eq("guild_id", gid)
        .eq("character_id", character_id)
        .eq("skill_key", skill_key)
        .limit(1)
        .execute()
    ) or []

    if existing_rows:
        return {
            "ok": True,
            "already_owned": True,
            "message": f"{character.get('name') or 'This OC'} already owns {skill.get('name') or skill_key}.",
            "character": character,
            "trait": trait,
            "skill": skill,
        }

    note = reason or f"Granted from {trait.get('name') or trait.get('slug') or 'trait'} trait benefit."

    grant_rows = sb_data(
        sb.table("oc_skills")
        .insert({
            "guild_id": gid,
            "character_id": character_id,
            "skill_key": skill_key,
            "acquired_via": "xp",
            "xp_cost_paid": 0,
            "actor_discord_id": int(staff_id),
            "notes": note,
        })
        .execute()
    ) or []

    grant = grant_rows[0] if grant_rows else {
        "guild_id": gid,
        "character_id": character_id,
        "skill_key": skill_key,
        "acquired_via": "xp",
        "xp_cost_paid": 0,
        "actor_discord_id": int(staff_id),
        "notes": note,
    }

    try:
        sb.table("activity_log").insert({
            "guild_id": gid,
            "event_type": "trait_benefit_granted",
            "label": f"Trait benefit granted: {skill.get('name') or skill_key}",
            "status": "approved",
            "actor_discord_id": int(staff_id),
            "character_id": character_id,
            "character_name": character.get("name"),
            "amount": 0,
            "note": note,
            "source": "staff_trait_benefit",
            "details": {
                "trait_id": trait.get("trait_id"),
                "trait_slug": trait.get("slug"),
                "trait_name": trait.get("name"),
                "skill_key": skill_key,
                "skill_name": skill.get("name"),
                "xp_cost_paid": 0,
            },
        }).execute()
    except Exception:
        pass

    try:
        send_staff_activity_webhook(
            title="Trait Benefit Granted",
            description=note,
            event_type="trait_benefit_granted",
            status="approved",
            actor_id=staff_id,
            character_id=character_id,
            character_name=character.get("name"),
            details={
                "trait": trait.get("name") or trait.get("slug"),
                "skill": skill.get("name") or skill_key,
                "xp_cost_paid": 0,
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "already_owned": False,
        "message": f"Granted {skill.get('name') or skill_key} to {character.get('name') or 'OC'} from {trait.get('name') or 'trait'} benefit.",
        "grant": grant,
        "character": character,
        "trait": trait,
        "skill": skill,
    }
