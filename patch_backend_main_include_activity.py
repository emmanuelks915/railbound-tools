from pathlib import Path
import re

MAIN_PATH = Path("backend/app/main.py")

def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text

    route_import_pattern = re.compile(r"from app\.routes import ([^\n]+)")
    match = route_import_pattern.search(text)

    if match:
        routes = [part.strip() for part in match.group(1).split(",")]
        if "activity" not in routes:
            routes.append("activity")
            text = text[:match.start(1)] + ", ".join(routes) + text[match.end(1):]
    elif "from app.routes import activity" not in text:
        text = "from app.routes import activity\n" + text

    if "activity.router" not in text:
        include_lines = list(re.finditer(r"app\.include_router\([^\n]+\)", text))
        if include_lines:
            insert_at = include_lines[-1].end()
            text = text[:insert_at] + "\napp.include_router(activity.router)" + text[insert_at:]
        else:
            text += "\n\napp.include_router(activity.router)\n"

    if text != original:
        MAIN_PATH.with_suffix(".py.activity_log.bak").write_text(original, encoding="utf-8")
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/main.py")
        print("Backup saved as backend/app/main.py.activity_log.bak")
    else:
        print("backend/app/main.py already includes Activity router")

if __name__ == "__main__":
    main()
