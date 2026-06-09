"""
weather_routes.py  —  add to your existing FastAPI app

Mount with:
    from weather_routes import router as weather_router
    app.include_router(weather_router, prefix="/api/weather", tags=["weather"])

Requires env vars:
    DISCORD_BOT_TOKEN
    DISCORD_WEATHER_CHANNEL_ID
    SUPABASE_URL
    SUPABASE_SERVICE_KEY        (service role — bypasses RLS)
"""

import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import date

router = APIRouter()

DISCORD_TOKEN      = os.getenv("DISCORD_BOT_TOKEN")
WEATHER_CHANNEL_ID = os.getenv("DISCORD_WEATHER_CHANNEL_ID")
SUPABASE_URL       = os.getenv("SUPABASE_URL")
SUPABASE_KEY       = os.getenv("SUPABASE_SERVICE_KEY")


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    return create_client(url, key)

# ── condition display metadata ──────────────────────────────────────────────

CONDITION_EMOJI = {
    "CLEAR":          "☀️",
    "OVERCAST":       "☁️",
    "HEAVY_RAIN":     "🌧️",
    "THUNDERSTORM":   "⛈️",
    "FOG":            "🌫️",
    "SANDSTORM":      "🌪️",
    "BLIZZARD":       "❄️",
    "ICE_STORM":      "🧊",
    "HEATWAVE":       "🔥",
    "GALE":           "💨",
    "NAMED_STORM":    "⚠️",
    "SOURCE_ANOMALY": "✨",
}

INTENSITY_COLOR = {
    "LIGHT":    0x639922,   # green
    "MODERATE": 0xBA7517,   # amber
    "SEVERE":   0xE24B4A,   # red
}

REGION_LABELS = {
    "lumenhold":     "Lumenhold",
    "flywheel":      "Flywheel",
    "cinder":        "Cinder",
    "high_sable":    "High Sable",
    "gearford":      "Gearford",
    "thornwick":     "Thornwick",
    "ashgate":       "Ashgate",
    "morthand":      "Morthand",
    "brassmere":     "Brassmere",
    "citadel":       "The Citadel",
    "ragged_signal": "Ragged Signal",
    "gilded_index":  "Gilded Index",
    "black_spur":    "Black Spur",
    "iron_covenant": "Iron Covenant",
    "outlands":      "The Outlands",
}

# ── helpers ─────────────────────────────────────────────────────────────────

def build_effects_string(effects: dict) -> str:
    """Turn effects JSON into a readable modifier string."""
    if not effects:
        return "No mechanical effects this week."
    parts = []
    labels = {
        "ranged_accuracy":   "Ranged accuracy",
        "stamina_outdoor":   "Stamina (outdoors)",
        "stamina_indoor":    "Stamina (indoors)",
        "perception":        "Perception",
        "movement":          "Movement",
        "travel_penalty":    "Travel time",
    }
    for key, val in effects.items():
        label = labels.get(key, key.replace("_", " ").title())
        sign = "+" if val > 0 else ""
        unit = " day(s)" if key == "travel_penalty" else ""
        parts.append(f"`{label}: {sign}{val}{unit}`")
    return "  ".join(parts)


def build_embed(row: dict) -> dict:
    """Build a single Discord embed for one region's forecast."""
    condition   = row["condition"]
    intensity   = row["intensity"]
    emoji       = CONDITION_EMOJI.get(condition, "🌡️")
    color       = INTENSITY_COLOR.get(intensity, 0x888780)

    # Override color for special conditions
    if row.get("is_source_anomaly"):
        color = 0x1D9E75
    elif condition == "NAMED_STORM":
        color = 0xE24B4A

    title = f"{emoji}  {row['forecast_title'] or REGION_LABELS.get(row['region'], row['region'])}"

    fields = []

    if row.get("forecast_body"):
        fields.append({
            "name": "Forecast",
            "value": row["forecast_body"][:1024],
            "inline": False,
        })

    effects_str = build_effects_string(row.get("effects") or {})
    fields.append({
        "name": "Mechanical effects",
        "value": effects_str,
        "inline": False,
    })

    badges = []
    if row.get("is_indefinite"):
        badges.append("📌 Indefinite — ongoing arc event")
    if row.get("is_source_anomaly"):
        badges.append("✨ Source anomaly")
    if badges:
        fields.append({"name": "Flags", "value": "\n".join(badges), "inline": False})

    return {
        "title":  title,
        "color":  color,
        "fields": fields,
        "footer": {
            "text": f"{REGION_LABELS.get(row['region'], row['region'])}  •  {intensity.title()}  •  {row['short_desc'] or ''}",
        },
    }


async def discord_request(method: str, path: str, **kwargs):
    """Thin wrapper around Discord REST API."""
    url = f"https://discord.com/api/v10{path}"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


# ── routes ───────────────────────────────────────────────────────────────────

class PostWeatherRequest(BaseModel):
    weekStart: str
    staffName: str = "Staff"


