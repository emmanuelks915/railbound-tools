import { useState, useEffect, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path, options = {}, discordId) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const authToken = localStorage.getItem("railbound_auth_token");
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  if (discordId) headers.set("X-Discord-Id", discordId);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}

// ── constants ────────────────────────────────────────────────────────────────

const REGIONS = [
  { id: "lumenhold",    label: "Lumenhold",      zone: "Desert" },
  { id: "flywheel",     label: "Flywheel",        zone: "Mountain basin" },
  { id: "cinder",       label: "Cinder",          zone: "High pass" },
  { id: "high_sable",   label: "High Sable",      zone: "Cliff face" },
  { id: "gearford",     label: "Gearford",        zone: "Central highland" },
  { id: "thornwick",    label: "Thornwick",       zone: "Deep forest" },
  { id: "ashgate",      label: "Ashgate",         zone: "Eastern transition" },
  { id: "morthand",     label: "Morthand",        zone: "Northern coast" },
  { id: "brassmere",    label: "Brassmere",       zone: "Southern coast" },
  { id: "citadel",      label: "The Citadel",     zone: "Southeast coast" },
  { id: "ragged_signal",label: "Ragged Signal",   zone: "Southern tip" },
  { id: "gilded_index", label: "Gilded Index",    zone: "Western peninsula" },
  { id: "black_spur",   label: "Black Spur",      zone: "Northern forest" },
  { id: "iron_covenant",label: "Iron Covenant",   zone: "Eastern forest" },
  { id: "outlands",     label: "Outlands",        zone: "Wilderness" },
];

const CONDITIONS = [
  "CLEAR", "OVERCAST", "HEAVY_RAIN", "THUNDERSTORM",
  "FOG", "SANDSTORM", "BLIZZARD", "ICE_STORM",
  "HEATWAVE", "GALE", "NAMED_STORM", "SOURCE_ANOMALY",
];

const INTENSITIES = ["LIGHT", "MODERATE", "SEVERE"];
const SEASONS = ["spring", "summer", "autumn", "winter"];

const CONDITION_META = {
  CLEAR:          { icon: "ti-sun",           color: "#BA7517" },
  OVERCAST:       { icon: "ti-cloud",         color: "#5F5E5A" },
  HEAVY_RAIN:     { icon: "ti-cloud-rain",    color: "#185FA5" },
  THUNDERSTORM:   { icon: "ti-bolt",          color: "#534AB7" },
  FOG:            { icon: "ti-mist",          color: "#888780" },
  SANDSTORM:      { icon: "ti-wind",          color: "#854F0B" },
  BLIZZARD:       { icon: "ti-snowflake",     color: "#0C447C" },
  ICE_STORM:      { icon: "ti-snowflake",     color: "#185FA5" },
  HEATWAVE:       { icon: "ti-flame",         color: "#993C1D" },
  GALE:           { icon: "ti-tornado",       color: "#3C3489" },
  NAMED_STORM:    { icon: "ti-alert-triangle",color: "#A32D2D" },
  SOURCE_ANOMALY: { icon: "ti-sparkles",      color: "#0F6E56" },
};

const INTENSITY_COLOR = {
  LIGHT:    { bg: "#EAF3DE", text: "#3B6D11" },
  MODERATE: { bg: "#FAEEDA", text: "#854F0B" },
  SEVERE:   { bg: "#FCEBEB", text: "#A32D2D" },
};

function getWeekStart(offsetWeeks = 0) {
  const d = new Date();
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff + offsetWeeks * 7);
  return d.toISOString().split("T")[0];
}

function getCurrentSeason() {
  const m = new Date().getMonth();
  if (m < 3) return "winter";
  if (m < 6) return "spring";
  if (m < 9) return "summer";
  return "autumn";
}

// ── sub-components ───────────────────────────────────────────────────────────

function Badge({ label, bg, color, style = {} }) {
  return (
    <span style={{
      display: "inline-block", fontSize: 11, fontWeight: 500,
      padding: "2px 8px", borderRadius: 6,
      backgroundColor: bg, color,
      ...style,
    }}>{label}</span>
  );
}

