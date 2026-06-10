"""
weather_cron.py — add to backend/app/routes/

Provides a /api/weather/cron/weekly endpoint that:
1. Auto-posts the current week's forecast to Discord
2. Called by Railway's cron job every Monday at 9am UTC

Set up in Railway:
  Service → Settings → Cron Jobs
  Schedule: 0 9 * * 1   (every Monday 9am UTC)
  Command:  curl -X POST https://your-backend.railway.app/api/weather/cron/weekly \
              -H "X-Cron-Secret: $CRON_SECRET"
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Header
from datetime import date, timedelta

router = APIRouter(prefix="/api/weather/cron", tags=["weather-cron"])

CRON_SECRET = os.getenv("CRON_SECRET", "")


def get_current_season() -> str:
    m = date.today().month
    d = date.today().day
    if (m == 3 and d >= 20) or m in (4, 5) or (m == 6 and d <= 20):
        return "spring"
    if (m == 6 and d >= 21) or m in (7, 8) or (m == 9 and d <= 21):
        return "summer"
    if (m == 9 and d >= 22) or m in (10, 11) or (m == 12 and d <= 20):
        return "autumn"
    return "winter"


@router.post("/weekly")
async def weekly_auto_post(x_cron_secret: str = Header(default="")):
    """
    Called by Railway cron every Monday morning.
    Posts the current week's forecast to Discord automatically.
    """
    if CRON_SECRET and x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    # Current week start (Monday)
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    season = get_current_season()

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: roll if nothing set yet
        conditions_resp = await client.get(
            f"{backend_url}/api/weather/conditions",
            params={"week_start": week_start},
        )
        conditions = conditions_resp.json().get("conditions", [])

        if len(conditions) < 15:
            await client.post(
                f"{backend_url}/api/weather/roll",
                params={"season": season, "week_start": week_start},
            )

        # Step 2: post to Discord
        post_resp = await client.post(
            f"{backend_url}/api/weather/post-discord",
            json={"weekStart": week_start, "staffName": f"Auto ({season.title()})"},
        )
        post_data = post_resp.json()

    return {
        "ok": True,
        "week_start": week_start,
        "season": season,
        "discord": post_data,
    }
