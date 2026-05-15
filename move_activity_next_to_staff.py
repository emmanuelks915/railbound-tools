from __future__ import annotations

from pathlib import Path
import re


MAIN_PATH = Path("frontend/src/main.tsx")


def main() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text

    backup_path = MAIN_PATH.with_suffix(".tsx.activity_next_to_staff.bak")
    if not backup_path.exists():
        backup_path.write_text(text, encoding="utf-8")

    activity_line_match = re.search(
        r'^\s*\["activity"\s*,\s*[^,\]]+\s*,\s*"Activity"\s*\],\s*$',
        text,
        flags=re.MULTILINE,
    )

    staff_line_match = re.search(
        r'^\s*\["staff"\s*,\s*[^,\]]+\s*,\s*"Staff"\s*\],\s*$',
        text,
        flags=re.MULTILINE,
    )

    if not activity_line_match:
        raise RuntimeError('Could not find the Activity tab line in frontend/src/main.tsx.')

    if not staff_line_match:
        raise RuntimeError('Could not find the Staff tab line in frontend/src/main.tsx.')

    activity_line = activity_line_match.group(0)

    # Remove Activity from wherever it currently is.
    text = text[:activity_line_match.start()] + text[activity_line_match.end():]

    # Re-find Staff after removing Activity, then place Activity directly after it.
    staff_line_match = re.search(
        r'^\s*\["staff"\s*,\s*[^,\]]+\s*,\s*"Staff"\s*\],\s*$',
        text,
        flags=re.MULTILINE,
    )

    if not staff_line_match:
        raise RuntimeError('Could not re-find the Staff tab after removing Activity.')

    insert_at = staff_line_match.end()
    text = text[:insert_at] + "\n" + activity_line + text[insert_at:]

    if text != original:
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Moved Activity tab directly next to Staff.")
        print(f"Backup saved as {backup_path}")
    else:
        print("No changes made. Activity may already be next to Staff.")


if __name__ == "__main__":
    main()
