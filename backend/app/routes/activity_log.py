from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/activity-log", tags=["activity-log"])


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _row_time(row: dict[str, Any]) -> str:
    for key in ("created_at", "updated_at", "submitted_at", "approved_at", "denied_at", "timestamp", "posted_at"):
        if row.get(key):
            return str(row.get(key))
    return datetime.now(timezone.utc).isoformat()


def _status(row: dict[str, Any]) -> str:
    value = str(row.get("status") or row.get("state") or "").lower()
    if value in {"approved", "accepted", "complete", "completed"}:
        return "approved"
    if value in {"denied", "rejected", "declined"}:
        return "denied"
    if value in {"pending", "submitted", "open"}:
        return "pending"
    return value or "submitted"


def _actor(row: dict[str, Any]) -> Any:
    for key in ("actor_discord_id", "staff_discord_id", "reviewed_by", "approved_by", "denied_by", "requested_by", "submitted_by", "created_by", "user_id", "discord_id"):
        if row.get(key) is not None:
            return row.get(key)
    return None


def _character_id(row: dict[str, Any]) -> Any:
    for key in ("character_id", "oc_id", "target_character_id", "to_character_id", "from_character_id"):
        if row.get(key) is not None:
            return row.get(key)
    return None


def _event(*, event_type: str, label: str, row: dict[str, Any], status: str = "info", amount: Any = None, note: Any = None, source: str = "") -> dict[str, Any]:
    return {
        "event_type": event_type,
        "label": label,
        "status": status,
        "actor_id": str(_actor(row)) if _actor(row) is not None else None,
        "character_id": str(_character_id(row)) if _character_id(row) is not None else None,
        "character_name": row.get("character_name") or row.get("name"),
        "created_at": _row_time(row),
        "amount": amount,
        "note": str(note) if note is not None else None,
        "source": source,
        "raw": row,
    }


