
from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()
DISCORD_WEBHOOK = ROOT / "backend" / "app" / "discord_webhook.py"
SKILLS_ROUTE = ROOT / "backend" / "app" / "routes" / "skills.py"


SKILL_WEBHOOK_FUNCTIONS = '\ndef notify_skill_submitted(request: dict[str, Any] | None) -> bool:\n    if not request:\n        return False\n\n    return notify_staff_webhook(\n        title="✨ New Skill Request Submitted",\n        description="A player submitted a skill purchase request for staff review.",\n        color=0x2F6F73,\n        fields=[\n            _field("Request ID", request.get("request_id"), inline=False),\n            _field("Character ID", request.get("character_id"), inline=False),\n            _field("Skill", request.get("skill_key"), inline=False),\n            _field("Requested By", request.get("requested_by_discord_id")),\n            _field("Cost", f"{request.get(\'cost\', \'—\')} XP"),\n            _field("Status", request.get("status")),\n            _field("Submitter Note", request.get("submitter_note") or "—", inline=False),\n        ],\n    )\n\n\ndef notify_skill_reviewed(\n    *,\n    request_id: Any,\n    action: str,\n    staff_id: Any,\n    note: str | None = None,\n    result: dict[str, Any] | None = None,\n) -> bool:\n    approved = action.lower() == "approved"\n\n    return notify_staff_webhook(\n        title="✅ Skill Request Approved" if approved else "❌ Skill Request Denied",\n        description="A staff member reviewed a skill purchase request.",\n        color=0x2F8F5B if approved else 0x9C3D3D,\n        fields=[\n            _field("Request ID", request_id, inline=False),\n            _field("Reviewed By", staff_id),\n            _field("Action", action),\n            _field("Skill", result.get("skill_key") if isinstance(result, dict) else "—", inline=False),\n            _field("Character ID", result.get("character_id") if isinstance(result, dict) else "—", inline=False),\n            _field("Cost", f"{result.get(\'cost\', \'—\')} XP" if isinstance(result, dict) else "—"),\n            _field("Note", note or "—", inline=False),\n            _field("Result", result.get("status") if isinstance(result, dict) else "—"),\n        ],\n    )\n'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def backup(path: Path, suffix: str) -> None:
    backup_path = path.with_suffix(path.suffix + suffix)
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def add_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text

    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("from app.") or line.startswith("import app."):
            insert_at = i + 1

    lines.insert(insert_at, import_line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def patch_discord_webhook() -> None:
    text = read(DISCORD_WEBHOOK)
    original = text
    backup(DISCORD_WEBHOOK, ".skill_webhooks.bak")

    if "def notify_skill_submitted" not in text:
        text = text.rstrip() + "\n\n" + SKILL_WEBHOOK_FUNCTIONS.strip() + "\n"

    if text != original:
        write(DISCORD_WEBHOOK, text)
        print("Patched backend/app/discord_webhook.py")
    else:
        print("backend/app/discord_webhook.py already has skill webhook helpers")


def patch_skills_route() -> None:
    text = read(SKILLS_ROUTE)
    original = text
    backup(SKILLS_ROUTE, ".skill_webhooks.bak")

    text = add_import(
        text,
        "from app.discord_webhook import notify_skill_reviewed, notify_skill_submitted",
    )

    submit_needle = """    return {"request": result}


@router.get("/staff/skill-requests")"""
    submit_replacement = """    if isinstance(result, dict):
        notify_skill_submitted(result)

    return {"request": result}


@router.get("/staff/skill-requests")"""

    if "notify_skill_submitted(result)" not in text:
        if submit_needle not in text:
            raise RuntimeError("Could not patch submit_skill_request return block.")
        text = text.replace(submit_needle, submit_replacement, 1)

    approve_needle = """    return {"result": result}


@router.post("/staff/skill-requests/{request_id}/deny")"""
    approve_replacement = """    if isinstance(result, dict):
        notify_skill_reviewed(
            request_id=request_id,
            action="approved",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

    return {"result": result}


@router.post("/staff/skill-requests/{request_id}/deny")"""

    if 'action="approved"' not in text:
        if approve_needle not in text:
            raise RuntimeError("Could not patch approve_skill_request return block.")
        text = text.replace(approve_needle, approve_replacement, 1)

    deny_needle = """    return {"result": result}"""
    deny_replacement = """    if isinstance(result, dict):
        notify_skill_reviewed(
            request_id=request_id,
            action="denied",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

    return {"result": result}"""

    if 'action="denied"' not in text:
        deny_start = text.find("def deny_skill_request(")
        if deny_start == -1:
            raise RuntimeError("Could not find deny_skill_request function.")

        return_pos = text.find(deny_needle, deny_start)
        if return_pos == -1:
            raise RuntimeError("Could not find deny_skill_request return block.")

        text = text[:return_pos] + deny_replacement + text[return_pos + len(deny_needle):]

    if text != original:
        write(SKILLS_ROUTE, text)
        print("Patched backend/app/routes/skills.py")
    else:
        print("backend/app/routes/skills.py already patched")


def main() -> None:
    patch_discord_webhook()
    patch_skills_route()

    print("")
    print("Done. Restart backend, then submit/approve/deny a skill request to test Discord embeds.")


if __name__ == "__main__":
    main()
