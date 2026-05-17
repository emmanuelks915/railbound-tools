from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, HTTPException

from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase
from app.utils.activity_webhooks import send_staff_activity_webhook
from app.utils.activity_logger import log_activity

router = APIRouter(prefix="/api/oc-registration", tags=["oc-registration"])

NAME_RE = re.compile(r"^[A-Za-z0-9 _'\-]{1,64}$")
MAX_STARTING_TRAITS = 8


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _clean_text(value: Any, max_len: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:max_len]


def _clean_sheet_url(raw_url: Any) -> str | None:
    url = str(raw_url or "").strip()
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Please provide a valid sheet link starting with http:// or https://.")

    return url[:500]


def _trait_tier(trait: dict[str, Any]) -> str:
    return str(trait.get("tier") or "").strip().lower()


def _trait_cost(trait: dict[str, Any]) -> int:
    try:
        return int(trait.get("cost") or 0)
    except Exception:
        return 0


def _active_traits(sb) -> list[dict[str, Any]]:
    try:
        return _as_list(
            sb.table("traits")
            .select("trait_id,name,slug,tier,cost,is_active,exclusive_group,requirements_json")
            .eq("guild_id", get_guild_id())
            .eq("is_active", True)
            .order("name")
            .limit(500)
            .execute()
        )
    except Exception:
        return []


def _serialize_trait(trait: dict[str, Any]) -> dict[str, Any]:
    return {
        "trait_id": str(trait.get("trait_id") or ""),
        "name": trait.get("name") or "Trait",
        "slug": trait.get("slug"),
        "tier": trait.get("tier"),
        "cost": _trait_cost(trait),
        "exclusive_group": trait.get("exclusive_group"),
        "requirements_json": trait.get("requirements_json") or {},
    }


def _trait_map(traits: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("trait_id")): row for row in traits if row.get("trait_id")}


def _summary(selected_traits: list[dict[str, Any]]) -> dict[str, int]:
    positive = 0
    negative = 0
    origin = 0

    for trait in selected_traits:
        cost = _trait_cost(trait)
        tier = _trait_tier(trait)

        if tier == "origin":
            origin += 1
        elif cost >= 0:
            positive += cost
        else:
            negative += abs(cost)

    free_limit = 5
    hard_cap = 8
    overdraft_limit = min(hard_cap, free_limit + negative)

    return {
        "positive": positive,
        "negative": negative,
        "origin": origin,
        "free_limit": free_limit,
        "hard_cap": hard_cap,
        "overdraft_limit": overdraft_limit,
    }


def _validate_traits(selected_traits: list[dict[str, Any]]) -> str | None:
    ids = [str(t.get("trait_id")) for t in selected_traits if t.get("trait_id")]
    if len(ids) != len(set(ids)):
        return "You selected the same trait more than once."

    origin_count = sum(1 for trait in selected_traits if _trait_tier(trait) == "origin")
    if origin_count > 1:
        return "You may only choose one Origin trait."

    groups: dict[str, str] = {}
    for trait in selected_traits:
        group = str(trait.get("exclusive_group") or "").strip().lower()
        if not group:
            continue

        name = str(trait.get("name") or "Trait")
        if group in groups:
            return f"Trait conflict: {name} conflicts with {groups[group]}."

        groups[group] = name

    points = _summary(selected_traits)
    positive = int(points["positive"])
    negative = int(points["negative"])
    free_limit = int(points["free_limit"])
    hard_cap = int(points["hard_cap"])

    if positive > hard_cap:
        return f"A character may not exceed {hard_cap} positive trait points."

    if positive > free_limit and positive > free_limit + negative:
        needed = positive - free_limit
        return f"This build needs at least {needed} point(s) of Negative Traits."

    return None