function ConditionBadge({ condition }) {
  const meta = CONDITION_META[condition] ?? { icon: "ti-question-mark", color: "#888" };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 13 }}>
      <i className={`ti ${meta.icon}`} style={{ color: meta.color, fontSize: 14 }} aria-hidden />
      {condition.replace(/_/g, " ")}
    </span>
  );
}


const CLIMATE_PROFILES = {
  lumenhold:     { climate: "Rain shadow desert. Scorching days, freezing nights. Almost no rain. Rare coastal fog from western sea. Sandstorms common in summer.", biome: "desert" },
  flywheel:      { climate: "Mountain river basin with orographic lift. Heavy precipitation year-round. Persistent low cloud. Snow above the dam in winter. Mild valley temps.", biome: "mountain" },
  cinder:        { climate: "High mountain pass. Fierce winds and blizzards in winter. Short warm summers. Snowmelt floods in spring. Volcanic geothermal warmth near the city.", biome: "highland" },
  high_sable:    { climate: "Exposed cliff face, elevated. Constant wind scour. Brutal winters with ice storms. Short summer thaw. Fog rolls up from the valley below.", biome: "cliff" },
  gearford:      { climate: "Central highland continental. Warm summers, cold winters. Spring storms roll through the mountain gap. Industrial steam creates localized fog and smog.", biome: "continental" },
  thornwick:     { climate: "Dense old-growth frontier forest. Perpetually misty and damp from forest moisture cycle. Cool year-round. Heavy autumn rain. Rare sunny days.", biome: "forest" },
  ashgate:       { climate: "Eastern transition zone at trade crossroads. Variable weather from multiple fronts. Warm dry summers. Stormy unpredictable autumn. Mild winters.", biome: "transition" },
  morthand:      { climate: "Cold northern coast. Overcast and grey most of the year. Coastal storms in autumn and spring. Heavy snow. Short bright summers with sea fog.", biome: "northern coast" },
  brassmere:     { climate: "Humid southern coastal port on the Mere. Frequent sea mist. Hot muggy summers. Mild winters. Atlantic-style storms. Industrial smog compounds natural fog.", biome: "coastal industrial" },
  citadel:       { climate: "Southeast coast Mediterranean-like. Warmest and driest city. Hot summers, mild winters. Eastern sea storms in autumn. Occasional drought years.", biome: "mediterranean" },
  ragged_signal: { climate: "Exposed southern tip peninsula. Open ocean on three sides. Storms arrive fast with little warning. Fierce winds. Volatile year-round. Highest storm frequency in winter.", biome: "exposed peninsula" },
  gilded_index:  { climate: "Western peninsula cut off by water on three sides. Maritime climate. Moderate temps year-round. Constant Atlantic wind. Heavy rain in winter, clear breezy summers.", biome: "maritime" },
  black_spur:    { climate: "Northern forest near the coast. Cold and wet. Frequent fog rolling in from the sea. Heavy snow in winter. Cool summers.", biome: "northern forest" },
  iron_covenant: { climate: "Eastern forest, inland. Temperate with cold winters. Moderate rainfall year-round. Less extreme than Thornwick but still heavily forested and damp.", biome: "temperate forest" },
  outlands:      { climate: "Open wilderness between city-states. Exposed to all weather fronts with no shelter. Conditions vary wildly by sub-region.", biome: "wilderness" },
};