@router.post("/post-discord")
async def post_weather_to_discord(body: PostWeatherRequest):
    """
    Fetches all active conditions for the given week and posts
    a formatted embed per region to #weather-forecast.
    If a discord_message_id exists, edits the old message instead
    of posting a new one (keeps the channel clean).
    """
    # 1. Fetch all active conditions for this week
    result = (
        get_supabase().table("weather_conditions")
        .select("*")
        .eq("week_start", body.weekStart)
        .eq("is_active", True)
        .execute()
    )
    rows = result.data
    if not rows:
        raise HTTPException(status_code=400, detail="No forecasts set for this week.")

    # 2. Build the header message content
    week_dt = date.fromisoformat(body.weekStart)
    header = (
        f"# 🌍  Weekly weather forecast\n"
        f"**Week of {week_dt.strftime('%B %d, %Y')}**  —  posted by {body.staffName}\n"
        f"*Travel and combat modifiers are active from Monday through Sunday.*"
    )

    # 3. Group: named storms and anomalies first, then alphabetical
    def sort_key(r):
        priority = 0 if r["condition"] in ("NAMED_STORM", "SOURCE_ANOMALY") else 1
        return (priority, r["region"])

    rows_sorted = sorted(rows, key=sort_key)
    embeds = [build_embed(r) for r in rows_sorted]

    # Discord allows max 10 embeds per message — split if needed
    embed_chunks = [embeds[i:i+10] for i in range(0, len(embeds), 10)]

    # 4. Post or edit
    message_ids = []
    for i, chunk in enumerate(embed_chunks):
        content = header if i == 0 else ""
        payload = {"content": content, "embeds": chunk}

        # Check if any row already has a stored message id for this chunk
        stored_id = rows_sorted[0].get("discord_message_id") if i == 0 else None

        if stored_id:
            try:
                await discord_request(
                    "PATCH",
                    f"/channels/{WEATHER_CHANNEL_ID}/messages/{stored_id}",
                    json=payload,
                )
                message_ids.append(stored_id)
                continue
            except httpx.HTTPStatusError:
                pass  # message was deleted; fall through to new post

        posted = await discord_request(
            "POST",
            f"/channels/{WEATHER_CHANNEL_ID}/messages",
            json=payload,
        )
        message_ids.append(posted["id"])

    # 5. Store the first message ID back to supabase so we can edit next time
    if message_ids:
        get_supabase().table("weather_conditions").update(
            {"discord_message_id": message_ids[0]}
        ).eq("week_start", body.weekStart).eq("is_active", True).execute()

    return {"ok": True, "message_ids": message_ids, "regions_posted": len(rows)}


@router.post("/roll")
async def roll_forecast(season: str = "spring", week_start: str = None):
    """Trigger the DB roll function. Falls back to seeding blank rows if RPC not available."""
    from datetime import date, timedelta
    ws = week_start or (date.today() + timedelta(days=7 - date.today().weekday())).isoformat()
    sb = get_supabase()

    REGIONS_LIST = [
        "lumenhold","flywheel","cinder","high_sable","gearford","thornwick",
        "ashgate","morthand","brassmere","citadel","ragged_signal","gilded_index",
        "black_spur","iron_covenant","outlands"
    ]

    # Try the RPC first (requires migration to have been run)
    try:
        result = sb.rpc("roll_weekly_forecast", {
            "p_season": season,
            "p_week_start": ws,
        }).execute()
        return {"ok": True, "rows": result.data}
    except Exception:
        pass

    # Fallback: upsert blank OVERCAST rows so the dashboard shows region names
    rows = []
    for region in REGIONS_LIST:
        row = {
            "region": region,
            "condition": "OVERCAST",
            "intensity": "MODERATE",
            "forecast_title": f"{region.replace('_', ' ').title()} — pending review",
            "forecast_body": "Auto-seeded. Edit before posting.",
            "short_desc": "Forecast pending staff review.",
            "effects": {},
            "week_start": ws,
            "set_by": "system",
            "is_active": True,
        }
        rows.append(row)

    result = sb.table("weather_conditions").upsert(rows, on_conflict="region,week_start").execute()
    return {"ok": True, "rows": result.data, "note": "Seeded blank rows — run SQL migration to enable dice-table rolling"}


@router.get("/current")
async def get_current_weather(region: str = None):
    """
    Public endpoint — used by the interactive map and player dashboard.
    Returns active conditions for the current week.
    """
    today = date.today()
    # Monday of current week
    week_start = today - __import__("datetime").timedelta(days=today.weekday())

    query = (
        get_supabase().table("weather_conditions")
        .select("region,condition,intensity,forecast_title,short_desc,effects,is_source_anomaly,is_indefinite")
        .eq("week_start", week_start.isoformat())
        .eq("is_active", True)
    )
    if region:
        query = query.eq("region", region)

    result = query.execute()
    return {"week_start": week_start.isoformat(), "conditions": result.data}


@router.get("/conditions")
async def get_conditions(week_start: str = None):
    """Fetch active conditions for a given week (staff dashboard)."""
    from datetime import date
    ws = week_start or date.today().isoformat()
    result = (
        get_supabase().table("weather_conditions")
        .select("*")
        .eq("week_start", ws)
        .eq("is_active", True)
        .execute()
    )
    return {"conditions": result.data}


@router.post("/conditions")
async def create_condition(payload: dict):
    """Create or upsert a weather condition."""
    result = get_supabase().table("weather_conditions").upsert(
        payload, on_conflict="region,week_start"
    ).execute()
    return {"ok": True, "data": result.data}


@router.patch("/conditions/{condition_id}")
async def update_condition(condition_id: str, payload: dict):
    """Update an existing weather condition."""
    result = get_supabase().table("weather_conditions").update(payload).eq("id", condition_id).execute()
    return {"ok": True, "data": result.data}


@router.post("/archive")
async def archive_week():
    """Archive current week conditions."""
    result = get_supabase().rpc("archive_current_week").execute()
    return {"ok": True, "archived": result.data}
