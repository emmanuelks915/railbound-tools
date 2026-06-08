from __future__ import annotations

from math import ceil
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException

from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/companions", tags=["companions"])

CORE_STATS = ["strength", "dexterity", "stamina", "magic_affinity", "mana"]

RULES = {
    "combat":  {"combat": 3, "mount": 2, "utility": 1, "own_type_skill_cap_per_tier": 3, "non_type_skill_cap_per_tier": 2},
    "mount":   {"combat": 1, "mount": 3, "utility": 2, "own_type_skill_cap_per_tier": 3, "non_type_skill_cap_per_tier": 2},
    "utility": {"combat": 2, "mount": 1, "utility": 3, "own_type_skill_cap_per_tier": 3, "non_type_skill_cap_per_tier": 2},
}

STAT_LABELS = {
    "strength": "Strength",
    "dexterity": "Dexterity",
    "stamina": "Stamina",
    "magic_affinity": "Magic Affinity",
    "mana": "Mana",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _rows(x: Any) -> list[dict[str, Any]]:
    r = sb_data(x) or []
    return r if isinstance(r, list) else []


def _safe(q: Any) -> list[dict[str, Any]]:
    try:
        return _rows(q.execute())
    except Exception:
        return []


def _require_login(actor_discord_id: int | None) -> int:
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")
    return int(actor_discord_id)


def _get_character(sb: Any, character_id: str) -> dict[str, Any]:
    rows = _safe(sb.table("characters").select("*").eq("character_id", character_id).limit(1))
    if not rows:
        raise HTTPException(status_code=404, detail="OC not found.")
    return rows[0]


def _can_access(character: dict[str, Any], actor: int) -> bool:
    if is_staff(actor):
        return True
    owner_keys = ("user_id", "discord_id", "owner_discord_id", "player_discord_id")
    return any(
        str(character.get(k)) == str(actor)
        for k in owner_keys
        if character.get(k) is not None
    )


def _get_traits(sb: Any, character_id: str, guild_id: int) -> list[dict[str, Any]]:
    owned: list[dict[str, Any]] = []
    for table in ("oc_traits", "character_traits"):
        owned += _safe(sb.table(table).select("*").eq("character_id", character_id).limit(300))

    ids = [str(r.get("trait_id")) for r in owned if r.get("trait_id")]
    slugs = [str(r.get(k)) for r in owned for k in ("slug", "trait_slug", "trait_key") if r.get(k)]

    catalog: list[dict[str, Any]] = []
    if ids:
        catalog += _safe(
            sb.table("traits").select("*").eq("guild_id", guild_id).in_("trait_id", ids).limit(300)
        )
    if slugs:
        catalog += _safe(
            sb.table("traits").select("*").eq("guild_id", guild_id).in_("slug", slugs).limit(300)
        )

    by_id = {str(r.get("trait_id")): r for r in catalog if r.get("trait_id")}
    by_slug = {str(r.get("slug")): r for r in catalog if r.get("slug")}

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for r in owned:
        source = by_id.get(str(r.get("trait_id"))) if r.get("trait_id") else None

        if not source:
            for k in ("slug", "trait_slug", "trait_key"):
                if r.get(k) and str(r.get(k)) in by_slug:
                    source = by_slug[str(r.get(k))]
                    break

        source = source or r
        slug = str(source.get("slug") or r.get("slug") or r.get("trait_slug") or r.get("trait_key") or "")
        name = str(source.get("name") or r.get("name") or r.get("trait_name") or slug or "")
        marker = slug or name

        if marker in seen:
            continue
        seen.add(marker)
        out.append({**source, "slug": slug, "name": name})

    return out


def _has_loyal_companion(traits: list[dict[str, Any]]) -> bool:
    for t in traits:
        slug = str(t.get("slug") or "").lower().replace("-", "_").replace(" ", "_")
        name = str(t.get("name") or "").lower()
        if "loyal_companion" in slug or "loyal companion" in name:
            return True
    return False


def _get_oc_stats(sb: Any, character_id: str) -> dict[str, int]:
    rows = _safe(
        sb.table("oc_stats")
        .select("stat_key,stat_value")
        .eq("character_id", character_id)
        .in_("stat_key", CORE_STATS)
        .limit(100)
    )
    stats = {k: 0 for k in CORE_STATS}
    for row in rows:
        key = str(row.get("stat_key") or "")
        if key in stats:
            stats[key] = int(row.get("stat_value") or 0)
    return stats


def _default_beast(character_id: str, guild_id: int) -> dict[str, Any]:
    return {
        "guild_id": guild_id,
        "character_id": character_id,
        "beast_name": "",
        "beast_type": "utility",
        "description": "",
        "image_url": "",
        "xp": 0,
        "base_strength": 5,
        "base_dexterity": 5,
        "base_stamina": 5,
        "base_magic_affinity": 5,
        "base_mana": 5,
        "current_skills": "",
        "notes": "",
    }


def _computed_stats(beast: dict[str, Any], oc_stats: dict[str, int]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in CORE_STATS:
        base = int(beast.get(f"base_{k}") or 5)
        modifier = ceil(int(oc_stats.get(k) or 0) * 0.10)
        out[k] = {"base": base, "modifier": modifier, "final": base + modifier}
    return out


def _safe_int(payload: dict[str, Any], key: str, default: int = 5) -> int:
    try:
        return max(0, int(payload.get(key, default)))
    except Exception:
        return default


def _get_wallet(sb: Any, character_id: str) -> dict[str, Any]:
    rows = _safe(
        sb.table("oc_xp_wallets")
        .select("available_xp,total_spent_xp")
        .eq("character_id", character_id)
        .limit(1)
    )
    return rows[0] if rows else {"available_xp": 0}


def _stat_xp_cost(current: int, target: int) -> int:
    if target <= current:
        return 0
    brackets = [(50, 1), (150, 2), (250, 4), (350, 6), (450, 8), (550, 10), (650, 12), (750, 14)]
    total = 0
    pos = current
    while pos < target:
        rate = 14
        next_ceil = target
        for bracket_ceil, cost in brackets:
            if pos < bracket_ceil:
                rate = cost
                next_ceil = min(bracket_ceil, target)
                break
        total += (next_ceil - pos) * rate
        pos = next_ceil
    return total


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("/beast-skills/catalog")
def list_beast_skills_catalog(actor_discord_id: int | None = Depends(actor_from_header)):
    """Public endpoint — returns all active purchasable beast skills for players."""
    _require_login(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    rows = _safe(
        sb.table("source_beast_skill_definitions")
        .select("*")
        .eq("guild_id", gid)
        .eq("is_active", True)
        .eq("is_purchasable", True)
        .order("beast_skill_type")
        .order("tier")
        .order("sort_order")
        .order("name")
        .limit(500)
    )
    return {"skills": rows}


@router.get("/eligibility")
def companion_eligibility(actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()

    if is_staff(actor):
        return {
            "eligible": True,
            "eligible_characters": [],
            "staff_visibility": True,
            "reason": "Staff can always access the Companion tab for Loyal Companion support.",
        }

    character_rows = _safe(
        sb.table("characters")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("user_id", str(actor))
        .limit(300)
    )

    if not character_rows:
        character_rows = _safe(
            sb.table("characters").select("*").eq("user_id", str(actor)).limit(300)
        )

    eligible_characters = []
    for character in character_rows:
        cid = str(character.get("character_id") or "")
        if not cid:
            continue
        guild_id = int(character.get("guild_id") or get_guild_id())
        traits = _get_traits(sb, cid, guild_id)
        if _has_loyal_companion(traits):
            eligible_characters.append({"character_id": cid, "name": character.get("name")})

    return {
        "eligible": bool(eligible_characters),
        "eligible_characters": eligible_characters,
    }


@router.get("/{character_id}")
def get_companion(character_id: UUID, actor_discord_id: int | None = Depends(actor_from_header)):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    cid = str(character_id)
    character = _get_character(sb, cid)

    if not _can_access(character, actor):
        raise HTTPException(status_code=403, detail="You can only view your own companion.")

    gid = int(character.get("guild_id") or get_guild_id())
    traits = _get_traits(sb, cid, gid)
    eligible = _has_loyal_companion(traits)

    beast_rows = _safe(sb.table("source_beasts").select("*").eq("character_id", cid).limit(1))
    beast = beast_rows[0] if beast_rows else _default_beast(cid, gid)

    oc_stats = _get_oc_stats(sb, cid)
    beast_type = str(beast.get("beast_type") or "utility")
    wallet = _get_wallet(sb, cid)

    beast_xp_spent = sum(
        int(x.get("cost") or 0)
        for x in _safe(
            sb.table("skill_purchase_requests")
            .select("cost")
            .eq("character_id", cid)
            .in_("source_label", ["Beast Skill", "Beast Stat"])
            .eq("status", "approved")
            .limit(500)
        )
    )

    return {
        "eligible": eligible,
        "character": {"character_id": cid, "name": character.get("name")},
        "loyal_companion_trait": next((t for t in traits if _has_loyal_companion([t])), None),
        "beast": beast,
        "oc_stats": oc_stats,
        "computed_stats": _computed_stats(beast, oc_stats),
        "type_rules": RULES.get(beast_type, RULES["utility"]),
        "allowed_types": ["combat", "mount", "utility"],
        "wallet": wallet,
        "beast_xp_spent": beast_xp_spent,
    }


@router.put("/{character_id}")
def save_companion(
    character_id: UUID,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    cid = str(character_id)
    character = _get_character(sb, cid)

    if not _can_access(character, actor):
        raise HTTPException(status_code=403, detail="You can only edit your own companion.")

    gid = int(character.get("guild_id") or get_guild_id())

    if not _has_loyal_companion(_get_traits(sb, cid, gid)):
        raise HTTPException(status_code=403, detail="This OC does not have the Loyal Companion trait.")

    beast_type = str(payload.get("beast_type") or "utility").lower().strip()
    if beast_type == "support":
        beast_type = "utility"
    if beast_type not in RULES:
        raise HTTPException(status_code=400, detail="Beast type must be combat, mount, or utility.")

    row = {
        "guild_id": gid,
        "character_id": cid,
        "beast_name": str(payload.get("beast_name") or "")[:160],
        "beast_type": beast_type,
        "description": str(payload.get("description") or "")[:4000],
        "image_url": str(payload.get("image_url") or "")[:1000],
        "xp": _safe_int(payload, "xp", 0),
        "base_strength": _safe_int(payload, "base_strength"),
        "base_dexterity": _safe_int(payload, "base_dexterity"),
        "base_stamina": _safe_int(payload, "base_stamina"),
        "base_magic_affinity": _safe_int(payload, "base_magic_affinity"),
        "base_mana": _safe_int(payload, "base_mana"),
        "current_skills": str(payload.get("current_skills") or "")[:4000],
        "notes": str(payload.get("notes") or "")[:4000],
    }

    try:
        rows = _rows(sb.table("source_beasts").upsert(row, on_conflict="character_id").execute())
    except Exception:
        exists = _safe(sb.table("source_beasts").select("character_id").eq("character_id", cid).limit(1))
        query = sb.table("source_beasts").update(row).eq("character_id", cid) if exists else sb.table("source_beasts").insert(row)
        rows = _rows(query.execute())

    saved = rows[0] if rows else row
    oc_stats = _get_oc_stats(sb, cid)

    return {
        "message": "Source Beast saved.",
        "beast": saved,
        "computed_stats": _computed_stats(saved, oc_stats),
        "type_rules": RULES.get(beast_type, RULES["utility"]),
    }


@router.post("/{character_id}/skill-request")
def request_beast_skill(
    character_id: UUID,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    cid = str(character_id)
    character = _get_character(sb, cid)

    if not _can_access(character, actor):
        raise HTTPException(status_code=403, detail="You can only request skills for your own companion.")

    gid = int(character.get("guild_id") or get_guild_id())

    if not _has_loyal_companion(_get_traits(sb, cid, gid)):
        raise HTTPException(status_code=403, detail="This OC does not have the Loyal Companion trait.")

    skill_key = str(payload.get("skill_key") or "").strip()
    if not skill_key:
        raise HTTPException(status_code=400, detail="skill_key is required.")

    skill_rows = _safe(
        sb.table("source_beast_skill_definitions")
        .select("*")
        .eq("guild_id", gid)
        .eq("skill_key", skill_key)
        .eq("is_active", True)
        .limit(1)
    )
    if not skill_rows:
        raise HTTPException(status_code=404, detail="Beast skill not found or not available.")

    skill = skill_rows[0]
    if not skill.get("is_purchasable"):
        raise HTTPException(status_code=400, detail="This beast skill is not yet available for purchase.")

    cost = int(skill.get("cost") or 0)

    # Prerequisite check
    raw_prereqs = skill.get("prerequisites") or []
    if isinstance(raw_prereqs, str):
        raw_prereqs = [p.strip() for p in raw_prereqs.split(",") if p.strip()]
    elif isinstance(raw_prereqs, list):
        raw_prereqs = [str(p).strip() for p in raw_prereqs if p]

    prereq_keys = [p for p in raw_prereqs if p and p.lower() not in ("none", "n/a", "")]

    if prereq_keys:
        owned = _safe(
            sb.table("skill_purchase_requests")
            .select("skill_key,status")
            .eq("guild_id", gid)
            .eq("character_id", cid)
            .eq("source_label", "Beast Skill")
            .in_("skill_key", prereq_keys)
            .limit(50)
        )
        owned_approved = {
            str(r.get("skill_key"))
            for r in owned
            if str(r.get("status") or "").lower() in ("approved", "accepted")
        }
        missing = [k for k in prereq_keys if k not in owned_approved]

        if missing:
            missing_skills = _safe(
                sb.table("source_beast_skill_definitions")
                .select("skill_key,name")
                .eq("guild_id", gid)
                .in_("skill_key", missing)
                .limit(10)
            )
            missing_names = [s.get("name") or s.get("skill_key") for s in missing_skills] or missing
            raise HTTPException(
                status_code=400,
                detail=f"Prerequisites not met. You need: {', '.join(missing_names)}.",
            )

    # Duplicate check
    existing_requests = _safe(
        sb.table("skill_purchase_requests")
        .select("request_id,status")
        .eq("guild_id", gid)
        .eq("character_id", cid)
        .eq("skill_key", skill_key)
        .eq("source_label", "Beast Skill")
        .limit(10)
    )
    for req in existing_requests:
        status = str(req.get("status") or "").lower()
        if status == "pending":
            raise HTTPException(status_code=409, detail="You already have a pending request for this beast skill.")
        if status in ("approved", "accepted"):
            raise HTTPException(status_code=409, detail="Your companion already has this skill.")

    # XP check
    wallet = _get_wallet(sb, cid)
    available = int(wallet.get("available_xp") or 0)
    if cost > 0 and available < cost:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough XP. You have {available} XP, this skill costs {cost} XP.",
        )

    insert_row = {
        "guild_id": gid,
        "character_id": cid,
        "skill_key": skill_key,
        "skill_name": str(skill.get("name") or skill_key),
        "cost": cost,
        "status": "pending",
        "requested_by_discord_id": actor,
        "submitter_note": str(payload.get("note") or "")[:500],
        "source_label": "Beast Skill",
    }

    try:
        result_rows = _rows(sb.table("skill_purchase_requests").insert(insert_row).execute())
        result = result_rows[0] if result_rows else insert_row
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not submit beast skill request: {exc}")

    return {
        "message": f"Request submitted for {skill.get('name') or skill_key}. Staff will review it shortly.",
        "request": result,
        "xp_cost": cost,
        "xp_available": available,
    }


@router.post("/{character_id}/stat-request")
def request_beast_stat(
    character_id: UUID,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    sb = get_supabase()
    cid = str(character_id)
    character = _get_character(sb, cid)

    if not _can_access(character, actor):
        raise HTTPException(status_code=403, detail="You can only request stat changes for your own companion.")

    gid = int(character.get("guild_id") or get_guild_id())

    if not _has_loyal_companion(_get_traits(sb, cid, gid)):
        raise HTTPException(status_code=403, detail="This OC does not have the Loyal Companion trait.")

    stat_key = str(payload.get("stat_key") or "").strip().lower()
    if stat_key not in CORE_STATS:
        raise HTTPException(status_code=400, detail=f"stat_key must be one of: {', '.join(CORE_STATS)}.")

    try:
        target_value = int(payload.get("target_value") or 0)
    except Exception:
        raise HTTPException(status_code=400, detail="target_value must be a number.")

    if target_value < 1 or target_value > 750:
        raise HTTPException(status_code=400, detail="Target value must be between 1 and 750.")

    beast_rows = _safe(sb.table("source_beasts").select("*").eq("character_id", cid).limit(1))
    if not beast_rows:
        raise HTTPException(status_code=404, detail="No LC Unit found. Save your LC Unit profile first.")

    beast = beast_rows[0]
    current_value = int(beast.get(f"base_{stat_key}") or 5)

    if target_value <= current_value:
        raise HTTPException(
            status_code=400,
            detail=f"Target ({target_value}) must be higher than current base ({current_value}).",
        )

    existing = _safe(
        sb.table("skill_purchase_requests")
        .select("request_id,status")
        .eq("guild_id", gid)
        .eq("character_id", cid)
        .eq("skill_key", f"beast_stat_{stat_key}")
        .eq("source_label", "Beast Stat")
        .eq("status", "pending")
        .limit(5)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"You already have a pending stat request for {stat_key}.")

    cost = _stat_xp_cost(current_value, target_value)
    wallet = _get_wallet(sb, cid)
    available = int(wallet.get("available_xp") or 0)

    if cost > 0 and available < cost:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough XP. Cost: {cost} XP, available: {available} XP.",
        )

    label = STAT_LABELS.get(stat_key, stat_key)
    insert_row = {
        "guild_id": gid,
        "character_id": cid,
        "skill_key": f"beast_stat_{stat_key}",
        "skill_name": f"Beast Stat — {label} {current_value} → {target_value}",
        "cost": cost,
        "status": "pending",
        "requested_by_discord_id": actor,
        "submitter_note": str(payload.get("note") or "") or f"Raise {label} from {current_value} to {target_value}.",
        "source_label": "Beast Stat",
    }

    try:
        result_rows = _rows(sb.table("skill_purchase_requests").insert(insert_row).execute())
        result = result_rows[0] if result_rows else insert_row
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not submit stat request: {exc}")

    return {
        "message": f"Stat request submitted. Raising {label} from {current_value} to {target_value} ({cost} XP).",
        "request": result,
        "xp_cost": cost,
        "xp_available": available,
    }


@router.put("/{character_id}/base-stats")
def update_base_stats(
    character_id: UUID,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = _require_login(actor_discord_id)
    if not is_staff(actor):
        raise HTTPException(status_code=403, detail="Staff only.")

    sb = get_supabase()
    cid = str(character_id)
    character = _get_character(sb, cid)
    gid = int(character.get("guild_id") or get_guild_id())

    stat_updates = {f"base_{k}": _safe_int(payload, f"base_{k}") for k in CORE_STATS}
    xp_update = {"xp": _safe_int(payload, "xp", 0)} if "xp" in payload else {}

    existing = _safe(sb.table("source_beasts").select("character_id").eq("character_id", cid).limit(1))
    if not existing:
        raise HTTPException(status_code=404, detail="No LC Unit found for this OC. Save the LC Unit first.")

    sb.table("source_beasts").update({**stat_updates, **xp_update}).eq("character_id", cid).execute()

    rows = _safe(sb.table("source_beasts").select("*").eq("character_id", cid).limit(1))
    saved = rows[0] if rows else {}
    oc_stats = _get_oc_stats(sb, cid)

    return {
        "message": "Base stats updated.",
        "beast": saved,
        "computed_stats": _computed_stats(saved, oc_stats),
    }