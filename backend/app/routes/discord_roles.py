from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.config import get_settings
from app.security import actor_from_header, require_staff
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/staff/discord-roles", tags=["staff-discord-roles"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _staff(actor_discord_id: int | None) -> int:
    staff_id = int(actor_discord_id) if actor_discord_id is not None else None
    require_staff(staff_id)
    return int(staff_id)


def _bot_token() -> str:
    token = getattr(get_settings(), "discord_bot_token", "") or ""
    token = token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="DISCORD_BOT_TOKEN is not configured on the backend, so Keystone cannot assign Discord roles yet.")
    return token


def _discord_request(method: str, path: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    url = f"https://discord.com/api/v10{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=400, detail=f"Discord role request failed: {exc.code} {detail}")


def _character(sb, character_id: str) -> dict[str, Any]:
    rows = _as_list(sb.table("characters").select("character_id,name,user_id,guild_id,is_active").eq("guild_id", get_guild_id()).eq("character_id", character_id).limit(1).execute())
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found.")
    return rows[0]


def _owned_trait_slugs(sb, character_id: str) -> set[str]:
    gid = get_guild_id()
    trait_ids: set[str] = set()
    for table in ("character_traits", "oc_traits"):
        rows = _safe_rows(sb.table(table).select("trait_id").eq("guild_id", gid).eq("character_id", character_id).limit(1000))
        for row in rows:
            if row.get("trait_id"):
                trait_ids.add(str(row["trait_id"]))
    if not trait_ids:
        return set()
    traits = _safe_rows(sb.table("traits").select("trait_id,slug").eq("guild_id", gid).in_("trait_id", list(trait_ids)).limit(1000))
    return {str(row.get("slug")) for row in traits if row.get("slug")}


def _log(sb, event_type: str, label: str, staff_id: int, character: dict[str, Any], details: dict[str, Any]) -> None:
    try:
        sb.table("activity_log").insert({
            "guild_id": get_guild_id(),
            "event_type": event_type,
            "label": label,
            "status": "approved",
            "actor_discord_id": staff_id,
            "character_id": character.get("character_id"),
            "character_name": character.get("name"),
            "source": "discord_role_sync",
            "details": details,
        }).execute()
    except Exception:
        pass


@router.get("/options")
def discord_role_options(actor_discord_id: int | None = Depends(actor_from_header)):
    _staff(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()
    characters = _as_list(sb.table("characters").select("character_id,name,user_id,is_active").eq("guild_id", gid).eq("is_active", True).order("name", desc=False).limit(1000).execute())
    mappings = _safe_rows(sb.table("discord_role_mappings").select("*").eq("guild_id", gid).eq("is_active", True).order("label", desc=False).limit(1000))
    return {"characters": characters, "mappings": mappings, "bot_configured": bool((getattr(get_settings(), "discord_bot_token", "") or "").strip())}


@router.post("/sync-character")
def sync_character_roles(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()
    token = _bot_token()
    character_id = str(payload.get("character_id") or "").strip()
    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC.")
    character = _character(sb, character_id)
    user_id = str(character.get("user_id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="This OC does not have a Discord user_id.")
    owned_slugs = _owned_trait_slugs(sb, character_id)
    mappings = _safe_rows(sb.table("discord_role_mappings").select("*").eq("guild_id", gid).eq("is_active", True).limit(1000))
    matched = []
    for mapping in mappings:
        source_type = str(mapping.get("source_type") or "").strip().lower()
        source_key = str(mapping.get("source_key") or "").strip()
        if source_type == "trait_slug" and source_key in owned_slugs:
            matched.append(mapping)
    if not matched:
        return {"ok": True, "message": f"No mapped lore roles found for {character.get('name') or 'OC'}.", "applied_roles": [], "owned_trait_slugs": sorted(owned_slugs)}
    applied = []
    for mapping in matched:
        role_id = str(mapping.get("role_id") or "").strip()
        if not role_id:
            continue
        _discord_request("PUT", f"/guilds/{gid}/members/{user_id}/roles/{role_id}", token)
        applied.append(mapping)
    _log(sb, "discord_roles_synced", "Discord lore roles synced", staff_id, character, {"applied_role_ids": [row.get("role_id") for row in applied], "owned_trait_slugs": sorted(owned_slugs)})
    return {"ok": True, "message": f"Synced {len(applied)} lore role(s) for {character.get('name') or 'OC'}.", "applied_roles": applied, "owned_trait_slugs": sorted(owned_slugs)}


@router.post("/assign")
def assign_role(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()
    token = _bot_token()
    character_id = str(payload.get("character_id") or "").strip()
    role_id = str(payload.get("role_id") or "").strip()
    reason = str(payload.get("reason") or "Manual staff lore role assignment.").strip()
    if not character_id:
        raise HTTPException(status_code=400, detail="Choose an OC.")
    if not role_id:
        raise HTTPException(status_code=400, detail="Choose a Discord role.")
    character = _character(sb, character_id)
    user_id = str(character.get("user_id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="This OC does not have a Discord user_id.")
    _discord_request("PUT", f"/guilds/{gid}/members/{user_id}/roles/{role_id}", token)
    _log(sb, "discord_role_assigned", "Discord role assigned", staff_id, character, {"role_id": role_id, "reason": reason})
    return {"ok": True, "message": f"Assigned Discord role {role_id} to {character.get('name') or 'OC'}."}

@router.post("/sync-all")
def sync_all_city_lore_roles(payload: dict[str, Any] = Body(default={}), actor_discord_id: int | None = Depends(actor_from_header)):
    staff_id = _staff(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()
    token = _bot_token()

    dry_run = bool(payload.get("dry_run") or False)

    mappings = _safe_rows(
        sb.table("discord_role_mappings")
        .select("*")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .limit(1000)
    )

    trait_mappings = [
        row for row in mappings
        if str(row.get("source_type") or "").strip().lower() == "trait_slug"
        and row.get("source_key")
        and row.get("role_id")
    ]

    characters = _as_list(
        sb.table("characters")
        .select("character_id,name,user_id,guild_id,is_active")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .limit(2500)
        .execute()
    )

    results: list[dict[str, Any]] = []
    applied_count = 0
    skipped_count = 0
    error_count = 0

    for character in characters:
        character_id = str(character.get("character_id") or "")
        user_id = str(character.get("user_id") or "").strip()
        name = character.get("name") or character_id

        if not character_id or not user_id:
            skipped_count += 1
            results.append({
                "character_id": character_id,
                "character_name": name,
                "status": "skipped",
                "reason": "Missing character_id or user_id.",
                "roles": [],
            })
            continue

        try:
            owned_slugs = _owned_trait_slugs(sb, character_id)
            matched = [
                mapping for mapping in trait_mappings
                if str(mapping.get("source_key") or "") in owned_slugs
            ]

            if not matched:
                skipped_count += 1
                results.append({
                    "character_id": character_id,
                    "character_name": name,
                    "status": "skipped",
                    "reason": "No active mapped lore roles matched this OC.",
                    "roles": [],
                    "owned_trait_slugs": sorted(owned_slugs),
                })
                continue

            applied_roles = []
            for mapping in matched:
                role_id = str(mapping.get("role_id") or "").strip()
                if not role_id:
                    continue
                if not dry_run:
                    _discord_request("PUT", f"/guilds/{gid}/members/{user_id}/roles/{role_id}", token)
                applied_roles.append({
                    "role_id": role_id,
                    "label": mapping.get("label"),
                    "source_key": mapping.get("source_key"),
                })

            applied_count += len(applied_roles)
            results.append({
                "character_id": character_id,
                "character_name": name,
                "status": "would_apply" if dry_run else "applied",
                "roles": applied_roles,
                "owned_trait_slugs": sorted(owned_slugs),
            })

        except Exception as exc:
            error_count += 1
            results.append({
                "character_id": character_id,
                "character_name": name,
                "status": "error",
                "reason": str(exc),
                "roles": [],
            })

    try:
        sb.table("activity_log").insert({
            "guild_id": gid,
            "event_type": "discord_lore_roles_backfilled",
            "label": "Discord lore roles backfilled",
            "status": "approved" if error_count == 0 else "partial",
            "actor_discord_id": staff_id,
            "source": "discord_role_sync",
            "details": {
                "dry_run": dry_run,
                "characters_checked": len(characters),
                "roles_applied": applied_count,
                "characters_skipped": skipped_count,
                "errors": error_count,
            },
        }).execute()
    except Exception:
        pass

    return {
        "ok": error_count == 0,
        "message": (
            f"Dry run complete: {applied_count} lore role assignment(s) would be applied."
            if dry_run
            else f"Backfill complete: {applied_count} lore role assignment(s) applied."
        ),
        "dry_run": dry_run,
        "characters_checked": len(characters),
        "roles_applied": applied_count,
        "characters_skipped": skipped_count,
        "errors": error_count,
        "results": results,
    }
