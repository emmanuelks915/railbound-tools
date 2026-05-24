
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path.cwd()
CONFIG_PATH = ROOT / "backend" / "app" / "config.py"
SECURITY_PATH = ROOT / "backend" / "app" / "security.py"
AUTH_TOKENS_PATH = ROOT / "backend" / "app" / "auth_tokens.py"
AUTH_ROUTE_PATH = ROOT / "backend" / "app" / "routes" / "auth.py"
MAIN_PATH = ROOT / "backend" / "app" / "main.py"
ENV_EXAMPLE_PATH = ROOT / "backend" / ".env.example"
FRONTEND_MAIN = ROOT / "frontend" / "src" / "main.tsx"
FRONTEND_CSS = ROOT / "frontend" / "src" / "styles.css"

AUTH_TOKENS = 'from __future__ import annotations\n\nimport base64\nimport hashlib\nimport hmac\nimport json\nimport time\nfrom typing import Any\n\nfrom app.config import get_settings\n\n\ndef _b64encode(raw: bytes) -> str:\n    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")\n\n\ndef _b64decode(raw: str) -> bytes:\n    padding = "=" * (-len(raw) % 4)\n    return base64.urlsafe_b64decode(raw + padding)\n\n\ndef create_session_token(payload: dict[str, Any], *, max_age_seconds: int = 60 * 60 * 24 * 7) -> str:\n    settings = get_settings()\n    now = int(time.time())\n    body = {**payload, "iat": now, "exp": now + max_age_seconds}\n\n    encoded_payload = _b64encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))\n    signature = hmac.new(\n        settings.auth_session_secret.encode("utf-8"),\n        encoded_payload.encode("utf-8"),\n        hashlib.sha256,\n    ).digest()\n\n    return f"{encoded_payload}.{_b64encode(signature)}"\n\n\ndef verify_session_token(token: str | None) -> dict[str, Any] | None:\n    if not token or "." not in token:\n        return None\n\n    settings = get_settings()\n    encoded_payload, supplied_signature = token.split(".", 1)\n\n    expected_signature = hmac.new(\n        settings.auth_session_secret.encode("utf-8"),\n        encoded_payload.encode("utf-8"),\n        hashlib.sha256,\n    ).digest()\n\n    try:\n        supplied_bytes = _b64decode(supplied_signature)\n    except Exception:\n        return None\n\n    if not hmac.compare_digest(expected_signature, supplied_bytes):\n        return None\n\n    try:\n        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))\n    except Exception:\n        return None\n\n    expires_at = int(payload.get("exp") or 0)\n    if expires_at and expires_at < int(time.time()):\n        return None\n\n    return payload\n'
AUTH_ROUTE = 'from __future__ import annotations\n\nimport json\nimport secrets\nimport urllib.parse\nimport urllib.request\nfrom typing import Any\n\nfrom fastapi import APIRouter, Depends, HTTPException, Query\nfrom fastapi.responses import RedirectResponse\n\nfrom app.auth_tokens import create_session_token, verify_session_token\nfrom app.config import get_settings\nfrom app.permissions import is_staff\nfrom app.security import actor_from_header\n\nrouter = APIRouter(prefix="/api/auth", tags=["auth"])\n\nDISCORD_AUTH_URL = "https://discord.com/oauth2/authorize"\nDISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"\nDISCORD_ME_URL = "https://discord.com/api/users/@me"\n\n\ndef _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:\n    encoded = urllib.parse.urlencode(data).encode("utf-8")\n    request = urllib.request.Request(\n        url,\n        data=encoded,\n        method="POST",\n        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},\n    )\n    with urllib.request.urlopen(request, timeout=15) as response:\n        return json.loads(response.read().decode("utf-8"))\n\n\ndef _get_json(url: str, *, bearer_token: str) -> dict[str, Any]:\n    request = urllib.request.Request(\n        url,\n        method="GET",\n        headers={"Authorization": f"Bearer {bearer_token}", "Accept": "application/json"},\n    )\n    with urllib.request.urlopen(request, timeout=15) as response:\n        return json.loads(response.read().decode("utf-8"))\n\n\n@router.get("/discord/login")\ndef discord_login():\n    settings = get_settings()\n\n    if not settings.discord_oauth_client_id or not settings.discord_oauth_redirect_uri:\n        raise HTTPException(status_code=500, detail="Discord OAuth is not configured.")\n\n    state = create_session_token(\n        {"purpose": "discord_oauth_state", "nonce": secrets.token_urlsafe(24)},\n        max_age_seconds=10 * 60,\n    )\n\n    params = {\n        "response_type": "code",\n        "client_id": settings.discord_oauth_client_id,\n        "redirect_uri": settings.discord_oauth_redirect_uri,\n        "scope": "identify",\n        "state": state,\n        "prompt": "consent",\n    }\n\n    return RedirectResponse(f"{DISCORD_AUTH_URL}?{urllib.parse.urlencode(params)}")\n\n\n@router.get("/discord/callback")\ndef discord_callback(code: str = Query(...), state: str = Query(...)):\n    settings = get_settings()\n\n    state_payload = verify_session_token(state)\n    if not state_payload or state_payload.get("purpose") != "discord_oauth_state":\n        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")\n\n    if not settings.discord_oauth_client_id or not settings.discord_oauth_client_secret:\n        raise HTTPException(status_code=500, detail="Discord OAuth client ID/secret missing.")\n\n    try:\n        token_data = _post_form(\n            DISCORD_TOKEN_URL,\n            {\n                "client_id": settings.discord_oauth_client_id,\n                "client_secret": settings.discord_oauth_client_secret,\n                "grant_type": "authorization_code",\n                "code": code,\n                "redirect_uri": settings.discord_oauth_redirect_uri,\n            },\n        )\n        access_token = token_data.get("access_token")\n        if not access_token:\n            raise RuntimeError("Discord did not return an access token.")\n\n        discord_user = _get_json(DISCORD_ME_URL, bearer_token=str(access_token))\n    except Exception as exc:\n        raise HTTPException(status_code=400, detail=f"Discord OAuth callback failed: {exc}") from exc\n\n    discord_id = str(discord_user.get("id") or "")\n    if not discord_id:\n        raise HTTPException(status_code=400, detail="Discord did not return a user ID.")\n\n    app_token = create_session_token(\n        {\n            "discord_id": discord_id,\n            "username": discord_user.get("username"),\n            "global_name": discord_user.get("global_name"),\n            "avatar": discord_user.get("avatar"),\n        },\n        max_age_seconds=60 * 60 * 24 * 7,\n    )\n\n    frontend_url = settings.frontend_url.rstrip("/")\n    return RedirectResponse(f"{frontend_url}/#auth_token={urllib.parse.quote(app_token)}")\n\n\n@router.get("/me")\ndef auth_me(actor_discord_id: int | None = Depends(actor_from_header)):\n    if actor_discord_id is None:\n        return {"authenticated": False, "discord_id": None, "user": None, "is_staff": False}\n\n    return {\n        "authenticated": True,\n        "discord_id": str(actor_discord_id),\n        "user": {"discord_id": str(actor_discord_id)},\n        "is_staff": is_staff(actor_discord_id),\n    }\n'
SECURITY = 'from __future__ import annotations\n\nfrom fastapi import Header, HTTPException\n\nfrom app.auth_tokens import verify_session_token\nfrom app.config import get_settings\n\n\ndef _actor_from_bearer(authorization: str | None) -> int | None:\n    if not authorization:\n        return None\n\n    parts = authorization.strip().split(" ", 1)\n    if len(parts) != 2 or parts[0].lower() != "bearer":\n        return None\n\n    payload = verify_session_token(parts[1].strip())\n    if not payload:\n        return None\n\n    discord_id = str(payload.get("discord_id") or "").strip()\n    if not discord_id.isdigit():\n        return None\n\n    return int(discord_id)\n\n\ndef actor_from_header(\n    x_discord_id: int | None = Header(default=None, alias="X-Discord-Id"),\n    authorization: str | None = Header(default=None, alias="Authorization"),\n) -> int | None:\n    bearer_actor = _actor_from_bearer(authorization)\n    if bearer_actor is not None:\n        return bearer_actor\n    return x_discord_id\n\n\ndef require_staff(actor_discord_id: int | None) -> int:\n    if actor_discord_id is None:\n        raise HTTPException(status_code=401, detail="Missing Discord identity.")\n\n    if actor_discord_id not in get_settings().staff_ids:\n        raise HTTPException(status_code=403, detail="Staff access required.")\n\n    return actor_discord_id\n'
CSS_APPEND = '/* Discord OAuth login */\n\n.auth-box {\n  display: grid;\n  gap: 0.6rem;\n  align-content: start;\n  min-width: min(340px, 100%);\n  border-radius: 22px;\n  padding: 1rem;\n  background: rgba(255, 255, 255, 0.68);\n  border: 1px solid rgba(61, 51, 43, 0.1);\n  box-shadow: 0 12px 30px rgba(44, 31, 22, 0.08);\n}\n\n.auth-user {\n  display: flex;\n  flex-direction: column;\n  gap: 0.15rem;\n}\n\n.auth-user span,\n.auth-dev-login span {\n  font-size: 0.75rem;\n  font-weight: 900;\n  letter-spacing: 0.04em;\n  text-transform: uppercase;\n  color: rgba(44, 31, 22, 0.58);\n}\n\n.auth-user strong {\n  font-size: 1rem;\n}\n\n.auth-actions {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 0.55rem;\n}\n\n.auth-dev-login {\n  display: grid;\n  gap: 0.35rem;\n  margin-top: 0.35rem;\n  padding-top: 0.7rem;\n  border-top: 1px solid rgba(61, 51, 43, 0.1);\n}\n\n.auth-dev-login input {\n  width: 100%;\n}\n'


