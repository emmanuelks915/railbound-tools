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

function RegionCard({ row, onEdit }) {
  const meta = CONDITION_META[row?.condition] ?? CONDITION_META.OVERCAST;
  const intColor = row ? INTENSITY_COLOR[row.intensity] : INTENSITY_COLOR.MODERATE;
  const isEmpty = !row;

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
            {REGIONS.find(r => r.id === row?.region)?.label ?? row?.region}
          </div>
          <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 1 }}>
            {REGIONS.find(r => r.id === row?.region)?.zone ?? ""}
          </div>
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

function EditModal({ regionId, existing, weekStart, staffName, onSave, onClose }) {
  const region = REGIONS.find(r => r.id === regionId);
  const [form, setForm] = useState({
    condition:       existing?.condition ?? "OVERCAST",
    intensity:       existing?.intensity ?? "MODERATE",
    forecast_title:  existing?.forecast_title ?? "",
    forecast_body:   existing?.forecast_body ?? "",
    short_desc:      existing?.short_desc ?? "",
    effects:         existing?.effects ? JSON.stringify(existing.effects, null, 2) : "{}",
    is_indefinite:   existing?.is_indefinite ?? false,
    is_source_anomaly: existing?.is_source_anomaly ?? false,
    override_note:   existing?.override_note ?? "",
  });
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

  const labelStyle = { fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4, display: "block" };
  const rowStyle = { display: "flex", flexDirection: "column", gap: 4 };

  return (
    <div style={{
      position: "absolute", inset: 0, background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 100, padding: 24,
    }}>
      <div style={{
        background: "var(--color-background-primary)",
        border: "0.5px solid var(--color-border-secondary)",
        borderRadius: 16, padding: 24, width: "100%", maxWidth: 560,
        display: "flex", flexDirection: "column", gap: 16,
        maxHeight: "90vh", overflowY: "auto",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontWeight: 500, fontSize: 16 }}>{region?.label ?? regionId}</div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Week of {weekStart}</div>
          </div>
          <button onClick={onClose} aria-label="Close">
            <i className="ti ti-x" style={{ fontSize: 16 }} aria-hidden />
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={rowStyle}>
            <label style={labelStyle}>Condition</label>
            <select value={form.condition} onChange={e => set("condition", e.target.value)}>
              {CONDITIONS.map(c => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div style={rowStyle}>
            <label style={labelStyle}>Intensity</label>
            <select value={form.intensity} onChange={e => set("intensity", e.target.value)}>
              {INTENSITIES.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
        </div>

        <div style={rowStyle}>
          <label style={labelStyle}>Forecast title <span style={{ color: "var(--color-text-tertiary)" }}>(shown in Discord embed)</span></label>
          <input
            type="text"
            value={form.forecast_title}
            onChange={e => set("forecast_title", e.target.value)}
            placeholder="e.g. Named Storm: The Widow's Knell"
          />
        </div>

        <div style={rowStyle}>
          <label style={labelStyle}>Short description <span style={{ color: "var(--color-text-tertiary)" }}>(one line, embed footer)</span></label>
          <input
            type="text"
            value={form.short_desc}
            onChange={e => set("short_desc", e.target.value)}
            placeholder="e.g. Seas are impassable. Rail only."
          />
        </div>

        <div style={rowStyle}>
          <label style={labelStyle}>Forecast body <span style={{ color: "var(--color-text-tertiary)" }}>(full RP description)</span></label>
          <textarea
            value={form.forecast_body}
            onChange={e => set("forecast_body", e.target.value)}
            rows={4}
            placeholder="Describe the weather in flavour text..."
            style={{ resize: "vertical" }}
          />
        </div>

        <div style={rowStyle}>
          <label style={labelStyle}>
            Mechanical effects <span style={{ color: "var(--color-text-tertiary)" }}>(JSON)</span>
          </label>
          <textarea
            value={form.effects}
            onChange={e => set("effects", e.target.value)}
            rows={3}
            style={{ fontFamily: "var(--font-mono)", fontSize: 12, resize: "vertical" }}
            placeholder='{"ranged_accuracy": -10, "stamina_outdoor": -5}'
          />
        </div>

        <div style={{ display: "flex", gap: 20 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={form.is_indefinite} onChange={e => set("is_indefinite", e.target.checked)} />
            Indefinite (arc event — won't auto-clear)
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={form.is_source_anomaly} onChange={e => set("is_source_anomaly", e.target.checked)} />
            Source anomaly
          </label>
        </div>

        <div style={rowStyle}>
          <label style={labelStyle}>Staff note <span style={{ color: "var(--color-text-tertiary)" }}>(internal only, not shown to players)</span></label>
          <input
            type="text"
            value={form.override_note}
            onChange={e => set("override_note", e.target.value)}
            placeholder="e.g. Tied to arc event in ch.4"
          />
        </div>

        {error && (
          <div style={{ fontSize: 13, color: "var(--color-text-danger)", background: "var(--color-background-danger)", borderRadius: 8, padding: "8px 12px" }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
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
  const [editTarget, setEditTarget] = useState(null); // { regionId, existing }
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
              onEdit={(regionId, existing) => setEditTarget({ regionId: regionId ?? r.id, existing })}
            />
          ))}
        </div>
      )}

      {/* Edit modal */}
      {editTarget && (
        <EditModal
          regionId={editTarget.regionId}
          existing={editTarget.existing}
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
