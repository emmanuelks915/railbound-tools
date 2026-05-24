
from __future__ import annotations

from pathlib import Path


AUTH_PATH = Path("backend/app/routes/auth.py")


def main() -> None:
    text = AUTH_PATH.read_text(encoding="utf-8")
    original = text

    backup_path = AUTH_PATH.with_suffix(".py.oauth_403_fix.bak")
    if not backup_path.exists():
        backup_path.write_text(text, encoding="utf-8")

    if "import urllib.error" not in text:
        text = text.replace("import urllib.request\n", "import urllib.request\nimport urllib.error\n", 1)

    text = text.replace(
        '''        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
''',
        '''        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "RailboundToolsOAuth/1.0",
        },
''',
        1,
    )

    text = text.replace(
        '''        headers={"Authorization": f"Bearer {bearer_token}", "Accept": "application/json"},
''',
        '''        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
            "User-Agent": "RailboundToolsOAuth/1.0",
        },
''',
        1,
    )

    old = '''    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Discord OAuth callback failed: {exc}") from exc
'''
    new = '''    except urllib.error.HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            error_body = str(exc)

        raise HTTPException(
            status_code=400,
            detail=f"Discord OAuth callback failed: HTTP {exc.code}: {error_body}",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Discord OAuth callback failed: {exc}") from exc
'''

    if old in text:
        text = text.replace(old, new, 1)
    elif "HTTP {exc.code}" not in text:
        print("WARNING: Could not find callback exception block to patch.")

    if text != original:
        AUTH_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/routes/auth.py")
        print(f"Backup saved as {backup_path}")
    else:
        print("No changes made. auth.py may already be patched.")

    print("")
    print("Restart backend, then click Login with Discord again from the frontend.")
    print("If it still fails, the browser JSON will now show Discord's exact error body.")


if __name__ == "__main__":
    main()