def backup(path: Path, suffix: str) -> None:
    if not path.exists():
        return
    backup_path = path.with_suffix(path.suffix + suffix)
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def write_new_or_replace(path: Path, content: str, suffix: str) -> None:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            print(f"{path} already up to date")
            return
        backup(path, suffix)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")


def patch_config() -> None:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    original = text
    backup(CONFIG_PATH, ".oauth.bak")

    lines_to_add = [
        '    discord_oauth_client_id: str = ""',
        '    discord_oauth_client_secret: str = ""',
        '    discord_oauth_redirect_uri: str = "http://localhost:8000/api/auth/discord/callback"',
        '    frontend_url: str = "http://localhost:5173"',
        '    auth_session_secret: str = "dev-change-me"',
    ]

    missing = [line for line in lines_to_add if line.split(":")[0].strip() not in text]
    if missing:
        marker = "    model_config = SettingsConfigDict"
        if marker not in text:
            raise RuntimeError("Could not find Settings model_config marker in backend/app/config.py")
        text = text.replace(marker, "\n".join(missing) + "\n" + marker, 1)

    if text != original:
        CONFIG_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/config.py")
    else:
        print("backend/app/config.py already has OAuth settings")


def patch_main() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text
    backup(MAIN_PATH, ".oauth.bak")

    import_match = re.search(r"from app\.routes import ([^\n]+)", text)
    if import_match:
        imports = [item.strip() for item in import_match.group(1).split(",")]
        if "auth" not in imports:
            imports.append("auth")
            text = text[:import_match.start()] + "from app.routes import " + ", ".join(imports) + text[import_match.end():]
    elif "from app.routes import auth" not in text:
        lines = text.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_at = i + 1
        lines.insert(insert_at, "from app.routes import auth")
        text = "\n".join(lines) + ("\n" if original.endswith("\n") else "")

    if "app.include_router(auth.router)" not in text:
        include_matches = list(re.finditer(r"app\.include_router\([^\n]+\)", text))
        if include_matches:
            last = include_matches[-1]
            text = text[:last.end()] + "\napp.include_router(auth.router)" + text[last.end():]
        else:
            text = text.rstrip() + "\napp.include_router(auth.router)\n"

    if text != original:
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/main.py")
    else:
        print("backend/app/main.py already includes auth router")


