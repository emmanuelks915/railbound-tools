# Disable Dev Login for Production

This patch makes the manual Discord ID fallback local-only.

## What it changes

Backend:

- Adds `ALLOW_DEV_LOGIN=false` config
- Backend ignores `X-Discord-Id` unless `ALLOW_DEV_LOGIN=true`
- OAuth `Authorization: Bearer ...` still works normally

Frontend:

- Adds `VITE_ALLOW_DEV_LOGIN=false`
- Hides the manual "Dev fallback" box unless `VITE_ALLOW_DEV_LOGIN=true`
- Only sends `X-Discord-Id` if dev login is enabled

## Run from project root

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\disable_dev_login_for_production_patch.zip" -DestinationPath . -Force
python patch_disable_dev_login_for_production.py
```

## Set local env values

In `backend\.env`, add:

```env
ALLOW_DEV_LOGIN=false
```

In `frontend\.env`, add:

```env
VITE_ALLOW_DEV_LOGIN=false
```

If you ever need the manual fallback locally, set both to `true`, then restart backend and frontend.

## Restart

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd ..\frontend
npm run dev
```

## Test

- You should only see the Discord OAuth login/profile box.
- The Dev fallback input should be hidden.
- Logged-in OAuth pages should still work.

## Commit

```powershell
git add backend/app/config.py backend/app/security.py backend/.env.example frontend/.env.example frontend/src/main.tsx
git commit -m "Disable dev login outside local mode"
git push
```
