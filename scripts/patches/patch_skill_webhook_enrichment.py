from __future__ import annotations

from pathlib import Path


SKILLS_ROUTE = Path("backend/app/routes/skills.py")
DISCORD_WEBHOOK = Path("backend/app/discord_webhook.py")
HELPER_CODE = '\ndef _skill_request_for_webhook(sb, request_id: str | UUID) -> dict[str, Any] | None:\n    """Fetch the full request row after RPC calls so webhook embeds have character/requester details."""\n\n    gid = get_guild_id()\n\n    req_res = (\n        sb.table("skill_purchase_requests")\n        .select("*")\n        .eq("guild_id", gid)\n        .eq("request_id", str(request_id))\n        .limit(1)\n        .execute()\n    )\n    req_rows = sb_data(req_res) or []\n\n    if not req_rows:\n        return None\n\n    req = req_rows[0]\n\n    char_res = (\n        sb.table("characters")\n        .select("character_id,name,user_id")\n        .eq("guild_id", gid)\n        .eq("character_id", req["character_id"])\n        .limit(1)\n        .execute()\n    )\n    char_rows = sb_data(char_res) or []\n    character = char_rows[0] if char_rows else None\n\n    skill_res = (\n        sb.table("skill_definitions")\n        .select("skill_key,name,tree,tier,cost")\n        .eq("guild_id", gid)\n        .eq("skill_key", req["skill_key"])\n        .limit(1)\n        .execute()\n    )\n    skill_rows = sb_data(skill_res) or []\n    skill = skill_rows[0] if skill_rows else None\n\n    return {\n        **req,\n        "character": character,\n        "character_name": character.get("name") if character else None,\n        "skill": skill,\n        "skill_name": skill.get("name") if skill else req.get("skill_key"),\n    }\n'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def backup(path: Path, suffix: str) -> None:
    backup_path = path.with_suffix(path.suffix + suffix)
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def ensure_any_import(text: str) -> str:
    if "from typing import Any" in text:
        return text

    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("from __future__"):
            insert_at = i + 1
            break

    lines.insert(insert_at, "from typing import Any")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def patch_skills_route() -> None:
    text = read(SKILLS_ROUTE)
    original = text
    backup(SKILLS_ROUTE, ".webhook_enrich.bak")

    text = ensure_any_import(text)

    if "def _skill_request_for_webhook" not in text:
        marker = 'router = APIRouter(prefix="/api", tags=["skills"])\n'
        if marker not in text:
            raise RuntimeError("Could not find skills router marker.")
        text = text.replace(marker, marker + HELPER_CODE + "\n", 1)

    old_submit = """    if isinstance(result, dict):
        notify_skill_submitted(result)

    return {"request": result}"""
    new_submit = """    if isinstance(result, dict):
        full_request = _skill_request_for_webhook(sb, result.get("request_id") or result.get("id"))
        notify_skill_submitted(full_request or result)

    return {"request": result}"""

    if "notify_skill_submitted(full_request or result)" not in text and old_submit in text:
        text = text.replace(old_submit, new_submit, 1)

    old_approve = """    if isinstance(result, dict):
        notify_skill_reviewed(
            request_id=request_id,
            action="approved",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

    return {"result": result}"""
    new_approve = """    if isinstance(result, dict):
        full_request = _skill_request_for_webhook(sb, request_id)
        notify_skill_reviewed(
            request_id=request_id,
            action="approved",
            staff_id=staff_id,
            note=payload.staff_note,
            result=full_request or result,
        )

    return {"result": result}"""

    if 'action="approved"' in text and "result=full_request or result" not in text and old_approve in text:
        text = text.replace(old_approve, new_approve, 1)

    old_deny = """    if isinstance(result, dict):
        notify_skill_reviewed(
            request_id=request_id,
            action="denied",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

    return {"result": result}"""
    new_deny = """    if isinstance(result, dict):
        full_request = _skill_request_for_webhook(sb, request_id)
        notify_skill_reviewed(
            request_id=request_id,
            action="denied",
            staff_id=staff_id,
            note=payload.staff_note,
            result=full_request or result,
        )

    return {"result": result}"""

    if 'action="denied"' in text and "result=full_request or result" not in text and old_deny in text:
        text = text.replace(old_deny, new_deny, 1)

    if text != original:
        write(SKILLS_ROUTE, text)
        print("Patched backend/app/routes/skills.py")
    else:
        print("backend/app/routes/skills.py already enriched")


def patch_discord_webhook() -> None:
    text = read(DISCORD_WEBHOOK)
    original = text
    backup(DISCORD_WEBHOOK, ".webhook_enrich.bak")

    replacements = {
        '_field("Character ID", request.get("character_id"), inline=False),':
            '_field("Character", request.get("character_name") or request.get("character_id"), inline=False),',
        '_field("Skill", request.get("skill_key"), inline=False),':
            '_field("Skill", request.get("skill_name") or request.get("skill_key"), inline=False),',
        '_field("Skill", result.get("skill_key") if isinstance(result, dict) else "—", inline=False),':
            '_field("Skill", (result.get("skill_name") or result.get("skill_key")) if isinstance(result, dict) else "—", inline=False),',
        '_field("Character ID", result.get("character_id") if isinstance(result, dict) else "—", inline=False),':
            '_field("Character", (result.get("character_name") or result.get("character_id")) if isinstance(result, dict) else "—", inline=False),',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    if text != original:
        write(DISCORD_WEBHOOK, text)
        print("Patched backend/app/discord_webhook.py")
    else:
        print("backend/app/discord_webhook.py already uses enriched fields")


def main() -> None:
    patch_skills_route()
    patch_discord_webhook()

    print("")
    print("Done. Restart backend and request another skill. The embed should show Character + Requested By.")


if __name__ == "__main__":
    main()