def patch_env_example() -> None:
    if not ENV_EXAMPLE_PATH.exists():
        return

    text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    original = text
    backup(ENV_EXAMPLE_PATH, ".oauth.bak")

    block = "\n".join([
        "# Discord OAuth login",
        "DISCORD_OAUTH_CLIENT_ID=",
        "DISCORD_OAUTH_CLIENT_SECRET=",
        "DISCORD_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/discord/callback",
        "FRONTEND_URL=http://localhost:5173",
        "AUTH_SESSION_SECRET=change-me-use-a-long-random-string",
    ])

    if "DISCORD_OAUTH_CLIENT_ID" not in text:
        text = text.rstrip() + "\n\n" + block + "\n"

    if text != original:
        ENV_EXAMPLE_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/.env.example")
    else:
        print("backend/.env.example already has OAuth vars")


def patch_frontend_api_fetch(text: str) -> str:
    if 'headers.set("Authorization", `Bearer ${authToken}`);' in text:
        return text

    needle = """  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (discordId) headers.set("X-Discord-Id", discordId);"""

    replacement = """  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  const authToken = localStorage.getItem("railbound_auth_token");
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);

  if (discordId) headers.set("X-Discord-Id", discordId);"""

    if needle not in text:
        print("WARNING: Could not find apiFetch header block. Skipping apiFetch auth-token patch.")
        return text

    return text.replace(needle, replacement, 1)


