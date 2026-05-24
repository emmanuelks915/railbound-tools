from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/staff/source-beast-skills", tags=["staff-source-beast-skills"])

VALID_TYPES = {"combat", "mount", "utility"}


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _require_staff(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")
    if not is_staff(int(actor_discord_id)):
        raise HTTPException(status_code=403, detail="Staff only.")
    return int(actor_discord_id)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or "source_beast_skill"


def _json_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _payload_to_row(payload: dict[str, Any], actor_id: int, existing_key: str | None = None) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Skill name is required.")

    skill_key = str(payload.get("skill_key") or existing_key or "").strip()
    if not skill_key:
        skill_key = f"beast_{_slugify(name)}"
    else:
        skill_key = _slugify(skill_key)

    beast_skill_type = str(payload.get("beast_skill_type") or payload.get("type") or "utility").strip().lower()
    if beast_skill_type == "support":
        beast_skill_type = "utility"
    if beast_skill_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Beast skill type must be combat, mount, or utility.")

    try:
        tier = int(payload.get("tier") if payload.get("tier") is not None else 1)
        cost = int(payload.get("cost") if payload.get("cost") is not None else 0)
        sort_order = int(payload.get("sort_order") if payload.get("sort_order") is not None else 0)
    except Exception:
        raise HTTPException(status_code=400, detail="Tier, cost, and display order must be whole numbers.")

    if tier < 0 or tier > 3:
        raise HTTPException(status_code=400, detail="Tier must be between 0 and 3.")
    if cost < 0:
        raise HTTPException(status_code=400, detail="Cost cannot be negative.")

    return {
        "guild_id": get_guild_id(),
        "skill_key": skill_key,
        "name": name[:180],
        "beast_skill_type": beast_skill_type,
        "tier": tier,
        "cost": cost,
        "action_type": str(payload.get("action_type") or "").strip()[:80],
        "prerequisites": _json_list(payload.get("prerequisites")),
        "chain": str(payload.get("chain") or "").strip()[:500],
        "effects": str(payload.get("effects") or "").strip()[:4000],
        "description": str(payload.get("description") or "").strip()[:6000],
        "source_label": str(payload.get("source_label") or "Source Beast Skill Catalog").strip()[:180],
        "sort_order": sort_order,
        "is_active": bool(payload.get("is_active", True)),
        "is_purchasable": bool(payload.get("is_purchasable", False)),
        "updated_by_discord_id": actor_id,
    }


@router.get("")
def list_source_beast_skills(actor_discord_id: int | None = Depends(actor_from_header)):
    _require_staff(actor_discord_id)
    sb = get_supabase()
    rows = _as_list(
        sb.table("source_beast_skill_definitions")
        .select("*")
        .eq("guild_id", get_guild_id())
        .order("beast_skill_type", desc=False)
        .order("tier", desc=False)
        .order("sort_order", desc=False)
        .order("name", desc=False)
        .limit(500)
        .execute()
    )
    return {"skills": rows}


@router.post("")
def create_source_beast_skill(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    actor_id = _require_staff(actor_discord_id)
    sb = get_supabase()
    row = _payload_to_row(payload, actor_id)
    row["created_by_discord_id"] = actor_id
    try:
        rows = _as_list(sb.table("source_beast_skill_definitions").insert(row).execute())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not create Beast Skill. It may already exist. {exc}")
    return {"message": "Source Beast Skill created.", "skill": rows[0] if rows else row}


@router.put("/{skill_key}")
def update_source_beast_skill(skill_key: str, payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    actor_id = _require_staff(actor_discord_id)
    sb = get_supabase()
    normalized_key = _slugify(skill_key)
    row = _payload_to_row(payload, actor_id, existing_key=normalized_key)
    rows = _as_list(
        sb.table("source_beast_skill_definitions")
        .update(row)
        .eq("guild_id", get_guild_id())
        .eq("skill_key", normalized_key)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source Beast Skill not found.")
    return {"message": "Source Beast Skill updated.", "skill": rows[0]}


@router.patch("/{skill_key}/toggle")
def toggle_source_beast_skill(skill_key: str, payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    actor_id = _require_staff(actor_discord_id)
    sb = get_supabase()
    update: dict[str, Any] = {"updated_by_discord_id": actor_id}
    if "is_active" in payload:
        update["is_active"] = bool(payload.get("is_active"))
    if "is_purchasable" in payload:
        update["is_purchasable"] = bool(payload.get("is_purchasable"))
    if len(update) == 1:
        raise HTTPException(status_code=400, detail="No toggle fields provided.")
    rows = _as_list(
        sb.table("source_beast_skill_definitions")
        .update(update)
        .eq("guild_id", get_guild_id())
        .eq("skill_key", _slugify(skill_key))
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source Beast Skill not found.")
    return {"message": "Source Beast Skill updated.", "skill": rows[0]}


@router.delete("/{skill_key}")
def delete_source_beast_skill(skill_key: str, actor_discord_id: int | None = Depends(actor_from_header)):
    _require_staff(actor_discord_id)
    sb = get_supabase()
    normalized_key = _slugify(skill_key)
    rows = _as_list(
        sb.table("source_beast_skill_definitions")
        .delete()
        .eq("guild_id", get_guild_id())
        .eq("skill_key", normalized_key)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source Beast Skill not found.")
    return {"message": "Source Beast Skill deleted.", "skill_key": normalized_key}
