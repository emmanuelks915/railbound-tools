from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib import request


def _webhook_url() -> str | None:
    return (
        os.getenv("DISCORD_ACTIVITY_WEBHOOK_URL")
        or os.getenv("DISCORD_STAFF_WEBHOOK_URL")
        or os.getenv("STAFF_DISCORD_WEBHOOK_URL")
    )


def _clean(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)[:950]


def _field(name: str, value: Any, inline: bool = True) -> dict[str, Any]:
    return {"name": name[:256], "value": _clean(value), "inline": inline}


def _color_for(event_type: str, status: str | None = None) -> int:
    value = f"{event_type} {status or ''}".lower()

    if any(word in value for word in ("approved", "registered", "created", "restored", "complete")):
        return 0x2F7B4F
    if any(word in value for word in ("denied", "deleted", "archive", "rejected")):
        return 0xA02B2B
    if any(word in value for word in ("submitted", "pending", "request")):
        return 0xAD7830
    return 0x2F6F73


def send_staff_activity_webhook(
    *,
    title: str,
    description: str | None = None,
    event_type: str = "activity",
    status: str | None = None,
    actor_id: Any = None,
    character_id: Any = None,
    character_name: Any = None,
    fields: list[dict[str, Any]] | None = None,
) -> bool:
    """Best-effort Discord webhook notification.

    This must never break dashboard actions. If the webhook is missing or Discord
    rejects it, the caller still succeeds.
    """
    url = _webhook_url()
    if not url:
        return False

    embed_fields: list[dict[str, Any]] = []

    if character_name:
        embed_fields.append(_field("OC", character_name, True))
    elif character_id:
        embed_fields.append(_field("OC ID", character_id, True))

    if actor_id:
        embed_fields.append(_field("Actor", f"<@{actor_id}>", True))

    if status:
        embed_fields.append(_field("Status", status, True))

    for item in fields or []:
        if not item:
            continue
        embed_fields.append(
            _field(
                str(item.get("name") or "Detail"),
                item.get("value"),
                bool(item.get("inline", True)),
            )
        )

    embed: dict[str, Any] = {
        "title": title[:256],
        "color": _color_for(event_type, status),
        "fields": embed_fields[:25],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "Railbound Tools Activity"},
    }

    if description:
        embed["description"] = _clean(description, "")

    payload = {"embeds": [embed]}

    try:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Railbound-Tools/1.0",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=6) as resp:
            return 200 <= int(resp.status) < 300
    except Exception:
        return False
