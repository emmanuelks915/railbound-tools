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

router = APIRouter(prefix="/api/weather", tags=["weather"])

DISCORD_TOKEN      = os.getenv("DISCORD_BOT_TOKEN")
WEATHER_CHANNEL_ID = os.getenv("DISCORD_WEATHER_CHANNEL_ID")
SUPABASE_URL       = os.getenv("SUPABASE_URL")
SUPABASE_KEY       = os.getenv("SUPABASE_SERVICE_KEY")


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
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


WIND_LABELS = {
    "CALM": "Calm",
    "LIGHT_BREEZE": "Light breeze",
    "MODERATE_WIND": "Moderate wind",
    "STRONG_WIND": "Strong wind",
    "GALE_FORCE": "Gale force",
}

VISIBILITY_LABELS = {
    "CLEAR": "Clear",
    "HAZY": "Hazy",
    "POOR": "Poor",
    "NEAR_ZERO": "Near zero",
}


def build_embed(row: dict) -> dict:
    """Build a single Discord embed for one region's forecast."""
    condition   = row["condition"]
    intensity   = row["intensity"]
    emoji       = CONDITION_EMOJI.get(condition, "🌡️")
    color       = INTENSITY_COLOR.get(intensity, 0x888780)

    if row.get("is_source_anomaly"):
        color = 0x1D9E75
    elif condition == "NAMED_STORM":
        color = 0xE24B4A

    region_label = REGION_LABELS.get(row["region"], row["region"])
    title = f"{emoji}  {row.get('forecast_title') or region_label}"

    fields = []

    # Forecast body
    if row.get("forecast_body"):
        fields.append({
            "name": "📋  Forecast",
            "value": row["forecast_body"][:1024],
            "inline": False,
        })

    # Temperature, humidity, wind, visibility as inline fields
    temp_low  = row.get("temp_low")
    temp_high = row.get("temp_high")
    humidity  = row.get("humidity")
    wind      = row.get("wind")
    visibility = row.get("visibility")

    if temp_low is not None or temp_high is not None:
        temp_str = ""
        if temp_low is not None and temp_high is not None:
            temp_str = f"🔻 {temp_low}°C  /  🔺 {temp_high}°C"
        elif temp_high is not None:
            temp_str = f"🔺 {temp_high}°C"
        else:
            temp_str = f"🔻 {temp_low}°C"
        fields.append({"name": "🌡️  Temperature", "value": temp_str, "inline": True})

    if humidity is not None:
        fields.append({"name": "💧  Humidity", "value": f"{humidity}%", "inline": True})

    if wind:
        fields.append({"name": "🌬️  Wind", "value": WIND_LABELS.get(wind, wind), "inline": True})

    if visibility:
        fields.append({"name": "👁️  Visibility", "value": VISIBILITY_LABELS.get(visibility, visibility), "inline": True})

    # Mechanical effects
    effects_str = build_effects_string(row.get("effects") or {})
    fields.append({
        "name": "⚔️  Combat & travel effects",
        "value": effects_str,
        "inline": False,
    })

    # Flags
    badges = []
    if row.get("is_indefinite"):
        badges.append("📌 Indefinite — ongoing arc event")
    if row.get("is_source_anomaly"):
        badges.append("✨ Source anomaly")
    if badges:
        fields.append({"name": "⚠️  Flags", "value": "\n".join(badges), "inline": False})

    return {
        "title":  title,
        "color":  color,
        "fields": fields,
        "footer": {
            "text": f"{region_label}  •  {intensity.title()} {condition.replace('_', ' ').title()}  •  {row.get('short_desc') or ''}",
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

    for row in rows:
            try:
                sb.table("weather_conditions").insert(row).execute()
            except Exception:
                sb.table("weather_conditions").update(row).eq("region", row["region"]).eq("week_start", ws).eq("is_active", True).execute()
        result = type("R", (), {"data": rows})()
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
    try:
        result = get_supabase().table("weather_conditions").insert(payload).execute()
    except Exception:
        result = get_supabase().table("weather_conditions").update(payload).eq("region", payload["region"]).eq("week_start", payload["week_start"]).eq("is_active", True).execute()
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


class SuggestWeatherRequest(BaseModel):
    region_id: str
    season: str


CLIMATE_PROFILES = {
    "lumenhold":     {"climate": "Rain shadow desert. Scorching days, freezing nights. Almost no rain. Sandstorms common.", "temp": {"spring": (8,28), "summer": (18,42), "autumn": (6,24), "winter": (-2,12)}},
    "flywheel":      {"climate": "Mountain river basin. Heavy precipitation year-round. Persistent low cloud. Snow above the dam in winter.", "temp": {"spring": (4,14), "summer": (12,22), "autumn": (4,14), "winter": (-4,4)}},
    "cinder":        {"climate": "High mountain pass. Blizzards in winter. Short warm summers. Snowmelt floods in spring. Volcanic warmth near the city.", "temp": {"spring": (0,10), "summer": (8,18), "autumn": (-2,8), "winter": (-10,0)}},
    "high_sable":    {"climate": "Exposed cliff face. Constant wind scour. Brutal winters. Short summer thaw. Fog rolls up from the valley.", "temp": {"spring": (2,10), "summer": (10,18), "autumn": (0,8), "winter": (-8,-2)}},
    "gearford":      {"climate": "Central highland continental. Warm summers, cold winters. Spring storms. Industrial smog creates localized fog.", "temp": {"spring": (6,16), "summer": (14,26), "autumn": (4,14), "winter": (-4,4)}},
    "thornwick":     {"climate": "Dense old-growth frontier forest. Perpetually misty. Cool year-round. Heavy autumn rain. Rare sunny days.", "temp": {"spring": (6,14), "summer": (12,20), "autumn": (4,12), "winter": (-2,6)}},
    "ashgate":       {"climate": "Eastern transition zone. Variable weather from multiple fronts. Warm dry summers. Stormy unpredictable autumn.", "temp": {"spring": (8,18), "summer": (16,28), "autumn": (6,16), "winter": (0,8)}},
    "morthand":      {"climate": "Cold northern coast. Overcast and grey most of the year. Coastal storms. Heavy snow. Short bright summers.", "temp": {"spring": (2,10), "summer": (10,18), "autumn": (0,8), "winter": (-6,2)}},
    "brassmere":     {"climate": "Humid southern coastal port. Frequent sea mist. Hot muggy summers. Industrial smog compounds fog.", "temp": {"spring": (10,20), "summer": (18,30), "autumn": (8,18), "winter": (4,12)}},
    "citadel":       {"climate": "Southeast coast Mediterranean-like. Warmest and driest city. Hot summers, mild winters. Eastern sea storms in autumn.", "temp": {"spring": (12,22), "summer": (20,34), "autumn": (10,20), "winter": (4,14)}},
    "ragged_signal": {"climate": "Exposed southern tip. Open ocean on three sides. Storms arrive fast. Fierce winds year-round.", "temp": {"spring": (8,16), "summer": (14,22), "autumn": (6,14), "winter": (0,8)}},
    "gilded_index":  {"climate": "Western peninsula. Maritime climate. Constant Atlantic wind. Heavy rain in winter, clear breezy summers.", "temp": {"spring": (8,16), "summer": (14,22), "autumn": (6,14), "winter": (2,10)}},
    "black_spur":    {"climate": "Northern forest near the coast. Cold and wet. Frequent sea fog. Heavy snow in winter.", "temp": {"spring": (2,10), "summer": (10,18), "autumn": (0,8), "winter": (-6,2)}},
    "iron_covenant": {"climate": "Eastern forest, inland. Temperate with cold winters. Moderate rainfall year-round.", "temp": {"spring": (4,14), "summer": (12,22), "autumn": (2,12), "winter": (-4,4)}},
    "outlands":      {"climate": "Open wilderness between city-states. Exposed to all weather fronts. Conditions vary wildly.", "temp": {"spring": (4,16), "summer": (12,26), "autumn": (2,14), "winter": (-6,6)}},
}

REGION_ZONES = {
    "lumenhold": "Desert", "flywheel": "Mountain basin", "cinder": "High pass",
    "high_sable": "Cliff face", "gearford": "Central highland", "thornwick": "Deep forest",
    "ashgate": "Eastern transition", "morthand": "Northern coast", "brassmere": "Southern coast",
    "citadel": "Southeast coast", "ragged_signal": "Southern tip", "gilded_index": "Western peninsula",
    "black_spur": "Northern forest", "iron_covenant": "Eastern forest", "outlands": "Wilderness",
}


@router.post("/suggest")
async def suggest_weather(body: SuggestWeatherRequest):
    """Generate a weather suggestion using climate profiles and season weights — no AI needed."""
    import random
    profile = CLIMATE_PROFILES.get(body.region_id)
    if not profile:
        raise HTTPException(status_code=400, detail="Unknown region")

    season = body.season.lower()
    temps = profile["temp"].get(season, (5, 20))
    temp_low, temp_high = temps

    # Season-weighted condition tables per biome
    SEASON_WEIGHTS = {
        "desert":             {"spring": ["CLEAR","CLEAR","SANDSTORM","OVERCAST","HEATWAVE"], "summer": ["CLEAR","CLEAR","HEATWAVE","HEATWAVE","SANDSTORM"], "autumn": ["CLEAR","OVERCAST","SANDSTORM","CLEAR","FOG"], "winter": ["OVERCAST","CLEAR","FOG","HEAVY_RAIN","CLEAR"]},
        "mountain":           {"spring": ["HEAVY_RAIN","OVERCAST","HEAVY_RAIN","FOG","THUNDERSTORM"], "summer": ["OVERCAST","CLEAR","HEAVY_RAIN","THUNDERSTORM","CLEAR"], "autumn": ["HEAVY_RAIN","THUNDERSTORM","OVERCAST","FOG","HEAVY_RAIN"], "winter": ["BLIZZARD","BLIZZARD","ICE_STORM","OVERCAST","HEAVY_RAIN"]},
        "highland":           {"spring": ["OVERCAST","HEAVY_RAIN","CLEAR","BLIZZARD","FOG"], "summer": ["CLEAR","OVERCAST","THUNDERSTORM","CLEAR","HEAVY_RAIN"], "autumn": ["HEAVY_RAIN","OVERCAST","GALE","THUNDERSTORM","FOG"], "winter": ["BLIZZARD","ICE_STORM","BLIZZARD","OVERCAST","GALE"]},
        "cliff":              {"spring": ["GALE","OVERCAST","HEAVY_RAIN","FOG","CLEAR"], "summer": ["CLEAR","GALE","OVERCAST","CLEAR","FOG"], "autumn": ["GALE","HEAVY_RAIN","THUNDERSTORM","OVERCAST","GALE"], "winter": ["ICE_STORM","BLIZZARD","GALE","OVERCAST","ICE_STORM"]},
        "continental":        {"spring": ["OVERCAST","HEAVY_RAIN","THUNDERSTORM","CLEAR","FOG"], "summer": ["CLEAR","CLEAR","THUNDERSTORM","OVERCAST","HEATWAVE"], "autumn": ["HEAVY_RAIN","OVERCAST","THUNDERSTORM","FOG","CLEAR"], "winter": ["OVERCAST","BLIZZARD","ICE_STORM","OVERCAST","HEAVY_RAIN"]},
        "forest":             {"spring": ["FOG","HEAVY_RAIN","OVERCAST","FOG","CLEAR"], "summer": ["OVERCAST","FOG","CLEAR","HEAVY_RAIN","THUNDERSTORM"], "autumn": ["HEAVY_RAIN","FOG","OVERCAST","HEAVY_RAIN","THUNDERSTORM"], "winter": ["FOG","BLIZZARD","OVERCAST","ICE_STORM","HEAVY_RAIN"]},
        "transition":         {"spring": ["OVERCAST","HEAVY_RAIN","CLEAR","THUNDERSTORM","FOG"], "summer": ["CLEAR","CLEAR","HEATWAVE","THUNDERSTORM","OVERCAST"], "autumn": ["THUNDERSTORM","HEAVY_RAIN","GALE","OVERCAST","FOG"], "winter": ["OVERCAST","HEAVY_RAIN","ICE_STORM","CLEAR","BLIZZARD"]},
        "northern coast":     {"spring": ["FOG","HEAVY_RAIN","OVERCAST","THUNDERSTORM","FOG"], "summer": ["OVERCAST","CLEAR","FOG","HEAVY_RAIN","CLEAR"], "autumn": ["HEAVY_RAIN","THUNDERSTORM","GALE","OVERCAST","FOG"], "winter": ["BLIZZARD","ICE_STORM","GALE","OVERCAST","HEAVY_RAIN"]},
        "coastal industrial": {"spring": ["FOG","OVERCAST","HEAVY_RAIN","CLEAR","FOG"], "summer": ["OVERCAST","CLEAR","FOG","THUNDERSTORM","HEATWAVE"], "autumn": ["HEAVY_RAIN","THUNDERSTORM","GALE","FOG","OVERCAST"], "winter": ["OVERCAST","HEAVY_RAIN","FOG","GALE","CLEAR"]},
        "mediterranean":      {"spring": ["CLEAR","OVERCAST","HEAVY_RAIN","CLEAR","THUNDERSTORM"], "summer": ["CLEAR","CLEAR","HEATWAVE","CLEAR","THUNDERSTORM"], "autumn": ["THUNDERSTORM","HEAVY_RAIN","OVERCAST","CLEAR","GALE"], "winter": ["OVERCAST","HEAVY_RAIN","CLEAR","FOG","CLEAR"]},
        "exposed peninsula":  {"spring": ["HEAVY_RAIN","THUNDERSTORM","OVERCAST","FOG","CLEAR"], "summer": ["CLEAR","GALE","THUNDERSTORM","CLEAR","OVERCAST"], "autumn": ["NAMED_STORM","GALE","THUNDERSTORM","HEAVY_RAIN","OVERCAST"], "winter": ["NAMED_STORM","GALE","ICE_STORM","GALE","HEAVY_RAIN"]},
        "maritime":           {"spring": ["HEAVY_RAIN","OVERCAST","GALE","FOG","CLEAR"], "summer": ["CLEAR","CLEAR","OVERCAST","GALE","HEAVY_RAIN"], "autumn": ["HEAVY_RAIN","GALE","THUNDERSTORM","OVERCAST","FOG"], "winter": ["GALE","HEAVY_RAIN","OVERCAST","ICE_STORM","GALE"]},
        "northern forest":    {"spring": ["FOG","HEAVY_RAIN","OVERCAST","FOG","CLEAR"], "summer": ["OVERCAST","CLEAR","FOG","HEAVY_RAIN","CLEAR"], "autumn": ["HEAVY_RAIN","FOG","OVERCAST","THUNDERSTORM","GALE"], "winter": ["BLIZZARD","ICE_STORM","FOG","OVERCAST","HEAVY_RAIN"]},
        "temperate forest":   {"spring": ["OVERCAST","HEAVY_RAIN","FOG","CLEAR","THUNDERSTORM"], "summer": ["CLEAR","OVERCAST","THUNDERSTORM","CLEAR","FOG"], "autumn": ["HEAVY_RAIN","OVERCAST","FOG","THUNDERSTORM","CLEAR"], "winter": ["OVERCAST","BLIZZARD","ICE_STORM","HEAVY_RAIN","FOG"]},
        "wilderness":         {"spring": ["OVERCAST","HEAVY_RAIN","CLEAR","THUNDERSTORM","FOG"], "summer": ["CLEAR","HEATWAVE","THUNDERSTORM","CLEAR","OVERCAST"], "autumn": ["HEAVY_RAIN","GALE","OVERCAST","THUNDERSTORM","FOG"], "winter": ["BLIZZARD","ICE_STORM","OVERCAST","GALE","HEAVY_RAIN"]},
    }

    INTENSITY_WEIGHTS = {
        "CLEAR": "LIGHT", "OVERCAST": "LIGHT", "FOG": "LIGHT",
        "HEAVY_RAIN": "MODERATE", "THUNDERSTORM": "MODERATE", "GALE": "MODERATE",
        "HEATWAVE": "MODERATE", "SANDSTORM": "MODERATE",
        "BLIZZARD": "SEVERE", "ICE_STORM": "SEVERE", "NAMED_STORM": "SEVERE",
    }

    WIND_MAP = {
        "CLEAR": "LIGHT_BREEZE", "OVERCAST": "MODERATE_WIND", "FOG": "CALM",
        "HEAVY_RAIN": "STRONG_WIND", "THUNDERSTORM": "STRONG_WIND", "GALE": "GALE_FORCE",
        "HEATWAVE": "LIGHT_BREEZE", "SANDSTORM": "GALE_FORCE",
        "BLIZZARD": "GALE_FORCE", "ICE_STORM": "STRONG_WIND", "NAMED_STORM": "GALE_FORCE",
    }

    VISIBILITY_MAP = {
        "CLEAR": "CLEAR", "OVERCAST": "HAZY", "FOG": "NEAR_ZERO",
        "HEAVY_RAIN": "POOR", "THUNDERSTORM": "POOR", "GALE": "HAZY",
        "HEATWAVE": "HAZY", "SANDSTORM": "NEAR_ZERO",
        "BLIZZARD": "NEAR_ZERO", "ICE_STORM": "POOR", "NAMED_STORM": "NEAR_ZERO",
    }

    HUMIDITY_MAP = {
        "CLEAR": 30, "OVERCAST": 55, "FOG": 90, "HEAVY_RAIN": 85,
        "THUNDERSTORM": 80, "GALE": 60, "HEATWAVE": 20, "SANDSTORM": 10,
        "BLIZZARD": 70, "ICE_STORM": 75, "NAMED_STORM": 88,
    }

    TITLE_TEMPLATES = {
        "CLEAR": ["Clear Skies", "Blue Horizon", "Fair Weather", "Open Skies"],
        "OVERCAST": ["Grey Ceiling", "Heavy Cloud Cover", "Overcast", "Leaden Skies"],
        "FOG": ["The Thick of It", "Mist and Murk", "Low Visibility", "Morning Fog"],
        "HEAVY_RAIN": ["Downpour", "Heavy Rain", "The Deluge", "Driving Rain"],
        "THUNDERSTORM": ["Thunder Rolls", "Storm Front", "Lightning Season", "The Crackle"],
        "GALE": ["High Winds", "Gale Warning", "The Howl", "Wind Advisory"],
        "HEATWAVE": ["Dry Heat", "The Bake", "Scorching Week", "No Relief"],
        "SANDSTORM": ["The Scouring", "Sand and Grit", "Dust Curtain", "Desert Fury"],
        "BLIZZARD": ["Whiteout", "The Deep Freeze", "Blizzard Conditions", "Buried"],
        "ICE_STORM": ["Ice Lock", "The Glaze", "Freezing Rain", "Black Ice"],
        "NAMED_STORM": ["The Widow's Knell", "Iron Tide", "The Grey Fury", "Blackwater Storm", "The Howling Dark"],
    }

    SHORT_DESC_TEMPLATES = {
        "CLEAR": ["Good traveling weather. Roads are dry.", "Clear skies. No delays expected.", "Favorable conditions across the region."],
        "OVERCAST": ["Dull but passable. Bring a coat.", "No rain yet, but don't count on it.", "Grey skies, manageable roads."],
        "FOG": ["Visibility near zero. Travel with caution.", "Fog blankets the region. Rails only.", "Dense mist. Easy to get turned around."],
        "HEAVY_RAIN": ["Roads are muddy. Expect delays.", "Rivers are swelling. Watch the crossings.", "Wet through and through. Pack dry gear."],
        "THUNDERSTORM": ["Lightning risk outdoors. Seek shelter.", "Flash flood warnings in low areas.", "Storm cells moving fast. Stay alert."],
        "GALE": ["Strong winds. Unsecured cargo will not survive.", "Gale force gusts. Travel hazardous.", "Winds knock you sideways. Brace up."],
        "HEATWAVE": ["Extreme heat. Hydrate or suffer.", "Heat exhaustion risk for outdoor work.", "No shade, no mercy. Travel at night."],
        "SANDSTORM": ["Sandstorm conditions. Stay indoors.", "Visibility zero. Rail only. No exceptions.", "Grit in everything. Eyes and lungs at risk."],
        "BLIZZARD": ["Blizzard conditions. All roads closed.", "Whiteout. Do not travel overland.", "Snow is chest-deep in places. Rail or nothing."],
        "ICE_STORM": ["Ice everywhere. One wrong step.", "Freezing rain coats every surface.", "Dangerous footing. Slow down or don't go."],
        "NAMED_STORM": ["Named storm active. All travel suspended.", "Seek shelter immediately. This is serious.", "The worst of the season. Do not go outside."],
    }

    biome = profile.get("biome", "wilderness")
    table = SEASON_WEIGHTS.get(biome, SEASON_WEIGHTS["wilderness"])
    season_list = table.get(season, table.get("spring", ["OVERCAST"]))
    condition = random.choice(season_list)
    intensity = INTENSITY_WEIGHTS.get(condition, "MODERATE")

    # Small chance to bump severity
    if random.random() < 0.15 and intensity == "MODERATE":
        intensity = "SEVERE"
    elif random.random() < 0.2 and intensity == "LIGHT":
        intensity = "MODERATE"

    title = random.choice(TITLE_TEMPLATES.get(condition, ["Weather Report"]))
    short_desc = random.choice(SHORT_DESC_TEMPLATES.get(condition, ["Conditions vary."]))
    humidity = HUMIDITY_MAP.get(condition, 50) + random.randint(-10, 10)
    humidity = max(0, min(100, humidity))

    # Add slight temp variation
    variation = random.randint(-2, 2)

    suggestion = {
        "condition":      condition,
        "intensity":      intensity,
        "forecast_title": title,
        "short_desc":     short_desc,
        "forecast_body":  "",
        "temp_low":       temp_low + variation,
        "temp_high":      temp_high + variation,
        "humidity":       humidity,
        "wind":           WIND_MAP.get(condition, "MODERATE_WIND"),
        "visibility":     VISIBILITY_MAP.get(condition, "CLEAR"),
    }

    return {"ok": True, "suggestion": suggestion}


