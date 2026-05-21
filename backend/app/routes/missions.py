
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/missions", tags=["missions"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _require_staff(actor_discord_id: int | None) -> None:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")
    if not is_staff(int(actor_discord_id)):
        raise HTTPException(status_code=403, detail="Staff only.")


def _clean_str(value: Any, max_len: int = 500) -> str:
    return str(value or "").strip()[:max_len]


def _list_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _character_for_actor(sb, character_id: str, actor_discord_id: int | None) -> dict[str, Any]:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    rows = _as_list(
        sb.table("characters")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .limit(1)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="OC not found.")

    character = rows[0]
    owner_id = str(character.get("user_id") or character.get("discord_id") or "")
    if owner_id != str(actor_discord_id) and not is_staff(int(actor_discord_id)):
        raise HTTPException(status_code=403, detail="You can only sign up your own OC.")

    return character


def _core_bst(sb, character_id: str) -> int:
    rows = _safe_rows(
        sb.table("oc_stats")
        .select("stat_key,stat_value")
        .eq("guild_id", get_guild_id())
        .eq("character_id", character_id)
        .in_("stat_key", ["strength", "dexterity", "stamina", "magic_affinity", "mana"])
        .limit(100)
    )
    return sum(int(row.get("stat_value") or 0) for row in rows)