def _get_selected_traits(sb, origin_trait_id: str | None, trait_ids: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    all_traits = _active_traits(sb)
    by_id = _trait_map(all_traits)

    selected_ids: list[str] = []
    if origin_trait_id:
        selected_ids.append(str(origin_trait_id))
    selected_ids.extend([str(value) for value in trait_ids if str(value).strip()])

    selected_ids = list(dict.fromkeys(selected_ids))

    if len([tid for tid in selected_ids if _trait_tier(by_id.get(tid, {})) != "origin"]) > MAX_STARTING_TRAITS:
        return [], f"You can only select up to {MAX_STARTING_TRAITS} starting traits."

    missing = [trait_id for trait_id in selected_ids if trait_id not in by_id]
    if missing:
        return [], "One or more selected traits are no longer available."

    selected = [by_id[trait_id] for trait_id in selected_ids]
    return selected, _validate_traits(selected)


def _try_add_traits(sb, character_id: str, trait_ids: list[str], actor_discord_id: int) -> None:
    if not trait_ids:
        return

    payload = [
        {
            "guild_id": get_guild_id(),
            "character_id": character_id,
            "trait_id": trait_id,
            "approved_by": actor_discord_id,
            "notes": "Selected during dashboard OC registration",
        }
        for trait_id in trait_ids
    ]

    for table in ("character_traits", "oc_traits"):
        try:
            sb.table(table).upsert(payload).execute()
            return
        except Exception:
            continue

    raise HTTPException(status_code=500, detail="OC was created, but selected traits could not be attached.")


def _try_create_wallet(sb, character_id: str) -> None:
    try:
        currencies = _as_list(
            sb.table("currencies")
            .select("*")
            .eq("guild_id", get_guild_id())
            .limit(100)
            .execute()
        )
        if not currencies:
            return

        primary = None
        for row in currencies:
            if row.get("is_primary") is True or row.get("is_default") is True or row.get("primary") is True:
                primary = row
                break

        primary = primary or currencies[0]
        currency_id = primary.get("currency_id") or primary.get("id")
        if not currency_id:
            return

        sb.table("wallets").upsert(
            {
                "guild_id": get_guild_id(),
                "character_id": character_id,
                "currency_id": currency_id,
                "balance": 0,
            }
        ).execute()
    except Exception:
        return


@router.get("/options")
def get_registration_options(actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()
    traits = [_serialize_trait(row) for row in _active_traits(sb)]

    return {
        "traits": traits,
        "max_starting_traits": MAX_STARTING_TRAITS,
        "sections": [
            "General",
            "Stats",
            "Wardrobe",
            "Appearance",
            "Traits",
            "Inventory",
            "Skills",
            "Relationships",
            "Missions & Events",
            "XP Audit",
        ],
    }


# --- Starting XP v1 ---

STARTING_OC_XP = 600


def _try_create_starting_xp(sb, character_id: str, actor_discord_id: int | None = None) -> None:
    gid = get_guild_id()

    try:
        existing = _as_list(
            sb.table("oc_xp_wallets")
            .select("*")
            .eq("guild_id", gid)
            .eq("character_id", character_id)
            .limit(1)
            .execute()
        )

        if existing:
            return

        sb.table("oc_xp_wallets").insert(
            {
                "guild_id": gid,
                "character_id": character_id,
                "available_xp": STARTING_OC_XP,
                "total_earned_xp": STARTING_OC_XP,
                "total_spent_xp": 0,
            }
        ).execute()

        sb.table("oc_xp_transactions").insert(
            {
                "guild_id": gid,
                "character_id": character_id,
                "direction": "earn",
                "amount": STARTING_OC_XP,
                "source": "starting_xp",
                "reference_type": None,
                "reference_key": "starting_oc_xp",
                "reason": "Starting OC XP grant.",
                "actor_discord_id": actor_discord_id,
                "metadata": {"starting_xp": True, "amount": STARTING_OC_XP},
            }
        ).execute()

        try:
            sb.table("activity_log").insert(
                {
                    "guild_id": gid,
                    "event_type": "starting_xp_granted",
                    "label": "Starting XP granted",
                    "status": "approved",
                    "actor_discord_id": actor_discord_id,
                    "character_id": character_id,
                    "amount": STARTING_OC_XP,
                    "note": "Automatic starting XP granted on OC registration.",
                    "source": "oc_registration",
                    "details": {"starting_xp": True, "amount": STARTING_OC_XP},
                }
            ).execute()
        except Exception:
            pass

    except Exception:
        return


@router.post("/validate")
def validate_registration(payload: dict[str, Any] = Body(...), actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()
    selected, error = _get_selected_traits(
        sb,
        str(payload.get("origin_trait_id") or "").strip() or None,
        [str(value) for value in (payload.get("trait_ids") or [])],
    )

    return {
        "ok": error is None,
        "error": error,
        "summary": _summary(selected),
        "selected_traits": [_serialize_trait(row) for row in selected],
    }


@router.post("/characters")
def create_character(payload: dict[str, Any] = Body(...), actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is None:
        raise HTTPException(status_code=401, detail="Login with Discord required.")

    sb = get_supabase()

    name = _clean_text(payload.get("name"), 64)
    if not name:
        raise HTTPException(status_code=400, detail="Please provide an OC name.")

    if not NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="OC name has invalid characters.")

    sheet_url = _clean_sheet_url(payload.get("sheet_url"))
    occupation = _clean_text(payload.get("occupation"), 80)
    affiliation = _clean_text(payload.get("affiliation"), 120)
    blurb = _clean_text(payload.get("blurb"), 1200)

    origin_trait_id = str(payload.get("origin_trait_id") or "").strip() or None
    trait_ids = [str(value) for value in (payload.get("trait_ids") or []) if str(value).strip()]
    trait_ids = list(dict.fromkeys(trait_ids))

    selected, error = _get_selected_traits(sb, origin_trait_id, trait_ids)
    if error:
        raise HTTPException(status_code=400, detail=error)

    try:
        existing = _as_list(
            sb.table("characters")
            .select("character_id,name")
            .eq("guild_id", get_guild_id())
            .eq("user_id", int(actor_discord_id))
            .execute()
        )
    except Exception:
        existing = _as_list(
            sb.table("characters")
            .select("character_id,name")
            .eq("user_id", int(actor_discord_id))
            .execute()
        )
    for row in existing:
        if str(row.get("name") or "").casefold() == name.casefold():
            raise HTTPException(status_code=400, detail=f"You already have an OC named {row.get('name')}.")

    try:
        sb.table("users").upsert({"user_id": int(actor_discord_id)}).execute()
    except Exception:
        pass

    character_payload: dict[str, Any] = {
        "guild_id": get_guild_id(),
        "user_id": int(actor_discord_id),
        "name": name,
        "is_active": True,
    }

    if sheet_url:
        character_payload["sheet_url"] = sheet_url
    if occupation:
        character_payload["occupation"] = occupation
    if affiliation:
        character_payload["affiliation"] = affiliation
    if blurb:
        character_payload["blurb"] = blurb

    try:
        inserted = _as_list(sb.table("characters").insert(character_payload).execute())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not create OC: {exc}")

    if not inserted:
        raise HTTPException(status_code=500, detail="Could not create OC. Supabase did not return a row.")

    character = inserted[0]
    character_id = str(character.get("character_id") or character.get("id") or "")
    if not character_id:
        raise HTTPException(status_code=500, detail="OC created, but no character ID was returned.")

    selected_ids = [str(row.get("trait_id")) for row in selected if row.get("trait_id")]
    _try_add_traits(sb, character_id, selected_ids, int(actor_discord_id))
    _try_create_wallet(sb, character_id)

    send_staff_activity_webhook(
        title="📝 OC Registered",
        description="OC registered through dashboard.",
        event_type="oc_registered",
        status="created",
        actor_id=actor_discord_id,
        character_id=character_id,
        character_name=name,
        fields=[
            {"name": "Occupation", "value": occupation or "—"},
            {"name": "Affiliation", "value": affiliation or "—"},
            {"name": "Sheet", "value": sheet_url or "—", "inline": False},
        ],
    )

    log_activity(
        event_type="oc_registered",
        label=f"OC registered: {name}",
        status="created",
        actor_discord_id=actor_discord_id,
        character_id=character_id,
        character_name=name,
        note="activity_log_hardening_v2_oc_registered",
        source="oc_registration",
        details={
            "occupation": occupation,
            "affiliation": affiliation,
            "sheet_url": sheet_url,
            "trait_ids": selected_ids,
        },
        webhook_title="📝 OC Registered",
        webhook_description="OC registered through dashboard.",
        webhook_fields=[
            {"name": "Occupation", "value": occupation or "—"},
            {"name": "Affiliation", "value": affiliation or "—"},
            {"name": "Sheet", "value": sheet_url or "—", "inline": False},
        ],
    )

    return {
        "character": character,
        "character_id": character_id,
        "selected_traits": [_serialize_trait(row) for row in selected],
        "summary": _summary(selected),
        "message": f"{name} has been registered.",
    }
