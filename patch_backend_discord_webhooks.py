from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()
BACKEND = ROOT / "backend" / "app"

HELPER_SOURCE = ROOT / "backend_app_discord_webhook.py"
HELPER_TARGET = BACKEND / "discord_webhook.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def backup(path: Path):
    backup_path = path.with_suffix(path.suffix + ".webhook.bak")
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def add_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text

    lines = text.splitlines()
    insert_index = 0

    for i, line in enumerate(lines):
        if line.startswith("from app.") or line.startswith("import app."):
            insert_index = i + 1

    lines.insert(insert_index, import_line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def patch_xp():
    path = BACKEND / "routes" / "xp.py"
    text = read(path)
    original = text
    backup(path)

    text = add_import(
        text,
        "from app.discord_webhook import notify_stat_submitted",
    )

    needle = '''    return {"request": result}'''
    replacement = '''    if isinstance(result, dict):
        notify_stat_submitted(result)

    return {"request": result}'''

    if "notify_stat_submitted(result)" not in text:
        if needle not in text:
            raise RuntimeError("Could not patch xp.py: return {'request': result} not found.")
        text = text.replace(needle, replacement, 1)

    if text != original:
        write(path, text)
        print("Patched backend/app/routes/xp.py")
    else:
        print("backend/app/routes/xp.py already patched")


def patch_shops():
    path = BACKEND / "routes" / "shops.py"
    text = read(path)
    original = text
    backup(path)

    text = add_import(
        text,
        "from app.discord_webhook import notify_shop_listing_submitted",
    )

    needle = '''    return {
        "ok": True,
        "item": created,
        "message": "Listing submitted for staff review.",
    }'''

    replacement = '''    if isinstance(created, dict):
        notify_shop_listing_submitted(created)

    return {
        "ok": True,
        "item": created,
        "message": "Listing submitted for staff review.",
    }'''

    if "notify_shop_listing_submitted(created)" not in text:
        if needle not in text:
            raise RuntimeError("Could not patch shops.py: create listing return block not found.")
        text = text.replace(needle, replacement, 1)

    if text != original:
        write(path, text)
        print("Patched backend/app/routes/shops.py")
    else:
        print("backend/app/routes/shops.py already patched")


def patch_staff():
    path = BACKEND / "routes" / "staff.py"
    text = read(path)
    original = text
    backup(path)

    text = add_import(
        text,
        "from app.discord_webhook import notify_shop_listing_reviewed, notify_stat_reviewed",
    )

    needle = '''    return {"result": result}


@router.post("/stat-requests/{request_id}/deny")'''
    replacement = '''    if isinstance(result, dict):
        notify_stat_reviewed(
            request_id=request_id,
            action="approved",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

    return {"result": result}


@router.post("/stat-requests/{request_id}/deny")'''

    if 'action="approved"' not in text:
        if needle not in text:
            raise RuntimeError("Could not patch staff.py stat approve return.")
        text = text.replace(needle, replacement, 1)

    needle = '''    return {"result": result}


@router.get("/shop-items")'''
    replacement = '''    if isinstance(result, dict):
        notify_stat_reviewed(
            request_id=request_id,
            action="denied",
            staff_id=staff_id,
            note=payload.staff_note,
            result=result,
        )

    return {"result": result}


@router.get("/shop-items")'''

    if 'action="denied"' not in text:
        if needle not in text:
            raise RuntimeError("Could not patch staff.py stat deny return.")
        text = text.replace(needle, replacement, 1)

    needle = '''    return {
        "ok": True,
        "item": item,
        "message": "Shop listing approved and published.",
    }


@router.post("/shop-items/{item_id}/deny")'''
    replacement = '''    notify_shop_listing_reviewed(
        item_id=item_id,
        action="approved",
        staff_id=staff_id,
        note=payload.staff_note,
        item=item,
    )

    return {
        "ok": True,
        "item": item,
        "message": "Shop listing approved and published.",
    }


@router.post("/shop-items/{item_id}/deny")'''

    if 'notify_shop_listing_reviewed(\n        item_id=item_id,\n        action="approved"' not in text:
        if needle not in text:
            raise RuntimeError("Could not patch staff.py shop approve return.")
        text = text.replace(needle, replacement, 1)

    needle = '''    return {
        "ok": True,
        "item": item,
        "message": "Shop listing denied.",
    }'''
    replacement = '''    notify_shop_listing_reviewed(
        item_id=item_id,
        action="denied",
        staff_id=staff_id,
        note=payload.staff_note,
        item=item,
    )

    return {
        "ok": True,
        "item": item,
        "message": "Shop listing denied.",
    }'''

    if 'notify_shop_listing_reviewed(\n        item_id=item_id,\n        action="denied"' not in text:
        if needle not in text:
            raise RuntimeError("Could not patch staff.py shop deny return.")
        text = text.replace(needle, replacement, 1)

    if text != original:
        write(path, text)
        print("Patched backend/app/routes/staff.py")
    else:
        print("backend/app/routes/staff.py already patched")


def main():
    if not HELPER_SOURCE.exists():
        raise RuntimeError(f"Missing {HELPER_SOURCE.name}. Extract the patch zip into the project root first.")

    HELPER_TARGET.write_text(HELPER_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    print("Installed backend/app/discord_webhook.py")

    patch_xp()
    patch_shops()
    patch_staff()

    print("")
    print("Done. Restart backend, then submit/review a test item/request.")


if __name__ == "__main__":
    main()