def _mission(sb, mission_id: str) -> dict[str, Any]:
    rows = _as_list(
        sb.table("missions")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("mission_id", mission_id)
        .limit(1)
        .execute()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Mission not found.")
    return rows[0]


@router.get("")
def list_missions(actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    rows = _as_list(
        sb.table("missions")
        .select("*")
        .eq("guild_id", get_guild_id())
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )

    if actor_discord_id is None or not is_staff(int(actor_discord_id)):
        rows = [row for row in rows if str(row.get("status") or "open") == "open"]

    return {"missions": rows}


@router.post("")
def create_mission(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    _require_staff(actor_discord_id)
    sb = get_supabase()

    title = _clean_str(payload.get("title"), 160)
    if not title:
        raise HTTPException(status_code=400, detail="Mission title is required.")

    policy = _clean_str(payload.get("guild_policy") or "open", 24).lower()
    if policy not in {"open", "priority", "restricted"}:
        policy = "open"

    try:
        min_bst = int(payload.get("min_bst")) if str(payload.get("min_bst") or "").strip() else None
        max_bst = int(payload.get("max_bst")) if str(payload.get("max_bst") or "").strip() else None
        party_size = int(payload.get("party_size") or 0)
        priority_window_hours = int(payload.get("priority_window_hours") or 24)
    except Exception:
        raise HTTPException(status_code=400, detail="BST, party size, and priority window must be whole numbers.")

    mission = {
        "guild_id": get_guild_id(),
        "title": title,
        "status": _clean_str(payload.get("status") or "open", 24).lower(),
        "description": _clean_str(payload.get("description"), 4000),
        "reward": _clean_str(payload.get("reward"), 1000),
        "location": _clean_str(payload.get("location"), 160),
        "difficulty": _clean_str(payload.get("difficulty"), 80),
        "party_size": party_size,
        "min_bst": min_bst,
        "max_bst": max_bst,
        "guild_policy": policy,
        "priority_guilds": _list_text(payload.get("priority_guilds")),
        "restricted_guilds": _list_text(payload.get("restricted_guilds")),
        "bonus_pay": _clean_str(payload.get("bonus_pay"), 1000),
        "priority_window_hours": priority_window_hours,
        "created_by_discord_id": int(actor_discord_id),
    }

    rows = _as_list(sb.table("missions").insert(mission).execute())
    return {"mission": rows[0] if rows else mission, "message": "Mission created."}


@router.patch("/{mission_id}")
def update_mission(mission_id: str, payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    _require_staff(actor_discord_id)
    sb = get_supabase()

    allowed = {
        "title", "status", "description", "reward", "location", "difficulty",
        "party_size", "min_bst", "max_bst", "guild_policy", "priority_guilds",
        "restricted_guilds", "bonus_pay", "priority_window_hours",
    }
    update: dict[str, Any] = {}

    for key in allowed:
        if key not in payload:
            continue
        value = payload.get(key)
        if key in {"priority_guilds", "restricted_guilds"}:
            update[key] = _list_text(value)
        elif key in {"party_size", "min_bst", "max_bst", "priority_window_hours"}:
            update[key] = int(value) if str(value or "").strip() else None
        else:
            update[key] = _clean_str(value, 4000)

    if not update:
        raise HTTPException(status_code=400, detail="No mission fields provided.")

    rows = _as_list(
        sb.table("missions")
        .update(update)
        .eq("guild_id", get_guild_id())
        .eq("mission_id", mission_id)
        .execute()
    )
    return {"mission": rows[0] if rows else {**update, "mission_id": mission_id}, "message": "Mission updated."}


@router.post("/{mission_id}/signup")
def signup_for_mission(mission_id: str, payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    sb = get_supabase()
    mission = _mission(sb, mission_id)

    if str(mission.get("status") or "open") != "open":
        raise HTTPException(status_code=400, detail="This mission is not open for signups.")

    character_id = _clean_str(payload.get("character_id"), 80)
    character = _character_for_actor(sb, character_id, actor_discord_id)

    guild_name = _clean_str(payload.get("guild_name") or payload.get("guild"), 120)
    if not guild_name:
        raise HTTPException(status_code=400, detail="Guild is required for mission signup.")

    bst = int(payload.get("bst") or _core_bst(sb, character_id) or 0)
    min_bst = mission.get("min_bst")
    max_bst = mission.get("max_bst")

    if min_bst is not None and bst < int(min_bst):
        raise HTTPException(status_code=400, detail=f"BST too low. This mission requires at least {min_bst}.")
    if max_bst is not None and bst > int(max_bst):
        raise HTTPException(status_code=400, detail=f"BST too high. This mission allows at most {max_bst}.")

    policy = str(mission.get("guild_policy") or "open").lower()
    restricted = [str(g).lower() for g in (mission.get("restricted_guilds") or [])]
    priority = [str(g).lower() for g in (mission.get("priority_guilds") or [])]
    guild_norm = guild_name.lower()

    placement_group = "general"
    if policy == "restricted":
        if guild_norm not in restricted and guild_norm not in priority:
            raise HTTPException(status_code=400, detail="This mission is restricted to specific guilds.")
        placement_group = "restricted"
    elif policy == "priority" and guild_norm in priority:
        placement_group = "priority"

    existing = _safe_rows(
        sb.table("mission_signups")
        .select("signup_id")
        .eq("guild_id", get_guild_id())
        .eq("mission_id", mission_id)
        .eq("character_id", character_id)
        .limit(1)
    )
    if existing:
        raise HTTPException(status_code=400, detail="This OC is already signed up for this mission.")

    row = {
        "guild_id": get_guild_id(),
        "mission_id": mission_id,
        "character_id": character_id,
        "character_name": character.get("name"),
        "player_discord_id": int(actor_discord_id),
        "guild_name": guild_name,
        "bst": bst,
        "other_active_missions": _clean_str(payload.get("other_active_missions"), 1000),
        "note": _clean_str(payload.get("note"), 1000),
        "placement_group": placement_group,
        "status": "pending",
    }

    rows = _as_list(sb.table("mission_signups").insert(row).execute())
    return {"signup": rows[0] if rows else row, "message": "Mission signup submitted."}


@router.get("/{mission_id}/signups")
def mission_signups(mission_id: str, actor_discord_id: int | None = Depends(actor_from_header)):
    _require_staff(actor_discord_id)
    sb = get_supabase()
    rows = _as_list(
        sb.table("mission_signups")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("mission_id", mission_id)
        .order("created_at", desc=False)
        .limit(500)
        .execute()
    )
    return {"signups": rows}


@router.patch("/signups/{signup_id}")
def update_signup(signup_id: str, payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    _require_staff(actor_discord_id)
    sb = get_supabase()

    status = _clean_str(payload.get("status") or "", 40).lower()
    if status not in {"pending", "accepted", "waitlisted", "denied", "withdrawn"}:
        raise HTTPException(status_code=400, detail="Invalid signup status.")

    update = {
        "status": status,
        "staff_note": _clean_str(payload.get("staff_note"), 1000),
        "reviewed_by_discord_id": int(actor_discord_id),
    }

    rows = _as_list(
        sb.table("mission_signups")
        .update(update)
        .eq("guild_id", get_guild_id())
        .eq("signup_id", signup_id)
        .execute()
    )
    return {"signup": rows[0] if rows else {"signup_id": signup_id, **update}, "message": "Mission signup updated."}