async function generateWeatherSuggestion(regionId, season) {
  const profile = CLIMATE_PROFILES[regionId];
  const regionLabel = REGIONS.find(r => r.id === regionId)?.label ?? regionId;
  if (!profile) return null;

  const prompt = `You are the weather loremaster for Doranswyr, a fictional continent in an early industrial-era roleplay server called Railbound.

Generate a weekly weather forecast for ${regionLabel} during ${season}.

Climate profile: ${profile.climate}

Return ONLY a JSON object with exactly these fields:
{
  "condition": one of: CLEAR, OVERCAST, HEAVY_RAIN, THUNDERSTORM, FOG, SANDSTORM, BLIZZARD, ICE_STORM, HEATWAVE, GALE, NAMED_STORM, SOURCE_ANOMALY,
  "intensity": one of: LIGHT, MODERATE, SEVERE,
  "forecast_title": a short evocative title (e.g. "The Widow's Knell" for a named storm, or "Dry Heat" for a heatwave),
  "short_desc": one punchy sentence describing what this means for travelers (max 80 chars),
  "forecast_body": 2-3 sentences of rich RP flavour text describing how this weather feels, sounds, and looks in ${regionLabel}. Write it like a weather report for adventurers. Do not mention game mechanics.
}

Match the condition to what is climatically realistic for this region and season. Named storms and Source anomalies should be rare. No explanation, no markdown, just the JSON object.`;

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 1000,
        messages: [{ role: "user", content: prompt }],
      }),
    });
    const data = await response.json();
    const text = data.content?.find(b => b.type === "text")?.text ?? "";
    const clean = text.replace(/```json|```/g, "").trim();
    return JSON.parse(clean);
  } catch {
    return null;
  }
}


const ZONE_COLORS = {
  "desert":             { color: "#BA7517", bg: "#FAEEDA" },
  "mountain":           { color: "#185FA5", bg: "#E6F1FB" },
  "highland":           { color: "#993C1D", bg: "#FAECE7" },
  "cliff":              { color: "#5F5E5A", bg: "#F1EFE8" },
  "continental":        { color: "#3B6D11", bg: "#EAF3DE" },
  "forest":             { color: "#0F6E56", bg: "#E1F5EE" },
  "transition":         { color: "#534AB7", bg: "#EEEDFE" },
  "northern coast":     { color: "#0C447C", bg: "#E6F1FB" },
  "coastal industrial": { color: "#712B13", bg: "#FAECE7" },
  "mediterranean":      { color: "#854F0B", bg: "#FAEEDA" },
  "exposed peninsula":  { color: "#3C3489", bg: "#EEEDFE" },
  "maritime":           { color: "#085041", bg: "#E1F5EE" },
  "northern forest":    { color: "#27500A", bg: "#EAF3DE" },
  "temperate forest":   { color: "#0F6E56", bg: "#E1F5EE" },
  "wilderness":         { color: "#444441", bg: "#F1EFE8" },
};

