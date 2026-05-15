from __future__ import annotations

from pathlib import Path

MAIN_PATH = Path("frontend/src/main.tsx")
CSS_PATH = Path("frontend/src/styles.css")
COMPONENT_PATH = Path("SkillsDashboard_component.tsx")
CSS_SOURCE_PATH = Path("skills_catalog_v2_css_append.css")


def find_function_block(text: str, function_name: str) -> tuple[int, int]:
    start = text.find(f"function {function_name}(")
    if start == -1:
        raise RuntimeError(f"Could not find function {function_name}.")

    brace_start = text.find("{", start)
    if brace_start == -1:
        raise RuntimeError(f"Could not find opening brace for {function_name}.")

    depth = 0
    in_string: str | None = None
    escaped = False
    in_line_comment = False
    in_block_comment = False

    for i in range(brace_start, len(text)):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            continue

        if ch in ("'", '"', "`"):
            in_string = ch
            continue

        if ch == "{":
            depth += 1

        if ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1

    raise RuntimeError(f"Could not find end of function {function_name}.")


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    component = COMPONENT_PATH.read_text(encoding="utf-8")
    original = text

    start, end = find_function_block(text, "SkillsDashboard")
    text = text[:start] + component.rstrip() + text[end:]

    if text != original:
        MAIN_PATH.with_suffix(".tsx.skills_v2.bak").write_text(original, encoding="utf-8")
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
        print("Backup saved as frontend/src/main.tsx.skills_v2.bak")
    else:
        print("frontend/src/main.tsx unchanged")

    css = CSS_PATH.read_text(encoding="utf-8")
    css_append = CSS_SOURCE_PATH.read_text(encoding="utf-8")

    if "Skill Catalog v2" not in css:
        CSS_PATH.with_suffix(".css.skills_v2.bak").write_text(css, encoding="utf-8")
        CSS_PATH.write_text(css.rstrip() + "\n\n" + css_append.strip() + "\n", encoding="utf-8")
        print("Patched frontend/src/styles.css")
    else:
        print("Skill Catalog v2 CSS already present")


if __name__ == "__main__":
    main()
