from __future__ import annotations

from pathlib import Path


SKILLS_PATH = Path("backend/app/routes/skills.py")
OLD_DENY = '    if isinstance(result, dict):\n        notify_skill_reviewed(\n            request_id=request_id,\n            action="denied",\n            staff_id=staff_id,\n            note=payload.staff_note,\n            result=result,\n        )\n\n    return {"result": result}\n'
NEW_DENY = '    if isinstance(result, dict):\n        full_request = _skill_request_for_webhook(sb, request_id)\n        notify_skill_reviewed(\n            request_id=request_id,\n            action="denied",\n            staff_id=staff_id,\n            note=payload.staff_note,\n            result=full_request or result,\n        )\n\n    return {"result": result}\n'


def main() -> None:
    text = SKILLS_PATH.read_text(encoding="utf-8")
    original = text

    backup_path = SKILLS_PATH.with_suffix(".py.skill_requests_422.bak")
    if not backup_path.exists():
        backup_path.write_text(text, encoding="utf-8")

    bad_helper_route = '@router.get("/staff/skill-requests")\ndef _skill_prereq_keys'
    if bad_helper_route in text:
        text = text.replace(bad_helper_route, 'def _skill_prereq_keys', 1)

    text = text.replace(
        '    return {"requests": out}@router.post("/staff/skill-requests/{request_id}/approve")',
        '    return {"requests": out}\n\n\n@router.post("/staff/skill-requests/{request_id}/approve")',
    )

    deny_start = text.find("def deny_skill_request(")
    deny_block = text[deny_start:] if deny_start != -1 else ""

    if OLD_DENY in text and deny_start != -1 and "result=full_request or result" not in deny_block:
        text = text.replace(OLD_DENY, NEW_DENY, 1)

    if text != original:
        SKILLS_PATH.write_text(text, encoding="utf-8")
        print("Fixed backend/app/routes/skills.py")
        print(f"Backup saved as {backup_path}")
    else:
        print("No changes made. File may already be fixed.")

    fixed = SKILLS_PATH.read_text(encoding="utf-8")

    if '@router.get("/staff/skill-requests")\ndef _skill_prereq_keys' in fixed:
        raise RuntimeError("Still broken: helper is still decorated as a route.")

    if 'return {"requests": out}@router.post' in fixed:
        raise RuntimeError("Still broken: approve route is glued to return line.")

    print("Sanity checks passed.")


if __name__ == "__main__":
    main()