function RegionCard({ row, onEdit, suggesting = false, regionId }) {
  const meta = CONDITION_META[row?.condition] ?? CONDITION_META.OVERCAST;
  const intColor = row ? INTENSITY_COLOR[row.intensity] : INTENSITY_COLOR.MODERATE;
  const isEmpty = !row;
  const regionInfo = REGIONS.find(r => r.id === (row?.region ?? regionId));

  return (
    <div style={{
      background: "var(--color-background-primary)",
      border: `0.5px solid ${row?.is_source_anomaly ? "#1D9E75" : row?.condition === "NAMED_STORM" ? "#E24B4A" : "var(--color-border-tertiary)"}`,
      borderRadius: 12, padding: "14px 16px",
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div>
          <div style={{ fontWeight: 500, fontSize: 14, color: "var(--color-text-primary)" }}>
            {regionInfo?.label ?? row?.region ?? regionId}
          </div>
          {regionInfo?.zone && (() => {
            const zc = ZONE_COLORS[regionInfo.zone] ?? { color: "var(--color-text-secondary)", bg: "var(--color-background-secondary)" };
            return (
              <span style={{
                display: "inline-block", fontSize: 10, fontWeight: 500,
                padding: "1px 7px", borderRadius: 10, marginTop: 3,
                background: zc.bg, color: zc.color,
              }}>{regionInfo.zone}</span>
            );
          })()}
        </div>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {row?.is_indefinite && <Badge label="Indefinite" bg="#EEEDFE" color="#3C3489" />}
          {row?.is_source_anomaly && <Badge label="Source anomaly" bg="#E1F5EE" color="#085041" />}
        </div>
      </div>

      {isEmpty ? (
        <div style={{ fontSize: 12, color: "var(--color-text-tertiary)", fontStyle: "italic" }}>
          No forecast set for this week
        </div>
      ) : (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <ConditionBadge condition={row.condition} />
            <Badge
              label={row.intensity}
              bg={intColor.bg}
              color={intColor.text}
            />
          </div>
          {row.forecast_title && (
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)" }}>
              {row.forecast_title}
            </div>
          )}
          {row.short_desc && (
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {row.short_desc}
            </div>
          )}
          {row.override_note && (
            <div style={{
              fontSize: 11, color: "var(--color-text-secondary)",
              background: "var(--color-background-secondary)",
              borderRadius: 6, padding: "4px 8px",
            }}>
              <i className="ti ti-lock" style={{ fontSize: 11, marginRight: 4 }} aria-hidden />
              {row.override_note}
            </div>
          )}
        </>
      )}

      <button
        onClick={() => onEdit(row?.region ?? null, row)}
        style={{ marginTop: 4, alignSelf: "flex-start" }}
      >
        <i className={`ti ${isEmpty ? "ti-plus" : "ti-edit"}`} style={{ fontSize: 13, marginRight: 4 }} aria-hidden />
        {isEmpty ? "Set forecast" : "Edit"}
      </button>
    </div>
  );
}

function EditModal({ regionId, existing, suggestion, weekStart, staffName, onSave, onClose }) {
  const region = REGIONS.find(r => r.id === regionId);
  const seed = existing ?? suggestion ?? {};
  const [form, setForm] = useState({
    condition:         seed.condition       ?? "OVERCAST",
    intensity:         seed.intensity       ?? "MODERATE",
    forecast_title:    seed.forecast_title  ?? "",
    forecast_body:     seed.forecast_body   ?? "",
    short_desc:        seed.short_desc      ?? "",
    effects:           seed.effects ? JSON.stringify(seed.effects, null, 2) : "{}",
    is_indefinite:     seed.is_indefinite   ?? false,
    is_source_anomaly: seed.is_source_anomaly ?? false,
    override_note:     seed.override_note   ?? "",
  });
  const hasSuggestion = !existing && !!suggestion;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function set(key, val) { setForm(f => ({ ...f, [key]: val })); }

  async function handleSave() {
    setSaving(true);
    setError(null);
    let parsedEffects;
    try { parsedEffects = JSON.parse(form.effects); }
    catch { setError("Effects JSON is invalid."); setSaving(false); return; }

    const payload = {
      region:            regionId,
      condition:         form.condition,
      intensity:         form.intensity,
      forecast_title:    form.forecast_title,
      forecast_body:     form.forecast_body,
      short_desc:        form.short_desc,
      effects:           parsedEffects,
      is_indefinite:     form.is_indefinite,
      is_source_anomaly: form.is_source_anomaly,
      override_note:     form.override_note,
      week_start:        weekStart,
      set_by:            staffName,
      is_active:         true,
    };

    try {
      if (existing?.id) {
        await apiFetch(`/api/weather/conditions/${existing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        await apiFetch("/api/weather/conditions", { method: "POST", body: JSON.stringify(payload) });
      }
      onSave();
    } catch (e) { setError(e.message); setSaving(false); return; }
  }

  const meta = CONDITION_META[form.condition] ?? { icon: "ti-cloud", color: "#888" };
  const intColor = INTENSITY_COLOR[form.intensity] ?? INTENSITY_COLOR.MODERATE;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      display: "flex", alignItems: "stretch", justifyContent: "flex-end",
    }}>
      <div onClick={onClose} style={{ flex: 1, background: "rgba(0,0,0,0.25)" }} />
      <div style={{
        width: "min(520px, 100vw)",
        background: "var(--color-background-primary)",
        borderLeft: "0.5px solid var(--color-border-secondary)",
        display: "flex", flexDirection: "column",
        overflowY: "auto",
      }}>
        <div style={{
          padding: "20px 24px 16px",
          borderBottom: "0.5px solid var(--color-border-tertiary)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          position: "sticky", top: 0,
          background: "var(--color-background-primary)", zIndex: 1,
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <i className={`ti ${meta.icon}`} style={{ color: meta.color, fontSize: 18 }} aria-hidden />
              <span style={{ fontWeight: 500, fontSize: 16 }}>{region?.label ?? regionId}</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 2 }}>
              Week of {weekStart} · {region?.zone}
            </div>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ padding: "6px 8px" }}>
            <i className="ti ti-x" style={{ fontSize: 16 }} aria-hidden />
          </button>
        </div>

        {hasSuggestion && (
          <div style={{
            margin: "0 24px",
            marginTop: 12,
            padding: "10px 14px",
            background: "var(--color-background-info)",
            borderRadius: 8,
            display: "flex", alignItems: "center", gap: 8,
            fontSize: 12, color: "var(--color-text-info)",
          }}>
            <i className="ti ti-sparkles" style={{ fontSize: 14 }} aria-hidden />
            <span>Auto-suggested based on {region?.zone} climate + {season} season. Edit freely.</span>
          </div>
        )}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20, flex: 1 }}>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>Condition</span>
              <select value={form.condition} onChange={e => set("condition", e.target.value)}>
                {CONDITIONS.map(c => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>Intensity</span>
              <select value={form.intensity} onChange={e => set("intensity", e.target.value)}>
                {INTENSITIES.map(i => <option key={i} value={i}>{i}</option>)}
              </select>
            </label>
          </div>

          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            padding: "6px 12px", borderRadius: 8, alignSelf: "flex-start",
            background: intColor.bg, fontSize: 12, fontWeight: 500, color: intColor.text,
          }}>
            <i className={`ti ${meta.icon}`} style={{ fontSize: 14 }} aria-hidden />
            {form.condition.replace(/_/g, " ")} · {form.intensity}
          </div>

          <div style={{ height: "0.5px", background: "var(--color-border-tertiary)" }} />

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>
              Forecast title
              <span style={{ fontWeight: 400, marginLeft: 6, color: "var(--color-text-tertiary)" }}>shown in Discord embed</span>
            </span>
            <input
              type="text"
              value={form.forecast_title}
              onChange={e => set("forecast_title", e.target.value)}
              placeholder="e.g. Named Storm: The Widow's Knell"
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>
              Short description
              <span style={{ fontWeight: 400, marginLeft: 6, color: "var(--color-text-tertiary)" }}>one line, embed footer</span>
            </span>
            <input
              type="text"
              value={form.short_desc}
              onChange={e => set("short_desc", e.target.value)}
              placeholder="e.g. Seas are impassable. Rail only."
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>Forecast body</span>
            <textarea
              value={form.forecast_body}
              onChange={e => set("forecast_body", e.target.value)}
              rows={5}
              placeholder="Describe the weather in flavour text..."
              style={{ resize: "vertical" }}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>
              Mechanical effects
              <span style={{ fontWeight: 400, marginLeft: 6, color: "var(--color-text-tertiary)" }}>JSON</span>
            </span>
            <textarea
              value={form.effects}
              onChange={e => set("effects", e.target.value)}
              rows={3}
              style={{ fontFamily: "var(--font-mono)", fontSize: 12, resize: "vertical" }}
              placeholder='{"ranged_accuracy": -10, "stamina_outdoor": -5}'
            />
          </label>

          <div style={{ height: "0.5px", background: "var(--color-border-tertiary)" }} />

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, cursor: "pointer" }}>
              <input type="checkbox" checked={form.is_indefinite} onChange={e => set("is_indefinite", e.target.checked)} />
              <div>
                <div style={{ fontWeight: 500 }}>Indefinite</div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Arc event — won't auto-clear at week end</div>
              </div>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, cursor: "pointer" }}>
              <input type="checkbox" checked={form.is_source_anomaly} onChange={e => set("is_source_anomaly", e.target.checked)} />
              <div>
                <div style={{ fontWeight: 500 }}>Source anomaly</div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Shows with distinct styling on player-facing map</div>
              </div>
            </label>
          </div>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>
              Staff note
              <span style={{ fontWeight: 400, marginLeft: 6, color: "var(--color-text-tertiary)" }}>internal only</span>
            </span>
            <input
              type="text"
              value={form.override_note}
              onChange={e => set("override_note", e.target.value)}
              placeholder="e.g. Tied to arc event in ch.4"
            />
          </label>

          {error && (
            <div style={{ fontSize: 13, color: "var(--color-text-danger)", background: "var(--color-background-danger)", borderRadius: 8, padding: "10px 14px" }}>
              {error}
            </div>
          )}
        </div>

        <div style={{
          padding: "16px 24px",
          borderTop: "0.5px solid var(--color-border-tertiary)",
          display: "flex", gap: 8, justifyContent: "flex-end",
          position: "sticky", bottom: 0,
          background: "var(--color-background-primary)",
        }}>
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSave} disabled={saving} style={{ fontWeight: 500 }}>
            {saving ? "Saving..." : "Save forecast"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── main dashboard ────────────────────────────────────────────────────────────

export default function WeatherDashboard({ staffName = "Staff" }) {
  const [weekStart, setWeekStart] = useState(getWeekStart(1)); // next week by default
  const [season, setSeason] = useState(getCurrentSeason());
  const [conditions, setConditions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rolling, setRolling] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [posting, setPosting] = useState(false);
  const [editTarget, setEditTarget] = useState(null); // { regionId, existing, suggestion }
  const [suggesting, setSuggesting] = useState(false);
  const [toast, setToast] = useState(null);

  function showToast(msg, type = "success") {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  }

  const fetchConditions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch(`/api/weather/conditions?week_start=${weekStart}`);
      setConditions(data.conditions ?? []);
    } catch { setConditions([]); }
    setLoading(false);
  }, [weekStart]);

  useEffect(() => { fetchConditions(); }, [fetchConditions]);

  async function handleRoll() {
    setRolling(true);
    try {
      await apiFetch(`/api/weather/roll?season=${season}&week_start=${weekStart}`, { method: "POST" });
      showToast("Rolled forecast for all regions — review and edit before posting.");
    } catch (e) { showToast(e.message, "error"); }
    await fetchConditions();
    setRolling(false);
  }

  async function handleArchive() {
    if (!confirm("Archive this week's forecasts and clear non-indefinite conditions?")) return;
    setArchiving(true);
    try {
      await apiFetch("/api/weather/archive", { method: "POST" });
      showToast("Week archived. Roll new forecasts when ready.");
    } catch (e) { showToast(e.message, "error"); }
    await fetchConditions();
    setArchiving(false);
  }

  async function handlePostToDiscord() {
    setPosting(true);
    try {
      const res = await fetch("/api/weather/post-discord", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weekStart, staffName }),
      });
      if (!res.ok) throw new Error(await res.text());
      showToast("Posted to #weather-forecast on Discord!");
    } catch (e) {
      showToast(e.message, "error");
    }
    setPosting(false);
  }

  function getRowForRegion(regionId) {
    return conditions.find(c => c.region === regionId) ?? null;
  }

  const setCount = conditions.length;
  const totalRegions = REGIONS.length;
  const hasNamed = conditions.some(c => c.condition === "NAMED_STORM");
  const hasAnomaly = conditions.some(c => c.is_source_anomaly);

  return (
    <div style={{ padding: "24px 0", position: "relative" }}>

      {/* Toast */}
      {toast && (
        <div style={{
          position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)",
          background: toast.type === "error" ? "var(--color-background-danger)" : "var(--color-background-success)",
          color: toast.type === "error" ? "var(--color-text-danger)" : "var(--color-text-success)",
          border: `0.5px solid ${toast.type === "error" ? "var(--color-border-danger)" : "var(--color-border-success)"}`,
          borderRadius: 8, padding: "8px 16px", fontSize: 13, zIndex: 200,
          whiteSpace: "nowrap",
        }}>{toast.msg}</div>
      )}

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 500 }}>
          <i className="ti ti-cloud-storm" style={{ marginRight: 8, fontSize: 18 }} aria-hidden />
          Weather dashboard
        </h2>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-secondary)" }}>
          Set and broadcast weekly forecasts for all regions of Doranswyr.
        </p>
      </div>

      {/* Controls bar */}
      <div style={{
        display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center",
        marginBottom: 20, padding: "14px 16px",
        background: "var(--color-background-secondary)",
        borderRadius: 12,
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <label style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Week of</label>
          <input
            type="date"
            value={weekStart}
            onChange={e => setWeekStart(e.target.value)}
            style={{ width: 150 }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <label style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Season</label>
          <select value={season} onChange={e => setSeason(e.target.value)} style={{ width: 120 }}>
            {SEASONS.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
          </select>
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={handleRoll} disabled={rolling}>
            <i className="ti ti-dice-5" style={{ fontSize: 14, marginRight: 6 }} aria-hidden />
            {rolling ? "Rolling..." : "Roll all regions"}
          </button>
          <button onClick={handleArchive} disabled={archiving}>
            <i className="ti ti-archive" style={{ fontSize: 14, marginRight: 6 }} aria-hidden />
            {archiving ? "Archiving..." : "Archive week"}
          </button>
          <button
            onClick={handlePostToDiscord}
            disabled={posting || setCount === 0}
            style={{ fontWeight: 500 }}
          >
            <i className="ti ti-brand-discord" style={{ fontSize: 14, marginRight: 6 }} aria-hidden />
            {posting ? "Posting..." : "Post to Discord"}
          </button>
        </div>
      </div>

      {/* Status row */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ background: "var(--color-background-secondary)", borderRadius: 8, padding: "10px 16px", minWidth: 110 }}>
          <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 2 }}>Regions set</div>
          <div style={{ fontSize: 22, fontWeight: 500 }}>{setCount} / {totalRegions}</div>
        </div>
        {hasNamed && (
          <div style={{ background: "#FCEBEB", borderRadius: 8, padding: "10px 16px" }}>
            <div style={{ fontSize: 11, color: "#A32D2D", marginBottom: 2 }}>Named storm active</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#791F1F" }}>
              {conditions.filter(c => c.condition === "NAMED_STORM").map(c =>
                REGIONS.find(r => r.id === c.region)?.label
              ).join(", ")}
            </div>
          </div>
        )}
        {hasAnomaly && (
          <div style={{ background: "#E1F5EE", borderRadius: 8, padding: "10px 16px" }}>
            <div style={{ fontSize: 11, color: "#0F6E56", marginBottom: 2 }}>Source anomaly active</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#085041" }}>
              {conditions.filter(c => c.is_source_anomaly).map(c =>
                REGIONS.find(r => r.id === c.region)?.label
              ).join(", ")}
            </div>
          </div>
        )}
      </div>

      {/* Region grid */}
      {loading ? (
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)", padding: "40px 0", textAlign: "center" }}>
          Loading forecasts...
        </div>
      ) : (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
        }}>
          {REGIONS.map(r => (
            <RegionCard
              key={r.id}
              row={getRowForRegion(r.id)}
              regionId={r.id}
              suggesting={suggesting === r.id}
              onEdit={async (regionId, existing) => {
                const rid = regionId ?? r.id;
                if (!existing) {
                  setSuggesting(rid);
                  const suggestion = await generateWeatherSuggestion(rid, season);
                  setSuggesting(false);
                  setEditTarget({ regionId: rid, existing: null, suggestion });
                } else {
                  setEditTarget({ regionId: rid, existing, suggestion: null });
                }
              }}
            />
          ))}
        </div>
      )}

      {/* Edit modal */}
      {editTarget && (
        <EditModal
          regionId={editTarget.regionId}
          existing={editTarget.existing}
          suggestion={editTarget.suggestion}
          weekStart={weekStart}
          staffName={staffName}
          onSave={async () => {
            setEditTarget(null);
            await fetchConditions();
            showToast("Forecast saved.");
          }}
          onClose={() => setEditTarget(null)}
        />
      )}
    </div>
  );
}