def patch_frontend_app_state(text: str) -> str:
    if "authUser, setAuthUser" not in text:
        needle = """  const [tab, setTab] = useState<Tab>("home");
  const [discordId, setDiscordId] = useState(() => localStorage.getItem("railbound_discord_id") || "");"""

        replacement = """  const [tab, setTab] = useState<Tab>("home");
  const [authUser, setAuthUser] = useState<any>(null);
  const [discordId, setDiscordId] = useState(() => localStorage.getItem("railbound_discord_id") || "");"""

        if needle in text:
            text = text.replace(needle, replacement, 1)
        else:
            print("WARNING: Could not find App state block. Skipping authUser state patch.")

    if "function logoutDiscord" not in text:
        needle = """  useEffect(() => {
    localStorage.setItem("railbound_character_id", selectedCharacterId);
  }, [selectedCharacterId]);"""

        replacement = """  useEffect(() => {
    localStorage.setItem("railbound_character_id", selectedCharacterId);
  }, [selectedCharacterId]);

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const authToken = hash.get("auth_token");

    if (authToken) {
      localStorage.setItem("railbound_auth_token", authToken);
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }

    const existingToken = authToken || localStorage.getItem("railbound_auth_token");

    if (existingToken || discordId) {
      apiFetch("/api/auth/me", {}, discordId)
        .then((data) => {
          if (data?.authenticated && data.discord_id) {
            setAuthUser(data.user || { discord_id: data.discord_id });
            setDiscordId(String(data.discord_id));
          }
        })
        .catch(() => setAuthUser(null));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loginWithDiscord() {
    window.location.href = `${API_BASE}/api/auth/discord/login`;
  }

  function logoutDiscord() {
    localStorage.removeItem("railbound_auth_token");
    localStorage.removeItem("railbound_discord_id");
    setAuthUser(null);
    setDiscordId("");
  }"""

        if needle in text:
            text = text.replace(needle, replacement, 1)
        else:
            print("WARNING: Could not find selectedCharacter localStorage effect. Skipping auth useEffect patch.")

    return text


def patch_frontend_login_box(text: str) -> str:
    if 'className="auth-box"' in text:
        return text

    pattern = re.compile(
        r"""\n\s*<label className="discord-id-box">\s*\n\s*<span>Testing Login</span>\s*\n\s*<input\s*\n\s*value=\{discordId\}\s*\n\s*onChange=\{\(event\) => setDiscordId\(event\.target\.value\)\}\s*\n\s*placeholder="Paste Discord ID for local testing"\s*\n\s*/>\s*\n\s*</label>""",
        re.MULTILINE,
    )

    replacement = """
        <div className="auth-box">
          <div className="auth-user">
            <span>{authUser ? "Logged in with Discord" : "Login"}</span>
            <strong>
              {authUser
                ? authUser.global_name || authUser.username || authUser.discord_id || discordId
                : "Use Discord OAuth"}
            </strong>
            {discordId ? <small>Discord ID: {discordId}</small> : null}
          </div>

          <div className="auth-actions">
            {!authUser ? (
              <button type="button" onClick={loginWithDiscord}>
                Login with Discord
              </button>
            ) : (
              <button type="button" className="ghost" onClick={logoutDiscord}>
                Logout
              </button>
            )}
          </div>

          <label className="auth-dev-login">
            <span>Dev fallback</span>
            <input
              value={discordId}
              onChange={(event) => setDiscordId(event.target.value)}
              placeholder="Paste Discord ID for local testing"
            />
          </label>
        </div>"""

    text2, count = pattern.subn(replacement, text, count=1)
    if count == 0:
        print("WARNING: Could not find Testing Login label. Skipping OAuth login UI patch.")
        return text

    return text2


def patch_frontend() -> None:
    text = FRONTEND_MAIN.read_text(encoding="utf-8")
    original = text
    backup(FRONTEND_MAIN, ".oauth.bak")

    text = patch_frontend_api_fetch(text)
    text = patch_frontend_app_state(text)
    text = patch_frontend_login_box(text)

    if text != original:
        FRONTEND_MAIN.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
    else:
        print("frontend/src/main.tsx unchanged")

    css = FRONTEND_CSS.read_text(encoding="utf-8")
    if "Discord OAuth login" not in css:
        backup(FRONTEND_CSS, ".oauth.bak")
        FRONTEND_CSS.write_text(css.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n", encoding="utf-8")
        print("Patched frontend/src/styles.css")
    else:
        print("frontend/src/styles.css already has OAuth CSS")


def main() -> None:
    write_new_or_replace(AUTH_TOKENS_PATH, AUTH_TOKENS, ".oauth.bak")
    write_new_or_replace(AUTH_ROUTE_PATH, AUTH_ROUTE, ".oauth.bak")
    write_new_or_replace(SECURITY_PATH, SECURITY, ".oauth.bak")
    patch_config()
    patch_main()
    patch_env_example()
    patch_frontend()
    print("")
    print("Done. Add OAuth env vars, restart backend/frontend, then test Login with Discord.")


if __name__ == "__main__":
    main()
