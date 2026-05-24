
from __future__ import annotations

from pathlib import Path


AUTH_PATH = Path("backend/app/routes/auth.py")
MAIN_TSX_PATH = Path("frontend/src/main.tsx")
CSS_PATH = Path("frontend/src/styles.css")

NEW_AUTH_ME = '@router.get("/me")\ndef auth_me(\n    actor_discord_id: int | None = Depends(actor_from_header),\n    authorization: str | None = Header(default=None, alias="Authorization"),\n):\n    if actor_discord_id is None:\n        return {\n            "authenticated": False,\n            "discord_id": None,\n            "user": None,\n            "is_staff": False,\n        }\n\n    user = {\n        "discord_id": str(actor_discord_id),\n        "username": None,\n        "global_name": None,\n        "avatar": None,\n        "avatar_url": None,\n    }\n\n    if authorization and authorization.lower().startswith("bearer "):\n        token = authorization.split(" ", 1)[1].strip()\n        payload = verify_session_token(token)\n\n        if payload:\n            discord_id = str(payload.get("discord_id") or actor_discord_id)\n            avatar = payload.get("avatar")\n            avatar_url = None\n\n            if avatar:\n                ext = "gif" if str(avatar).startswith("a_") else "png"\n                avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.{ext}?size=128"\n\n            user = {\n                "discord_id": discord_id,\n                "username": payload.get("username"),\n                "global_name": payload.get("global_name"),\n                "avatar": avatar,\n                "avatar_url": avatar_url,\n            }\n\n    return {\n        "authenticated": True,\n        "discord_id": str(actor_discord_id),\n        "user": user,\n        "is_staff": is_staff(actor_discord_id),\n    }\n'
NEW_AUTH_USER_BLOCK = '          <div className="auth-user">\n            {authUser?.avatar_url ? (\n              <img\n                src={authUser.avatar_url}\n                alt="Discord avatar"\n                className="auth-avatar"\n              />\n            ) : null}\n\n            <span>{authUser ? "Logged in with Discord" : "Login"}</span>\n\n            <strong>\n              {authUser\n                ? authUser.global_name || authUser.username || authUser.discord_id || discordId\n                : "Use Discord OAuth"}\n            </strong>\n\n            {authUser?.username ? (\n              <small>@{authUser.username}</small>\n            ) : discordId ? (\n              <small>Discord ID: {discordId}</small>\n            ) : null}\n          </div>'
CSS_APPEND = '/* Discord profile display */\n\n.auth-avatar {\n  width: 56px;\n  height: 56px;\n  border-radius: 999px;\n  object-fit: cover;\n  border: 2px solid rgba(61, 51, 43, 0.12);\n  margin-bottom: 0.35rem;\n  box-shadow: 0 8px 20px rgba(44, 31, 22, 0.12);\n}\n\n.auth-user small {\n  color: rgba(44, 31, 22, 0.62);\n  font-weight: 700;\n}\n'


def backup(path: Path, suffix: str) -> None:
    backup_path = path.with_suffix(path.suffix + suffix)
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def find_python_function(text: str, function_name: str) -> tuple[int, int]:
    marker = "def " + function_name + "("
    start = text.find(marker)
    if start == -1:
        raise RuntimeError("Could not find function " + function_name + ".")

    decorator_start = text.rfind("\n@router.", 0, start)
    if decorator_start != -1:
        line_after_decorator = text.find("\n", decorator_start + 1)
        if line_after_decorator != -1 and line_after_decorator < start:
            start = decorator_start + 1

    next_route = text.find("\n@router.", start + 1)
    next_def = text.find("\ndef ", start + 1)
    candidates = [idx for idx in [next_route, next_def] if idx != -1]
    end = min(candidates) + 1 if candidates else len(text)

    return start, end


def find_matching_tag_end(text: str, start: int, tag: str = "div") -> int:
    open_token = "<" + tag
    close_token = "</" + tag + ">"

    pos = start
    depth = 0

    while pos < len(text):
        next_open = text.find(open_token, pos)
        next_close = text.find(close_token, pos)

        if next_close == -1:
            raise RuntimeError("Could not find closing tag.")

        if next_open != -1 and next_open < next_close:
            depth += 1
            tag_end = text.find(">", next_open)
            if tag_end == -1:
                raise RuntimeError("Malformed opening tag.")
            pos = tag_end + 1
            continue

        depth -= 1
        pos = next_close + len(close_token)

        if depth == 0:
            return pos

    raise RuntimeError("Could not find matching closing tag.")


def patch_auth_py() -> None:
    text = AUTH_PATH.read_text(encoding="utf-8")
    original = text
    backup(AUTH_PATH, ".profile_display.bak")

    if "from fastapi import APIRouter, Depends, HTTPException, Query, Header" not in text:
        text = text.replace(
            "from fastapi import APIRouter, Depends, HTTPException, Query",
            "from fastapi import APIRouter, Depends, HTTPException, Query, Header",
            1,
        )

    start, end = find_python_function(text, "auth_me")
    text = text[:start] + NEW_AUTH_ME.rstrip() + "\n" + text[end:]

    if text != original:
        AUTH_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/routes/auth.py")
    else:
        print("backend/app/routes/auth.py already patched")


def patch_main_tsx() -> None:
    text = MAIN_TSX_PATH.read_text(encoding="utf-8")
    original = text
    backup(MAIN_TSX_PATH, ".profile_display.bak")

    start = text.find('<div className="auth-user">')
    if start == -1:
        raise RuntimeError('Could not find <div className="auth-user"> in frontend/src/main.tsx.')

    end = find_matching_tag_end(text, start, "div")
    text = text[:start] + NEW_AUTH_USER_BLOCK + text[end:]

    if text != original:
        MAIN_TSX_PATH.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
    else:
        print("frontend/src/main.tsx already patched")


def patch_css() -> None:
    text = CSS_PATH.read_text(encoding="utf-8")
    original = text
    backup(CSS_PATH, ".profile_display.bak")

    if "Discord profile display" not in text:
        text = text.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n"

    if text != original:
        CSS_PATH.write_text(text, encoding="utf-8")
        print("Patched frontend/src/styles.css")
    else:
        print("frontend/src/styles.css already has profile display CSS")


def main() -> None:
    patch_auth_py()
    patch_main_tsx()
    patch_css()

    print("")
    print("Done. Restart backend/frontend, logout if needed, then Login with Discord again.")


if __name__ == "__main__":
    main()
