from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


def _field(name: str, value: Any, inline: bool = True) -> dict[str, Any]:
    text = "—" if value is None or value == "" else str(value)

    if len(text) > 900:
        text = text[:897] + "..."

    return {
        "name": name,
        "value": text,
        "inline": inline,
    }


def notify_staff_webhook(
    *,
    title: str,
    description: str | None = None,
    color: int = 0x2F6F73,
    fields: list[dict[str, Any]] | None = None,
    url: str | None = None,
) -> bool:
    """
    Best-effort Discord webhook notifier.

    This never raises if Discord fails, because Railbound Tools actions should
    still succeed even when Discord is down or the webhook is temporarily broken.
    """

    settings = get_settings()
    webhook_url = (settings.discord_staff_webhook_url or "").strip()

    if not webhook_url:
        return False

    embed: dict[str, Any] = {
        "title": title,
        "color": color,
    }

    if description:
        embed["description"] = description

    if fields:
        embed["fields"] = fields[:25]

    if url:
        embed["url"] = url

    payload = {
        "embeds": [embed],
        "allowed_mentions": {
            "parse": [],
        },
    }

    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        return 200 <= response.status_code < 300
    except Exception:
        return False


def notify_stat_submitted(request: dict[str, Any] | None) -> bool:
    if not request:
        return False

    return notify_staff_webhook(
        title="📊 New Stat Request Submitted",
        description="A player submitted a stat upgrade request for staff review.",
        color=0x2F6F73,
        fields=[
            _field("Request ID", request.get("request_id"), inline=False),
            _field("Character", request.get("character_name") or request.get("character_id"), inline=False),
            _field("Requested By", request.get("requested_by_discord_id")),
            _field("Total Cost", f"{request.get('total_cost', '—')} XP"),
            _field("Status", request.get("status")),
        ],
    )


def notify_stat_reviewed(
    *,
    request_id: Any,
    action: str,
    staff_id: Any,
    note: str | None = None,
    result: dict[str, Any] | None = None,
) -> bool:
    approved = action.lower() == "approved"

    return notify_staff_webhook(
        title="✅ Stat Request Approved" if approved else "❌ Stat Request Denied",
        description="A staff member reviewed a stat upgrade request.",
        color=0x2F8F5B if approved else 0x9C3D3D,
        fields=[
            _field("Request ID", request_id, inline=False),
            _field("Reviewed By", staff_id),
            _field("Action", action),
            _field("Note", note or "—", inline=False),
            _field("Result", result.get("status") if isinstance(result, dict) else "—"),
        ],
    )


def notify_shop_listing_submitted(item: dict[str, Any] | None) -> bool:
    if not item:
        return False

    return notify_staff_webhook(
        title="🛒 New Shop Listing Submitted",
        description="A player shop listing is waiting for staff review.",
        color=0x2F6F73,
        fields=[
            _field("Item", item.get("name"), inline=False),
            _field("Item ID", item.get("item_id"), inline=False),
            _field("Vendor Company", item.get("vendor_company_id"), inline=False),
            _field("Price", item.get("price")),
            _field("Stock", item.get("stock") if item.get("stock") is not None else "∞"),
            _field("Status", item.get("review_status")),
            _field("Submitted By", item.get("submitted_by_discord_id")),
        ],
        url=item.get("image_url"),
    )


def notify_shop_listing_reviewed(
    *,
    item_id: Any,
    action: str,
    staff_id: Any,
    note: str | None = None,
    item: dict[str, Any] | None = None,
) -> bool:
    approved = action.lower() == "approved"
    item = item or {}

    return notify_staff_webhook(
        title="✅ Shop Listing Approved" if approved else "❌ Shop Listing Denied",
        description="A staff member reviewed a player shop listing.",
        color=0x2F8F5B if approved else 0x9C3D3D,
        fields=[
            _field("Item", item.get("name") or "—", inline=False),
            _field("Item ID", item_id, inline=False),
            _field("Reviewed By", staff_id),
            _field("Action", action),
            _field("Note", note or "—", inline=False),
            _field("Status", item.get("review_status") or "—"),
        ],
        url=item.get("image_url"),
    )

def notify_skill_submitted(request: dict[str, Any] | None) -> bool:
    if not request:
        return False

    return notify_staff_webhook(
        title="✨ New Skill Request Submitted",
        description="A player submitted a skill purchase request for staff review.",
        color=0x2F6F73,
        fields=[
            _field("Request ID", request.get("request_id"), inline=False),
            _field("Character", request.get("character_name") or request.get("character_id"), inline=False),
            _field("Skill", request.get("skill_name") or request.get("skill_key"), inline=False),
            _field("Requested By", request.get("requested_by_discord_id")),
            _field("Cost", f"{request.get('cost', '—')} XP"),
            _field("Status", request.get("status")),
            _field("Submitter Note", request.get("submitter_note") or "—", inline=False),
        ],
    )


def notify_skill_reviewed(
    *,
    request_id: Any,
    action: str,
    staff_id: Any,
    note: str | None = None,
    result: dict[str, Any] | None = None,
) -> bool:
    approved = action.lower() == "approved"

    return notify_staff_webhook(
        title="✅ Skill Request Approved" if approved else "❌ Skill Request Denied",
        description="A staff member reviewed a skill purchase request.",
        color=0x2F8F5B if approved else 0x9C3D3D,
        fields=[
            _field("Request ID", request_id, inline=False),
            _field("Reviewed By", staff_id),
            _field("Action", action),
            _field("Skill", (result.get("skill_name") or result.get("skill_key")) if isinstance(result, dict) else "—", inline=False),
            _field("Character", (result.get("character_name") or result.get("character_id")) if isinstance(result, dict) else "—", inline=False),
            _field("Cost", f"{result.get('cost', '—')} XP" if isinstance(result, dict) else "—"),
            _field("Note", note or "—", inline=False),
            _field("Result", result.get("status") if isinstance(result, dict) else "—"),
        ],
    )
