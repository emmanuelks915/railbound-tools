from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from postgrest.exceptions import APIError

from app.security import actor_from_header
from app.permissions import require_actor
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase, raise_clean_api_error

router = APIRouter(prefix="/api/rp", tags=["rp"])


def _discord_thread_url(guild_id: int, thread_id: int | str | None) -> str | None:
    if not thread_id:
        return None
    return f"https://discord.com/channels/{guild_id}/{thread_id}"


def _discord_message_url(
    guild_id: int,
    thread_id: int | str | None,
    message_id: int | str | None,
) -> str | None:
    if not thread_id or not message_id:
        return None
    return f"https://discord.com/channels/{guild_id}/{thread_id}/{message_id}"


def _is_open_status(status: str | None) -> bool:
    normalized = str(status or "").lower().strip()
    return normalized in {"open", "active", "ongoing", "in_progress"}


@router.get("/me")
def my_rp_hub(
    character_id: UUID | None = Query(default=None),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    try:
        character_query = (
            sb.table("characters")
            .select("character_id,name,user_id,is_active,sheet_url")
            .eq("guild_id", gid)
            .eq("user_id", actor)
            .order("name", desc=False)
            .limit(250)
        )

        if character_id is not None:
            character_query = character_query.eq("character_id", str(character_id))

        character_res = character_query.execute()
    except APIError as e:
        raise_clean_api_error(e)

    characters = sb_data(character_res) or []
    character_ids = [str(c["character_id"]) for c in characters]

    if not character_ids:
        return {
            "characters": [],
            "active_scenes": [],
            "closed_scenes": [],
            "xp_claims": [],
            "recent_posts": [],
            "totals": {
                "scene_count": 0,
                "active_scene_count": 0,
                "closed_scene_count": 0,
                "post_count": 0,
                "word_count": 0,
                "estimated_xp": 0,
                "approved_xp": 0,
            },
        }

    try:
        participant_res = (
            sb.table("rp_scene_participants")
            .select("*")
            .eq("user_id", actor)
            .in_("character_id", character_ids)
            .order("joined_at", desc=True)
            .limit(500)
            .execute()
        )
    except APIError as e:
        raise_clean_api_error(e)

    participants = sb_data(participant_res) or []
    scene_ids = sorted({str(p["scene_id"]) for p in participants if p.get("scene_id")})

    scenes: list[dict[str, Any]] = []
    if scene_ids:
        try:
            scene_res = (
                sb.table("rp_scenes")
                .select("*")
                .eq("guild_id", gid)
                .in_("scene_id", scene_ids)
                .order("updated_at", desc=True)
                .limit(500)
                .execute()
            )
        except APIError as e:
            raise_clean_api_error(e)

        scenes = sb_data(scene_res) or []

    try:
        post_query = (
            sb.table("rp_posts")
            .select("*")
            .eq("guild_id", gid)
            .eq("user_id", actor)
            .in_("character_id", character_ids)
            .order("posted_at", desc=True)
            .limit(1000)
        )

        if scene_ids:
            post_query = post_query.in_("scene_id", scene_ids)

        post_res = post_query.execute()
    except APIError as e:
        raise_clean_api_error(e)

    posts = sb_data(post_res) or []

    try:
        claim_res = (
            sb.table("rp_xp_claims")
            .select("*")
            .eq("guild_id", gid)
            .eq("user_id", actor)
            .in_("character_id", character_ids)
            .order("created_at", desc=True)
            .limit(250)
            .execute()
        )
    except APIError as e:
        raise_clean_api_error(e)

    claims = sb_data(claim_res) or []

    event_ids = sorted({str(scene["event_id"]) for scene in scenes if scene.get("event_id")})
    events_by_id: dict[str, dict[str, Any]] = {}

    if event_ids:
        try:
            event_res = (
                sb.table("rp_events")
                .select("event_id,title,status,xp_eligible,channel_id,opened_at,closed_at")
                .eq("guild_id", gid)
                .in_("event_id", event_ids)
                .execute()
            )
            events = sb_data(event_res) or []
            events_by_id = {str(event["event_id"]): event for event in events}
        except APIError as e:
            raise_clean_api_error(e)

    participants_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for participant in participants:
        participants_by_scene[str(participant["scene_id"])].append(participant)

    posts_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for post in posts:
        posts_by_scene[str(post["scene_id"])].append(post)

    claims_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        if claim.get("scene_id"):
            claims_by_scene[str(claim["scene_id"])].append(claim)

    def serialize_scene(scene: dict[str, Any]) -> dict[str, Any]:
        sid = str(scene["scene_id"])
        scene_posts = posts_by_scene.get(sid, [])
        scene_participants = participants_by_scene.get(sid, [])
        scene_claims = claims_by_scene.get(sid, [])

        my_word_count = sum(int(post.get("word_count") or 0) for post in scene_posts)
        my_post_count = len(scene_posts)
        latest_post = scene_posts[0] if scene_posts else None

        event = None
        if scene.get("event_id"):
            event = events_by_id.get(str(scene["event_id"]))

        return {
            **scene,
            "discord_url": _discord_thread_url(gid, scene.get("thread_id")),
            "event": event,
            "participants": scene_participants,
            "my_post_count": my_post_count,
            "my_word_count": my_word_count,
            "latest_post": {
                **latest_post,
                "discord_url": _discord_message_url(
                    gid,
                    latest_post.get("thread_id") if latest_post else None,
                    latest_post.get("message_id") if latest_post else None,
                ),
            }
            if latest_post
            else None,
            "claim_count": len(scene_claims),
            "latest_claim": scene_claims[0] if scene_claims else None,
        }

    serialized_scenes = [serialize_scene(scene) for scene in scenes]
    active_scenes = [scene for scene in serialized_scenes if _is_open_status(scene.get("status"))]
    closed_scenes = [scene for scene in serialized_scenes if not _is_open_status(scene.get("status"))]

    serialized_posts = [
        {
            **post,
            "discord_url": _discord_message_url(gid, post.get("thread_id"), post.get("message_id")),
        }
        for post in posts[:25]
    ]

    serialized_claims = []
    for claim in claims:
        claim_scene = None

        if claim.get("scene_id"):
            claim_scene = next(
                (scene for scene in serialized_scenes if str(scene["scene_id"]) == str(claim["scene_id"])),
                None,
            )

        serialized_claims.append(
            {
                **claim,
                "scene": {
                    "scene_id": claim_scene.get("scene_id"),
                    "title": claim_scene.get("title"),
                    "discord_url": claim_scene.get("discord_url"),
                }
                if claim_scene
                else None,
            }
        )

    totals = {
        "scene_count": len(serialized_scenes),
        "active_scene_count": len(active_scenes),
        "closed_scene_count": len(closed_scenes),
        "post_count": len(posts),
        "word_count": sum(int(post.get("word_count") or 0) for post in posts),
        "estimated_xp": sum(int(claim.get("estimated_xp") or 0) for claim in claims),
        "approved_xp": sum(
            int(claim.get("approved_xp") or 0)
            for claim in claims
            if claim.get("approved_xp") is not None
        ),
    }

    return {
        "characters": characters,
        "active_scenes": active_scenes,
        "closed_scenes": closed_scenes,
        "xp_claims": serialized_claims,
        "recent_posts": serialized_posts,
        "totals": totals,
    }
