
from __future__ import annotations

from pathlib import Path
import re


CONFIG_PATH = Path("backend/app/config.py")
SECURITY_PATH = Path("backend/app/security.py")
BACKEND_ENV_EXAMPLE = Path("backend/.env.example")
FRONTEND_MAIN = Path("frontend/src/main.tsx")
FRONTEND_ENV_EXAMPLE = Path("frontend/.env.example")

OLD_ACTOR = 'def actor_from_header(\n    x_discord_id: int | None = Header(default=None, alias="X-Discord-Id"),\n    authorization: str | None = Header(default=None, alias="Authorization"),\n) -> int | None:\n    bearer_actor = _actor_from_bearer(authorization)\n    if bearer_actor is not None:\n        return bearer_actor\n    return x_discord_id\n'
NEW_ACTOR = 'def actor_from_header(\n    x_discord_id: int | None = Header(default=None, alias="X-Discord-Id"),\n    authorization: str | None = Header(default=None, alias="Authorization"),\n) -> int | None:\n    bearer_actor = _actor_from_bearer(authorization)\n    if bearer_actor is not None:\n        return bearer_actor\n\n    # Manual Discord ID login is a local-dev escape hatch only.\n    # In production, ALLOW_DEV_LOGIN should be false so users must authenticate through Discord OAuth.\n    if get_settings().allow_dev_login:\n        return x_discord_id\n\n    return None\n'


def backup(path: Path, suffix: str) -> None:
    if not path.exists():
        return

    backup_path = path.with_suffix(path.suffix + suffix)
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def patch_config() -> None:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    original = text
    backup(CONFIG_PATH, ".dev_login_gate.bak")

    if "allow_dev_login:" not in text:
        marker = "    model_config = SettingsConfigDict"
        if marker not in text:
            raise RuntimeError("Could not find model_config marker in backend/app/config.py.")

        text = text.replace(
            marker,
            "    allow_dev_login: bool = False\n" + marker,
            1,
        )

    if text != original:
        CONFIG_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/config.py")
    else:
        print("backend/app/config.py already patched")


def patch_security() -> None:
    text = SECURITY_PATH.read_text(encoding="utf-8")
    original = text
    backup(SECURITY_PATH, ".dev_login_gate.bak")

    if OLD_ACTOR in text:
        text = text.replace(OLD_ACTOR, NEW_ACTOR, 1)
    elif "ALLOW_DEV_LOGIN should be false" not in text:
        pattern = re.compile(
            r"def actor_from_header\([\s\S]*?\n\s*return x_discord_id\n",
            re.MULTILINE,
        )
        text, count = pattern.subn(NEW_ACTOR, text, count=1)
        if count == 0:
            raise RuntimeError("Could not patch actor_from_header in backend/app/security.py.")

    if text != original:
        SECURITY_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/security.py")
    else:
        print("backend/app/security.py already patched")


def append_env_var(path: Path, line: str, comment: str) -> None:
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    original = text
    backup(path, ".dev_login_gate.bak")

    key = line.split("=", 1)[0]
    if key not in text:
        text = text.rstrip() + "\n\n" + comment + "\n" + line + "\n"

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"Patched {path}")
    else:
        print(f"{path} already has {key}")


def patch_frontend_main() -> None:
    text = FRONTEND_MAIN.read_text(encoding="utf-8")
    original = text
    backup(FRONTEND_MAIN, ".dev_login_gate.bak")

    if "const ALLOW_DEV_LOGIN" not in text:
        api_base_match = re.search(r"^const API_BASE\s*=.*$", text, flags=re.MULTILINE)
        if not api_base_match:
            raise RuntimeError("Could not find const API_BASE line in frontend/src/main.tsx.")

        insert_at = api_base_match.end()
        text = (
            text[:insert_at]
            + '\nconst ALLOW_DEV_LOGIN = import.meta.env.VITE_ALLOW_DEV_LOGIN === "true";'
            + text[insert_at:]
        )

    text = text.replace(
        'if (discordId) headers.set("X-Discord-Id", discordId);',
        'if (ALLOW_DEV_LOGIN && discordId) headers.set("X-Discord-Id", discordId);',
    )

    if "ALLOW_DEV_LOGIN ? (" not in text and 'className="auth-dev-login"' in text:
        dev_label_start = text.find('<label className="auth-dev-login">')
        if dev_label_start == -1:
            raise RuntimeError("Could not find auth-dev-login label.")

        dev_label_end = text.find("</label>", dev_label_start)
        if dev_label_end == -1:
            raise RuntimeError("Could not find closing label for auth-dev-login.")

        dev_label_end += len("</label>")
        dev_label = text[dev_label_start:dev_label_end]

        wrapped = "{ALLOW_DEV_LOGIN ? (\n" + dev_label + "\n          ) : null}"
        text = text[:dev_label_start] + wrapped + text[dev_label_end:]

    if text != original:
        FRONTEND_MAIN.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
    else:
        print("frontend/src/main.tsx already patched")


def main() -> None:
    patch_config()
    patch_security()
    append_env_var(
        BACKEND_ENV_EXAMPLE,
        "ALLOW_DEV_LOGIN=false",
        "# Local-only manual Discord ID fallback. Keep false in production.",
    )
    append_env_var(
        FRONTEND_ENV_EXAMPLE,
        "VITE_ALLOW_DEV_LOGIN=false",
        "# Local-only manual Discord ID fallback. Keep false in production.",
    )
    patch_frontend_main()

    print("")
    print("Done.")
    print("For production/Railway: ALLOW_DEV_LOGIN=false and VITE_ALLOW_DEV_LOGIN=false.")
    print("For local emergency fallback only: set both to true and restart frontend/backend.")


if __name__ == "__main__":
    main()