def _character_lookup(sb, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    rows = _safe_rows(sb.table("characters").select("character_id,id,name").eq("guild_id", get_guild_id()).in_("character_id", list(ids)).limit(500))
    if not rows:
        rows = _safe_rows(sb.table("characters").select("character_id,id,name").in_("character_id", list(ids)).limit(500))
    out = {}
    for row in rows:
        if row.get("character_id"):
            out[str(row.get("character_id"))] = row.get("name") or "Unnamed OC"
        if row.get("id"):
            out[str(row.get("id"))] = row.get("name") or "Unnamed OC"
    return out


def _activity_table_events(sb, limit: int) -> list[dict[str, Any]]:
    rows = _safe_rows(sb.table("activity_log").select("*").eq("guild_id", get_guild_id()).order("created_at", desc=True).limit(limit))
    events = []
    for row in rows:
        events.append(_event(
            event_type=str(row.get("event_type") or row.get("type") or "activity"),
            label=str(row.get("label") or row.get("message") or row.get("event_type") or "Activity"),
            status=str(row.get("status") or "info"),
            row=row,
            amount=row.get("amount"),
            note=row.get("note") or row.get("details"),
            source="activity_log",
        ))
    return events


def _character_events(sb, limit: int) -> list[dict[str, Any]]:
    rows = _safe_rows(sb.table("characters").select("*").eq("guild_id", get_guild_id()).order("created_at", desc=True).limit(limit))
    events = []
    for row in rows:
        events.append(_event(
            event_type="oc_registered",
            label=f"OC registered: {row.get('name') or 'Unnamed OC'}",
            status="created",
            row={**row, "character_name": row.get("name")},
            note=row.get("occupation") or row.get("affiliation"),
            source="characters",
        ))
    return events


def _stat_request_events(sb, limit: int) -> list[dict[str, Any]]:
    rows = _safe_rows(sb.table("stat_requests").select("*").eq("guild_id", get_guild_id()).order("created_at", desc=True).limit(limit))
    events = []
    for row in rows:
        stat = row.get("stat_key") or row.get("stat_name") or row.get("stat") or "stat"
        events.append(_event(
            event_type="stat_request",
            label=f"Stat request {_status(row)}: {stat}",
            status=_status(row),
            row=row,
            amount=row.get("amount") or row.get("delta") or row.get("new_value"),
            note=row.get("reason") or row.get("notes") or row.get("denial_reason"),
            source="stat_requests",
        ))
    return events


def _skill_request_events(sb, limit: int) -> list[dict[str, Any]]:
    rows = _safe_rows(sb.table("skill_requests").select("*").eq("guild_id", get_guild_id()).order("created_at", desc=True).limit(limit))
    events = []
    for row in rows:
        skill = row.get("skill_name") or row.get("name") or row.get("skill_key") or "skill"
        events.append(_event(
            event_type="skill_request",
            label=f"Skill request {_status(row)}: {skill}",
            status=_status(row),
            row=row,
            amount=row.get("cost") or row.get("xp_cost"),
            note=row.get("reason") or row.get("notes") or row.get("denial_reason"),
            source="skill_requests",
        ))
    return events


def _xp_events(sb, limit: int) -> list[dict[str, Any]]:
    rows = _safe_rows(sb.table("oc_xp_transactions").select("*").eq("guild_id", get_guild_id()).order("created_at", desc=True).limit(limit))
    if not rows:
        rows = _safe_rows(sb.table("oc_xp_transactions").select("*").order("created_at", desc=True).limit(limit))
    events = []
    for row in rows:
        tx_type = row.get("tx_type") or row.get("type") or "change"
        events.append(_event(
            event_type="xp_change",
            label=f"XP {str(tx_type).lower()}",
            status="complete",
            row=row,
            amount=row.get("amount") or row.get("delta") or row.get("xp"),
            note=row.get("memo") or row.get("note") or row.get("reason"),
            source="oc_xp_transactions",
        ))
    return events


def _currency_events(sb, limit: int) -> list[dict[str, Any]]:
    rows = _safe_rows(sb.table("transactions").select("*").eq("guild_id", get_guild_id()).order("created_at", desc=True).limit(limit))
    if not rows:
        rows = _safe_rows(sb.table("transactions").select("*").order("created_at", desc=True).limit(limit))
    events = []
    for row in rows:
        tx_type = row.get("tx_type") or row.get("type") or row.get("kind") or "transaction"
        events.append(_event(
            event_type="currency_change",
            label=f"Currency {str(tx_type).lower()}",
            status="complete",
            row=row,
            amount=row.get("amount") or row.get("delta") or row.get("value"),
            note=row.get("memo") or row.get("note") or row.get("reason"),
            source="transactions",
        ))
    return events


@router.get("")
def get_activity_log(
    actor_discord_id: int | None = Depends(actor_from_header),
    limit: int = Query(120, ge=1, le=250),
    event_type: str | None = Query(None),
    status: str | None = Query(None),
):
    if actor_discord_id is None:
        return {"events": [], "total": 0, "message": "Login with Discord required."}

    sb = get_supabase()
    per_source = max(30, min(limit, 120))

    events: list[dict[str, Any]] = []
    events.extend(_activity_table_events(sb, per_source))
    events.extend(_character_events(sb, per_source))
    events.extend(_stat_request_events(sb, per_source))
    events.extend(_skill_request_events(sb, per_source))
    events.extend(_xp_events(sb, per_source))
    events.extend(_currency_events(sb, per_source))

    lookup = _character_lookup(sb, {e["character_id"] for e in events if e.get("character_id")})
    for event in events:
        if event.get("character_id") and not event.get("character_name"):
            event["character_name"] = lookup.get(str(event["character_id"]))

    if event_type:
        events = [e for e in events if str(e.get("event_type")) == event_type]
    if status:
        events = [e for e in events if str(e.get("status")) == status]

    events.sort(key=lambda e: str(e.get("created_at") or ""), reverse=True)
    return {"events": events[:limit], "total": len(events[:limit])}
