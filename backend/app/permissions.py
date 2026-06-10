from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.config import get_settings
from app.services import get_guild_id, sb_data


def is_staff(actor_discord_id: int | None) -> bool:
    return bool(actor_discord_id and actor_discord_id in get_settings().staff_ids)


def require_actor(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Missing X-Discord-Id header.")
    return int(actor_discord_id)


def character_owner_id(sb: Client, character_id: UUID | str) -> int | None:
    res = (
        sb.table("characters")
        .select("character_id,user_id")
        .eq("character_id", str(character_id))
        .limit(1)
        .execute()
    )
    rows = sb_data(res) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found.")
    raw = rows[0].get("user_id")
    if raw is None:
        return None
    s = str(raw).strip()
    return int(s) if s.isdigit() else None


def require_character_access(sb: Client, character_id: UUID | str, actor_discord_id: int | None) -> int:
    actor = require_actor(actor_discord_id)
    if is_staff(actor):
        return actor
    owner = character_owner_id(sb, character_id)
    if owner != actor:
        raise HTTPException(status_code=403, detail="You can only access your own OC.")
    return actor


def role_rank(role: str | None) -> int:
    r = (role or "").strip().upper()
    return {"OWNER": 3, "MANAGER": 2, "TELLER": 1, "MEMBER": 0}.get(r, 0)


def company_member_rank(sb: Client, company_id: str, actor_discord_id: int) -> int:
    res = (
        sb.table("company_members")
        .select("role")
        .eq("company_id", str(company_id))
        .eq("discord_id", int(actor_discord_id))
        .limit(1)
        .execute()
    )
    rows = sb_data(res) or []
    if not rows:
        return 0
    return role_rank(rows[0].get("role"))


def require_company_manager(sb: Client, company_id: str, actor_discord_id: int | None, *, min_rank: int = 2) -> int:
    actor = require_actor(actor_discord_id)
    if is_staff(actor):
        return actor
    rank = company_member_rank(sb, company_id, actor)
    if rank < min_rank:
        raise HTTPException(status_code=403, detail="You must be this shop's owner or manager.")
    return actor
