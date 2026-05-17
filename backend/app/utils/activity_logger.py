from __future__ import annotations

from typing import Any

from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase
from app.utils.activity_webhooks import send_staff_activity_webhook


def _as_list(value: Any) -> list[dict[str, Any]]:
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _clean(value: Any, max_len: int = 1000) -> str | None:
    if value is None or value == "":
        return None
    return str(value)[:max_len]


def log_activity(
    *,
    event_type: str,
    label: str,
    status: str = "info",
    actor_discord_id: Any = None,
    character_id: Any = None,
    character_name: Any = None,
    amount: Any = None,
    note: Any = None,
    source: str | None = None,
    details: dict[str, Any] | None = None,
    send_webhook: bool = True,
    webhook_title: str | None = None,
    webhook_description: str | None = None,
    webhook_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Write a reliable activity_log row and optionally send Discord webhook.

    This is intentionally best-effort. It should never break a user action.
    """
    payload: dict[str, Any] = {
        "guild_id": get_guild_id(),
        "event_type": _clean(event_type, 80) or "activity",
        "label": _clean(label, 240) or "Activity",
        "status": _clean(status, 80) or "info",
        "details": details or {},
    }

    if actor_discord_id is not None and str(actor_discord_id).isdigit():
        payload["actor_discord_id"] = int(actor_discord_id)

    if character_id is not None:
        payload["character_id"] = str(character_id)

    if character_name is not None:
        payload["character_name"] = _clean(character_name, 160)

    if amount is not None:
        try:
            payload["amount"] = float(amount)
        except Exception:
            payload["details"] = {**payload["details"], "amount_text": str(amount)}

    if note is not None:
        payload["note"] = _clean(note, 1200)

    if source is not None:
        payload["source"] = _clean(source, 120)

    row: dict[str, Any] | None = None

    try:
        sb = get_supabase()
        inserted = _as_list(sb.table("activity_log").insert(payload).execute())
        if inserted:
            row = inserted[0]
    except Exception:
        row = None

    if send_webhook:
        send_staff_activity_webhook(
            title=webhook_title or payload["label"],
            description=webhook_description or payload.get("note"),
            event_type=payload["event_type"],
            status=payload["status"],
            actor_id=payload.get("actor_discord_id"),
            character_id=payload.get("character_id"),
            character_name=payload.get("character_name"),
            fields=webhook_fields,
        )

    return row
