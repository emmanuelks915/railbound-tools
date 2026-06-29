import React, { useEffect, useMemo, useRef, useState } from "react";
import WeatherDashboard from "./components/WeatherDashboard";
import GettingStartedDashboard from "./components/GettingStartedDashboard";
import LandingPage from "./components/LandingPage";
import "./landing.css";
import { createRoot } from "react-dom/client";
import { BookOpen, Calculator, Check, ClipboardList, CloudLightning, Edit, Eye, EyeOff, Home, Package, Plus, RefreshCw, Save, Search, Send, ShieldCheck, ShoppingCart, Sparkles, Store, Trash2, UserRound, X, Users } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const ALLOW_DEV_LOGIN = import.meta.env.VITE_ALLOW_DEV_LOGIN === "true";

type Character = {
  character_id: string;
  name: string;
  user_id?: string;
  active_loadout_name?: string | null;
};

type CoreStats = {
  strength: number;
  dexterity: number;
  stamina: number;
  magic_affinity: number;
  mana: number;
};

type Tab = "home" | "getting_started" | "activity" | "planner" | "oc" | "inventory" | "shops" | "skills" | "rp" | "missions" | "companion" | "staff" | "beast_skills" | "combat" | "registry" | "register" | "manage_oc" | "qa" | "shop_owner" | "loadouts" | "weather";

const STAT_LABELS: Record<keyof CoreStats, string> = {
  strength: "Strength",
  dexterity: "Dexterity",
  stamina: "Stamina",
  magic_affinity: "Magic Affinity",
  mana: "Mana",
};

const blankStats: CoreStats = {
  strength: 0,
  dexterity: 0,
  stamina: 0,
  magic_affinity: 0,
  mana: 0,
};

async function apiFetch(path: string, options: RequestInit = {}, discordId?: string) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  const authToken = localStorage.getItem("railbound_auth_token");
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);

  if (ALLOW_DEV_LOGIN && discordId) headers.set("X-Discord-Id", discordId);

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }

  return data;
}

function App() {
  const [tab, setTab] = useState<Tab>("home");
  const [authUser, setAuthUser] = useState<any>(null);
  const [discordId, setDiscordId] = useState(() => localStorage.getItem("railbound_discord_id") || "");
  const [selectedCharacterId, setSelectedCharacterId] = useState(() => localStorage.getItem("railbound_character_id") || "");
  const [hasLoyalCompanion, setHasLoyalCompanion] = useState(false);
  useEffect(() => {
    // Root Cause OC Ghost Fix v1: clear stored selected OC when Discord account changes.
    const previousDiscordId = localStorage.getItem("railbound_last_discord_id") || "";

    if (previousDiscordId && previousDiscordId !== discordId) {
      localStorage.removeItem("railbound_character_id");
      setSelectedCharacterId("");
    }

    if (discordId) {
      localStorage.setItem("railbound_last_discord_id", discordId);
    }

    localStorage.setItem("railbound_discord_id", discordId);
  }, [discordId]);

  useEffect(() => {
    localStorage.setItem("railbound_character_id", selectedCharacterId);
    loadSelectedCompanionEligibility(selectedCharacterId).catch(() => {});
  }, [selectedCharacterId, discordId]);

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

  async function loadSelectedCompanionEligibility(characterId = selectedCharacterId) {
    if (!discordId || !characterId) {
      setHasLoyalCompanion(false);
      return;
    }

    try {
      const data = await apiFetch(`/api/companions/${characterId}`, {}, discordId);
      setHasLoyalCompanion(Boolean(data?.eligible));
    } catch {
      setHasLoyalCompanion(false);
    }
  }

  async function loadAccountCompanionEligibility() {
    if (!discordId) {
      setHasLoyalCompanion(false);
      return;
    }

    try {
      const data = await apiFetch("/api/companions/eligibility", {}, discordId);
      setHasLoyalCompanion(Boolean(data?.eligible));
    } catch {
      setHasLoyalCompanion(false);
    }
  }

  function loginWithDiscord() {
    window.location.href = `${API_BASE}/api/auth/discord/login`;
  }

  function logoutDiscord() {
    localStorage.removeItem("railbound_auth_token");
    localStorage.removeItem("railbound_discord_id");
    setAuthUser(null);
    setDiscordId("");
  }

  const tabs = [
    ["home", Home, "Dashboard"],

    ["getting_started", BookOpen, "Getting Started"],
    ["oc", UserRound, "OC"],
    ["register", UserRound, "Register OC"],
    ["registry", Users, "OC Registry"],
    ["manage_oc", UserRound, "Manage OC"],

    ["planner", Calculator, "XP Planner"],
    ["skills", Sparkles, "Skills"],
    ["inventory", Package, "Inventory"],
    ["loadouts", Package, "Loadouts"],
    ["rp", ClipboardList, "RP Hub"],
    ["missions", ClipboardList, "Missions"],
    ["companion", Sparkles, "Companion"],
    ["shops", Store, "Shops"],
    ["activity", ClipboardList, "Activity"],
    ["staff", ShieldCheck, "Staff"],
    ["beast_skills", Sparkles, "Beast Skills"],
    ["weather", CloudLightning, "Weather"],
    ["combat", ClipboardList, "Derived Stats"],
  ] as const;

    const permissions = usePermissions(discordId);
  // Staff OC Autoselect Safety: clear stale OC selection
  useEffect(() => {
    if (permissions?.is_staff) {
      setHasLoyalCompanion(true);
    }

    if (permissions?.is_staff && selectedCharacterId) {
      setSelectedCharacterId("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [permissions?.is_staff]);

  if (tab && !canUseTab(permissions, tab)) {
    setTab("dashboard");
  }

  const isLoggedInForDashboard = Boolean(discordId);

  // Show landing page for unauthenticated users
  if (!authUser && !discordId) {
    return <LandingPage onLogin={loginWithDiscord} />;
  }

return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Railbound Systems</p>
          <h1>Railbound Tools</h1>
          <p className="subtitle">
            OC dashboard, XP planning, inventory, loadouts, player shops, skills, staff approvals, and combat math.
          </p>
        </div>
        <div className="auth-box">
                    <div className="auth-user login-button-only-card">
            {authUser?.avatar_url ? (
              <img
                src={authUser.avatar_url}
                alt="Discord avatar"
                className="auth-avatar"
              />
            ) : null}

            <strong>
              {authUser
                ? authUser.global_name || authUser.username || authUser.discord_id || discordId
                : ""}
            </strong>

            {authUser?.username ? (
              <small>@{authUser.username}</small>
            ) : discordId ? (
              <small>Discord ID: {discordId}</small>
            ) : null}
          </div>

          <div className="auth-actions">
            {!authUser ? (
              <button type="button" onClick={loginWithDiscord} className="discord-login-button">
                Login with Discord
              </button>
            ) : (
              <button type="button" className="ghost" onClick={logoutDiscord}>
                Logout
              </button>
            )}
          </div>

          {ALLOW_DEV_LOGIN ? (
<label className="auth-dev-login">
            <span>Dev fallback</span>
            <input
              value={discordId}
              onChange={(event) => setDiscordId(event.target.value)}
              placeholder="Paste Discord ID for local testing"
            />
          </label>
          ) : null}
        </div>
      </section>

      <nav className="tabs">
        {tabs.filter(([key]) => canUseTab(permissions, key as Tab) && (key !== "companion" || permissions?.is_staff || hasLoyalCompanion))
            .map(([key, Icon, label]) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            <Icon size={18} /> {label}
          </button>
        ))}
      </nav>

      {tab === "home" && (
        <HomeDashboard
          discordId={discordId}
          selectedCharacterId={selectedCharacterId}
          setSelectedCharacterId={setSelectedCharacterId}
          jump={setTab}
        />
      )}
      {tab === "activity" && <StaffOnly discordId={discordId}><ActivityDashboard discordId={discordId} /></StaffOnly>}
      {tab === "planner" && <Planner discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "oc" && <OCDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} jump={setTab} />}
      {tab === "manage_oc" && <ManageOCDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "getting_started" && <GettingStartedDashboard discordId={discordId} jump={setTab} />}
      {tab === "inventory" && <InventoryDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "loadouts" && <LoadoutsDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "weather" && <WeatherDashboard staffName={authUser?.global_name || authUser?.username || discordId} />}
      {(tab === "shops" || tab === "shop_owner") && (
        <ShopHubDashboard
          discordId={discordId}
          selectedCharacterId={selectedCharacterId}
          initialView={tab === "shop_owner" ? "manage" : "browse"}
        />
      )}
      {tab === "skills" && <SkillsDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "rp" && <RpHubDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "missions" && <MissionBoardDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "companion" && <CompanionDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "register" && <OCRegistrationDashboard discordId={discordId} jump={setTab} />}
      {tab === "registry" && <OCRegistry discordId={discordId} />}
      {tab === "staff" && <StaffOnly discordId={discordId}><section className="request-workflow-page"><StaffQueue discordId={discordId} /></section></StaffOnly>}
      {tab === "beast_skills" && <BeastSkillCatalogDashboard discordId={discordId} />}
      {tab === "combat" && <DerivedStatsCalculator />}
    </main>
  );
}

function usePermissions(discordId: string) {
  const [permissions, setPermissions] = useState<any>({
    is_logged_in: false,
    is_staff: false,
    is_admin: false,
    allowed_tabs: [],
  });

  useEffect(() => {
    if (!discordId) return;

    apiFetch("/api/auth/permissions", {}, discordId)
      .then((data) => setPermissions(rememberPermissionsForSelectionSafety(data)))
      .catch(() =>
        setPermissions(
          rememberPermissionsForSelectionSafety({
            is_logged_in: Boolean(discordId),
            is_staff: false,
            is_admin: false,
            allowed_tabs: [],
          })
        )
      );
  }, [discordId]);

  return permissions;
}

function rememberPermissionsForSelectionSafety(data: any) {
  if (typeof window !== "undefined") {
    (window as any).__railboundPermissions = data;
  }
  return data;
}

function shouldAutoSelectOc() {
  if (typeof window === "undefined") return false;
  const permissions = (window as any).__railboundPermissions;

  if (!permissions || permissions.is_staff === undefined) return false;

  return permissions.is_staff !== true;
}

function canUseTab(permissions: any, tab: Tab) {
  const allowedTabs = permissions?.allowed_tabs || [];

  if (!allowedTabs.length) {
    // Not yet loaded — hide staff/restricted tabs, show everything else except shop_owner nav
    return !["staff", "qa", "activity", "shop_owner", "weather", "combat"].includes(String(tab));
  }

  return allowedTabs.includes(tab);
}

function StaffOnly({
  discordId,
  children,
}: {
  discordId: string;
  children: React.ReactNode;
}) {
  const permissions = usePermissions(discordId);

  if (!permissions?.is_staff) {
    return (
      <RequireDiscord discordId={discordId}>
        <div className="card permission-denied-card">
          <span className="activity-type-label">Restricted</span>
          <h2>Staff Only</h2>
          <p className="muted-text">
            This page is restricted to staff. If you should have access, check your STAFF_DISCORD_IDS backend variable.
          </p>
        </div>
      </RequireDiscord>
    );
  }

  return <>{children}</>;
}

function RequireDiscord({ discordId, children }: { discordId: string; children: React.ReactNode }) {
  if (!discordId) {
    return null;
  }
  return <>{children}</>;
}

function CharacterSelect({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
  label = "OC",
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
  label?: string;
}) {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [message, setMessage] = useState("");

  async function loadCharacters() {
    setMessage("");
    const data = await apiFetch("/api/characters/mine", {}, discordId);
    const rows = Array.isArray(data) ? data : data.characters || data.data || [];

    setCharacters(rows);

    const selectedIsValid = rows.some((character: any) =>
      String(character.character_id || character.id || "") === String(selectedCharacterId || "")
    );

    if (selectedCharacterId && !selectedIsValid) {
      setSelectedCharacterId("");
      return;
    }

    if (!selectedCharacterId && rows[0]?.character_id && shouldAutoSelectOc()) {
      setSelectedCharacterId(rows[0].character_id);
    }
  }

  useEffect(() => {
    if (discordId) loadCharacters().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  return (
    <label>
      {label}
      <select value={selectedCharacterId} onChange={(event) => setSelectedCharacterId(event.target.value)}>
        <option value="">Select an OC</option>
        {characters.map((character) => (
          <option key={character.character_id} value={character.character_id}>
            {character.name}
          </option>
        ))}
      </select>
      {message && <small className="bad">{message}</small>}
    </label>
  );
}

function HomeDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
  jump,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
  jump: (tab: Tab) => void;
}) {
  const [data, setData] = useState<any>(null);
  const [message, setMessage] = useState("");

  async function load() {
    setMessage("");
    const d = await apiFetch("/api/dashboard/me", {}, discordId);
    const rows = d.characters || [];

    const selectedIsValid = rows.some((character: any) =>
      String(character.character_id || character.id || "") === String(selectedCharacterId || "")
    );

    if (selectedCharacterId && !selectedIsValid) {
      setSelectedCharacterId("");
    }

    if (!selectedCharacterId && rows?.[0]?.character_id && shouldAutoSelectOc()) {
      setSelectedCharacterId(rows[0].character_id);
    }

    setData(d);
  }

  useEffect(() => {
    if (discordId) load().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid dashboard-grid">
        <div className="card">
          <div className="card-title-row">
            <h2>My Railbound</h2>
            <button className="ghost" onClick={load}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
          {message && <p className="message">{message}</p>}
          {!data ? (
            <p>Load your dashboard to see your OCs, shops, and pending requests.</p>
          ) : (
            <>
              <div className="summary">
                <div>
                  <span>OCs</span>
                  <strong>{data.characters?.length || 0}</strong>
                </div>
                <div>
                  <span>Shops</span>
                  <strong>{data.shops?.length || 0}</strong>
                </div>
                <div>
                  <span>Staff</span>
                  <strong className={data.is_staff ? "good" : ""}>{data.is_staff ? "Yes" : "No"}</strong>
                </div>
              </div>

              <h3>Characters</h3>
              <div className="item-list compact-list">
                {(data.characters || []).map((character: Character) => (
                  <button
                    className={`list-button ${selectedCharacterId === character.character_id ? "selected" : ""}`}
                    key={character.character_id}
                    onClick={() => {
                      setSelectedCharacterId(character.character_id);
                      jump("oc");
                    }}
                  >
                    <UserRound size={16} /> {character.name}
                    {character.active_loadout_name ? <small>Active loadout: {character.active_loadout_name}</small> : null}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="card">
          <h2>Quick Actions</h2>
          <div className="quick-grid">
            <button onClick={() => jump("planner")}><Calculator size={16} /> Plan Stats</button>
            <button onClick={() => jump("inventory")}><Package size={16} /> Manage Inventory</button>
            <button onClick={() => jump("skills")}><Sparkles size={16} /> Manage Skills</button>
            <button onClick={() => jump("register")}><UserRound size={16} /> Register OC</button>
            <button onClick={() => jump("shops")}><Store size={16} /> Shops & Market</button>
            <button onClick={() => jump("staff")}><ShieldCheck size={16} /> Staff Queue</button>
            <button onClick={() => jump("qa")}><ClipboardList size={16} /> QA Checklist</button>
          </div>

          {data && (
            <div className="split-panels">
              <div>
                <h3>Pending Stat Requests</h3>
                {(data.pending_stat_requests || []).length === 0 ? <p>None pending.</p> : null}
                {(data.pending_stat_requests || []).slice(0, 5).map((r: any) => (
                  <p className="pill" key={r.request_id}>{r.total_cost} XP • {r.status}</p>
                ))}
              </div>
              <div>
                <h3>Pending Skill Requests</h3>
                {(data.pending_skill_requests || []).length === 0 ? <p>None pending.</p> : null}
                {(data.pending_skill_requests || []).slice(0, 5).map((r: any) => (
                  <p className="pill" key={r.request_id}>{r.skill_key} • {r.cost} XP</p>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </RequireDiscord>
  );
}

function Planner({ discordId, selectedCharacterId, setSelectedCharacterId }: { discordId: string; selectedCharacterId: string; setSelectedCharacterId: (id: string) => void }) {
  const [currentStats, setCurrentStats] = useState<CoreStats>(blankStats);
  const [targetStats, setTargetStats] = useState<CoreStats>(blankStats);
  const [wallet, setWallet] = useState<any>(null);
  const [preview, setPreview] = useState<any>(null);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");

  async function loadSummary(id: string) {
    setPreview(null);
    if (!id) return;
    const data = await apiFetch(`/api/characters/${id}/summary`, {}, discordId);
    setCurrentStats(data.stats);
    setTargetStats(data.stats);
    setWallet(data.wallet);
  }

  useEffect(() => {
    if (selectedCharacterId) loadSummary(selectedCharacterId).catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCharacterId, discordId]);

  async function runPreview() {
    setMessage("");
    setPreview(null);

    if (!selectedCharacterId) {
      setMessage("Pick an OC first.");
      return;
    }

    const data = await apiFetch("/api/xp/preview", {
      method: "POST",
      body: JSON.stringify({
        character_id: selectedCharacterId,
        target_stats: targetStats,
      }),
    });

    setPreview(data);
  }

  async function submitRequest() {
    setMessage("");

    if (!discordId) {
      setMessage("Add your Discord ID first.");
      return;
    }

    const data = await apiFetch(
      "/api/stat-requests",
      {
        method: "POST",
        body: JSON.stringify({
          character_id: selectedCharacterId,
          requested_by_discord_id: Number(discordId),
          target_stats: targetStats,
          submitter_note: note,
        }),
      },
      discordId
    );

    setMessage(`Submitted request ${data.request?.request_id || ""}.`);
    setPreview(null);
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid">
        <div className="card">
          <h2>XP Stat Planner</h2>
          <CharacterSelect discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />

          {wallet && (
            <div className="stat-strip">
              <span>Available XP</span>
              <strong>{wallet.available_xp}</strong>
            </div>
          )}

          <div className="stats-grid">
            {(Object.keys(STAT_LABELS) as Array<keyof CoreStats>).map((key) => (
              <label key={key}>
                {STAT_LABELS[key]}
                <small>Current: {currentStats[key] ?? 0}</small>
                <input
                  type="number"
                  min={0}
                  value={targetStats[key] ?? 0}
                  onChange={(event) =>
                    setTargetStats((prev) => ({
                      ...prev,
                      [key]: Number(event.target.value),
                    }))
                  }
                />
              </label>
            ))}
          </div>

          <label>
            Submitter Note
            <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Optional note for staff..." />
          </label>

          <div className="actions">
            <button onClick={runPreview}>
              <Calculator size={16} /> Preview Cost
            </button>
            <button onClick={submitRequest} disabled={!preview}>
              <Send size={16} /> Submit Request
            </button>
          </div>

          {message && <p className="message">{message}</p>}
        </div>

        <PreviewPanel preview={preview} />
      </section>
    </RequireDiscord>
  );
}

function PreviewPanel({ preview }: { preview: any }) {
  if (!preview) {
    return (
      <div className="card muted-card">
        <h2>Preview</h2>
        <p>Pick an OC, enter target stats, then preview the cost.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>{preview.character?.name || "OC"} Upgrade Preview</h2>
      <div className="summary">
        <div>
          <span>Total Cost</span>
          <strong>{preview.total_cost} XP</strong>
        </div>
        <div>
          <span>Remaining</span>
          <strong className={preview.remaining_xp < 0 ? "bad" : ""}>{preview.remaining_xp} XP</strong>
        </div>
        <div>
          <span>Status</span>
          <strong className={preview.affordable ? "good" : "bad"}>{preview.affordable ? "Affordable" : "Not enough XP"}</strong>
        </div>
      </div>

      <div className="item-list">
        {preview.items.map((item: any) => (
          <div className="item-card" key={item.stat_key}>
            <h3>{STAT_LABELS[item.stat_key as keyof CoreStats] || item.stat_key}</h3>
            <p>
              {item.current_value} → {item.target_value} | +{item.points_added} points
            </p>
            <strong>{item.total_cost} XP</strong>
            <ul>
              {(item.breakdown || []).map((part: any, index: number) => (
                <li key={index}>
                  {part.from_value}–{part.to_value}: {part.points} × {part.cost_per_point} XP = {part.subtotal} XP
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function OCBalancesCard({ discordId, characterId }: { discordId: string; characterId: string }) {
  const [data, setData] = useState<any>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!discordId || !characterId) return;

    setMessage("");

    apiFetch(`/api/characters/${characterId}/balances`, {}, discordId)
      .then(setData)
      .catch((error) => {
        setData(null);
        setMessage(error.message || "Could not load balances.");
      });
  }, [discordId, characterId]);

  if (!characterId) return null;

  const xp = data?.xp || {};
  const currencies = data?.currencies || [];

  return (
    <div className="card oc-balances-card">
      <div className="card-title-row">
        <div>
          <h3>OC Balances</h3>
          <p className="muted-text">Current XP and currency balances for the selected character.</p>
        </div>
        {xp.source ? <span className="pill">{xp.source}</span> : null}
      </div>

      {message ? <p className="message">{message}</p> : null}

      <div className="oc-balances-grid">
        <div className="oc-balance-tile">
          <span>Available XP</span>
          <strong>{xp.available_xp ?? xp.current_xp ?? "—"}</strong>
        </div>
        <div className="oc-balance-tile">
          <span>Total XP</span>
          <strong>{xp.total_xp ?? "—"}</strong>
        </div>
        <div className="oc-balance-tile">
          <span>Spent XP</span>
          <strong>{xp.spent_xp ?? "—"}</strong>
        </div>

        {currencies.length === 0 ? (
          <div className="oc-balance-tile">
            <span>Currency</span>
            <strong>—</strong>
          </div>
        ) : null}

        {currencies.map((currency: any, index: number) => (
          <div className="oc-balance-tile" key={`${currency.currency_id || currency.name}-${index}`}>
            <span>
              {currency.emoji ? `${currency.emoji} ` : ""}
              {currency.ticker || currency.name || "Currency"}
            </span>
            <strong>{currency.balance ?? 0}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function OCMoneyCard({ discordId, characterId }: { discordId: string; characterId: string }) {
  const [data, setData] = useState<any>(null);
  const [message, setMessage] = useState("");

  async function loadBalances() {
    if (!discordId || !characterId) return;

    setMessage("");

    try {
      const result = await apiFetch(`/api/characters/${characterId}/balances`, {}, discordId);
      setData(result);
    } catch (error: any) {
      setData(null);
      setMessage(error.message || "Could not load money balances.");
    }
  }

  useEffect(() => {
    loadBalances();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, characterId]);

  if (!characterId) return null;

  const xp = data?.xp || {};
  const currencies = data?.currencies || [];

  return (
    <div className="card oc-money-card">
      <div className="card-title-row">
        <div>
          <span className="activity-type-label">Wallet</span>
          <h3>XP & Currency</h3>
          <p className="muted-text">The selected OC’s current progression and money balances.</p>
        </div>
        <button className="ghost" onClick={loadBalances}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {message ? <p className="message">{message}</p> : null}

      <div className="oc-money-grid">
        <div className="oc-money-tile xp-tile">
          <span>Available XP</span>
          <strong>{xp.available_xp ?? xp.current_xp ?? "—"}</strong>
        </div>
        <div className="oc-money-tile">
          <span>Total XP</span>
          <strong>{xp.total_xp ?? "—"}</strong>
        </div>
        <div className="oc-money-tile">
          <span>Spent XP</span>
          <strong>{xp.spent_xp ?? "—"}</strong>
        </div>

        {currencies.length === 0 ? (
          <div className="oc-money-tile">
            <span>Currency</span>
            <strong>—</strong>
          </div>
        ) : null}

        {currencies.map((currency: any, index: number) => (
          <div className="oc-money-tile currency-tile" key={`${currency.currency_id || currency.name}-${index}`}>
            <span>
              {currency.emoji ? `${currency.emoji} ` : ""}
              {currency.ticker || currency.name || "Currency"}
            </span>
            <strong>{currency.balance ?? 0}</strong>
            {currency.name && currency.ticker ? <small>{currency.name}</small> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function OCManagementCard({ discordId, characterId }: { discordId: string; characterId: string }) {
  const [data, setData] = useState<any>(null);
  const [form, setForm] = useState({
    name: "",
    occupation: "",
    affiliation: "",
    sheet_url: "",
    portrait_url: "",
    blurb: "",
  });
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");

  async function loadManagement() {
    if (!discordId || !characterId) return;

    setMessage("");

    try {
      const result = await apiFetch(`/api/characters/${characterId}/manage`, {}, discordId);
      setData(result);

      const character = result.character || {};
      setForm({
        name: character.name || "",
        occupation: character.occupation || "",
        affiliation: character.affiliation || "",
        sheet_url: character.sheet_url || "",
        portrait_url: character.portrait_url || "",
        blurb: character.blurb || "",
      });
    } catch (error: any) {
      setData(null);
      setMessage(error.message || "Could not load OC management.");
    }
  }

  useEffect(() => {
    loadManagement();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, characterId]);

  async function saveChanges() {
    if (!characterId) return;

    setSaving(true);
    setMessage("");

    try {
      const result = await apiFetch(
        `/api/characters/${characterId}/manage`,
        {
          method: "PATCH",
          body: JSON.stringify(form),
        },
        discordId
      );

      setData((current: any) => ({ ...(current || {}), character: result.character }));
      setMessage(result.message || "OC updated.");
    } catch (error: any) {
      setMessage(error.message || "Could not save OC changes.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveOC() {
    if (!characterId) return;

    setSaving(true);
    setMessage("");

    try {
      const result = await apiFetch(
        `/api/characters/${characterId}/archive`,
        { method: "POST" },
        discordId
      );
      setData((current: any) => ({ ...(current || {}), character: result.character }));
      setMessage(result.message || "OC archived.");
    } catch (error: any) {
      setMessage(error.message || "Could not archive OC.");
    } finally {
      setSaving(false);
    }
  }

  async function restoreOC() {
    if (!characterId) return;

    setSaving(true);
    setMessage("");

    try {
      const result = await apiFetch(
        `/api/characters/${characterId}/restore`,
        { method: "POST" },
        discordId
      );
      setData((current: any) => ({ ...(current || {}), character: result.character }));
      setMessage(result.message || "OC restored.");
    } catch (error: any) {
      setMessage(error.message || "Could not restore OC.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteOC() {
    if (!characterId || deleteConfirm !== "DELETE") return;

    setSaving(true);
    setMessage("");

    try {
      const result = await apiFetch(
        `/api/characters/${characterId}`,
        { method: "DELETE" },
        discordId
      );

      setMessage(result.message || "OC deleted.");
      setData(null);
      setDeleteConfirm("");
    } catch (error: any) {
      setMessage(error.message || "Could not delete OC.");
    } finally {
      setSaving(false);
    }
  }

  if (!characterId) return null;

  const character = data?.character || {};
  const canEdit = data?.can_edit;
  const staff = data?.is_staff;
  const archived = character.is_active === false || character.archived === true || String(character.status || "").toLowerCase() === "archived";

  return (
    <div className="card oc-management-card">
      <div className="card-title-row">
        <div>
          <span className="activity-type-label">Management</span>
          <h3>Manage OC</h3>
          <p className="muted-text">Edit this OC’s public dashboard information and manage visibility.</p>
        </div>
        <button className="ghost" onClick={loadManagement}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {message ? <p className="message">{message}</p> : null}

      {!canEdit ? (
        <p className="muted-text">You can view this OC, but only the owner or staff can edit it.</p>
      ) : (
        <>
          <div className="oc-management-form">
            <label>
              <span>Name</span>
              <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
            </label>

            <label>
              <span>Occupation</span>
              <input value={form.occupation} onChange={(event) => setForm((current) => ({ ...current, occupation: event.target.value }))} />
            </label>

            <label>
              <span>Affiliation</span>
              <input value={form.affiliation} onChange={(event) => setForm((current) => ({ ...current, affiliation: event.target.value }))} />
            </label>

            <label>
              <span>Sheet Link</span>
              <input value={form.sheet_url} onChange={(event) => setForm((current) => ({ ...current, sheet_url: event.target.value }))} />
            </label>

            <label>
              <span>Portrait URL</span>
              <input value={form.portrait_url} onChange={(event) => setForm((current) => ({ ...current, portrait_url: event.target.value }))} />
            </label>

            <label className="oc-management-wide">
              <span>Public Blurb</span>
              <textarea rows={4} value={form.blurb} onChange={(event) => setForm((current) => ({ ...current, blurb: event.target.value }))} />
            </label>
          </div>

          <div className="auth-actions">
            <button onClick={saveChanges} disabled={saving}>{saving ? "Saving..." : "Save OC Changes"}</button>
            {archived ? (
              <button className="ghost" onClick={restoreOC} disabled={saving}>Restore OC</button>
            ) : (
              <button className="ghost" onClick={archiveOC} disabled={saving}>Archive OC</button>
            )}
          </div>

          {staff ? (
            <div className="oc-danger-zone">
              <h4>Staff Danger Zone</h4>
              <p className="muted-text">For test OCs or cleanup only. Type DELETE to permanently remove this OC and related rows.</p>
              <div className="auth-actions">
                <input
                  value={deleteConfirm}
                  onChange={(event) => setDeleteConfirm(event.target.value)}
                  placeholder="Type DELETE"
                />
                <button className="danger-button" onClick={deleteOC} disabled={saving || deleteConfirm !== "DELETE"}>
                  Delete OC
                </button>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function ManageOCDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
}) {
  const [characters, setCharacters] = useState<any[]>([]);
  const [message, setMessage] = useState("");

  async function loadCharacters() {
    if (!discordId) return;

    setMessage("");

    try {
      const data = await apiFetch("/api/characters/mine", {}, discordId);
      const rows = Array.isArray(data) ? data : data.characters || data.data || [];
      setCharacters(rows);

      const validSelectedCharacter = rows.some((character: any) =>
        String(character.character_id || character.id || "") === String(selectedCharacterId || "")
      );

      if (selectedCharacterId && !validSelectedCharacter) {
        setSelectedCharacterId("");
      }

      if (!selectedCharacterId && rows.length > 0 && shouldAutoSelectOc()) {
        setSelectedCharacterId(String(rows[0].character_id || rows[0].id));
      }
    } catch (error: any) {
      setMessage(error.message || "Could not load your OCs.");
    }
  }

  useEffect(() => {
    loadCharacters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  const selected = characters.find(
    (character) => String(character.character_id || character.id) === String(selectedCharacterId)
  );

  return (
    <RequireDiscord discordId={discordId}>
      <section className="manage-oc-page">
        <div className="card manage-oc-hero">
          <div>
            <span className="activity-type-label">Character Controls</span>
            <h2>Manage OC</h2>
            <p className="muted-text">
              Edit public profile details, sheet links, portraits, and visibility controls without cluttering the main OC dashboard.
            </p>
          </div>
          <button className="ghost" onClick={loadCharacters}>
            <RefreshCw size={16} /> Refresh OCs
          </button>
        </div>

        <div className="card manage-oc-picker-card">
          <label>
            <span>Choose OC</span>
            <select
              value={selectedCharacterId}
              onChange={(event) => setSelectedCharacterId(event.target.value)}
            >
              <option value="">Select an OC</option>
              {characters.map((character) => {
                const id = String(character.character_id || character.id || "");
                return (
                  <option value={id} key={id}>
                    {character.name || "Unnamed OC"}
                  </option>
                );
              })}
            </select>
          </label>

          {selected ? (
            <p className="muted-text">
              Managing <strong>{selected.name}</strong>. Changes here update the OC record and public-facing profile fields.
            </p>
          ) : null}

          {message ? <p className="message">{message}</p> : null}
        </div>

        {selectedCharacterId ? (
          <OCManagementCard discordId={discordId} characterId={selectedCharacterId} />
        ) : (
          <div className="card">
            <p className="muted-text">Pick an OC above to open management tools.</p>
          </div>
        )}
      </section>
    </RequireDiscord>
  );
}

function OCDashboard({ discordId, selectedCharacterId, setSelectedCharacterId, jump }: { discordId: string; selectedCharacterId: string; setSelectedCharacterId: (id: string) => void; jump?: (tab: Tab) => void }) {
  const [summary, setSummary] = useState<any>(null);
  const [ownedSkills, setOwnedSkills] = useState<any[]>([]);
  const [skillRequests, setSkillRequests] = useState<any[]>([]);
  const [message, setMessage] = useState("");

  async function load() {
    if (!selectedCharacterId) return;

    setMessage("");

    const [summaryData, catalogData, characterSkillData] = await Promise.all([
      apiFetch(`/api/characters/${selectedCharacterId}/summary`, {}, discordId),
      apiFetch("/api/skills", {}, discordId),
      apiFetch(`/api/characters/${selectedCharacterId}/skills`, {}, discordId),
    ]);

    setSummary(summaryData);

    const catalog = catalogData.skills || [];
    const ownedKeys = characterSkillData.owned_keys || [];

    const owned = ownedKeys
      .map((skillKey: string) => {
        const skill = catalog.find((entry: any) => entry.skill_key === skillKey);

        return {
          skill_key: skillKey,
          ...(skill || {}),
        };
      })
      .sort((a: any, b: any) => {
        const treeCompare = String(a.tree || "").localeCompare(String(b.tree || ""));
        if (treeCompare !== 0) return treeCompare;

        const tierCompare = Number(a.tier ?? 0) - Number(b.tier ?? 0);
        if (tierCompare !== 0) return tierCompare;

        return String(a.name || a.skill_key).localeCompare(String(b.name || b.skill_key));
      });

    setOwnedSkills(owned);
    const enrichedRequests = (characterSkillData.requests || []).map((request: any) => {
      const skill = catalog.find((entry: any) => entry.skill_key === request.skill_key);

      return {
        ...request,
        skill_name: skill?.name || request.skill_key,
        tree: skill?.tree,
        tier: skill?.tier,
      };
    });

    setSkillRequests(enrichedRequests);
  }

  useEffect(() => {
    if (selectedCharacterId && discordId) load().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCharacterId, discordId]);

  const groupedOwnedSkills = ownedSkills.reduce<Record<string, any[]>>((groups, skill) => {
    const tree = String(skill.tree || "Other");
    if (!groups[tree]) groups[tree] = [];
    groups[tree].push(skill);
    return groups;
  }, {});

  const pendingRequests = skillRequests.filter((request) => String(request.status || "").toLowerCase() === "pending");
return (
    <RequireDiscord discordId={discordId}>
      {jump ? (
        <div className="card oc-manage-jump-card">
          <div>
            <span className="activity-type-label">Need to edit?</span>
            <h3>Manage this OC</h3>
            <p className="muted-text">Open the dedicated management tab to edit profile details, archive, restore, or clean up test OCs.</p>
          </div>
          <button onClick={() => jump("manage_oc")}>Edit / Manage This OC</button>
        </div>
      ) : null}
      <OCMoneyCard discordId={discordId} characterId={selectedCharacterId} />
<section className="grid oc-dashboard-grid">
        <div className="card">
          <div className="card-title-row">
            <h2>OC Dashboard</h2>
            <button className="ghost" onClick={load}><RefreshCw size={16} /> Refresh</button>
          </div>
          <CharacterSelect discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />
          {message && <p className="message">{message}</p>}
          {summary && (
            <>
              <h3>{summary.character?.name}</h3>
              <div className="stat-strip">
                <span>Available XP</span>
                <strong>{summary.wallet?.available_xp ?? 0}</strong>
              </div>
              <h3>Core Stats</h3>
              <div className="mini-stat-grid">
                {(Object.keys(STAT_LABELS) as Array<keyof CoreStats>).map((key) => (
                  <div key={key} className="mini-stat"><span>{STAT_LABELS[key]}</span><strong>{summary.stats?.[key] ?? 0}</strong></div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="card oc-traits-card">
          <div className="card-title-row">
            <div>
              <h2>Traits</h2>
              <p className="muted-text">Selected traits currently attached to this OC.</p>
            </div>
            <span className="pill">{(summary?.traits || []).length} traits</span>
          </div>

          {!summary ? <p>Select an OC to load traits.</p> : null}

          {summary && (summary.traits || []).length === 0 ? (
            <p>No traits found yet. Approved or staff-granted traits will appear here once attached to this OC.</p>
          ) : null}

          {summary && (summary.traits || []).length > 0 ? (
            <div className="owned-skill-list">
              {(summary.traits || []).map((trait: any, index: number) => (
                <div className="owned-skill-row" key={`${trait.slug || trait.trait_id || trait.name}-${index}`}>
                  <div>
                    <strong>{trait.name || trait.slug || "Trait"}</strong>
                    {trait.description ? <small>{trait.description}</small> : null}
                  </div>
                  <div className="owned-skill-meta">
                    <span>{trait.tier || trait.category || "Trait"}</span>
                    {trait.cost !== null && trait.cost !== undefined ? <span>{trait.cost} pts</span> : null}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="card oc-skills-card">
          <div className="card-title-row">
            <div>
              <h2>Owned Skills</h2>
              <p className="muted-text">A clean list of skills this OC already has.</p>
            </div>
            <span className="pill good">{ownedSkills.length} owned</span>
          </div>

          {!selectedCharacterId ? <p>Select an OC to view owned skills.</p> : null}

          {selectedCharacterId && ownedSkills.length === 0 ? (
            <p>No owned skills found yet. Requested skills will appear here after staff approval.</p>
          ) : null}

          {Object.entries(groupedOwnedSkills).map(([tree, skills]) => (
            <div className="owned-skill-group" key={tree}>
              <div className="owned-skill-group-heading">
                <h3>{tree}</h3>
                <span>{skills.length}</span>
              </div>

              <div className="owned-skill-list">
                {skills.map((skill) => (
                  <div className="owned-skill-row" key={skill.skill_key}>
                    <div>
                      <strong>{skill.name || skill.skill_key}</strong>
                    </div>
                    <div className="owned-skill-meta">
                      <span>Tier {skill.tier ?? "—"}</span>
                      <span>{skill.cost ?? 0} XP</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {pendingRequests.length > 0 ? (
            <div className="oc-pending-skills">
              <h3>Pending Skill Requests</h3>
              <div className="owned-skill-list">
                {pendingRequests.slice(0, 6).map((request) => (
                  <div className="owned-skill-row pending" key={request.request_id}>
                    <div>
                      <strong>{request.skill_name || request.skill_key}</strong>
                    </div>
                    <div className="owned-skill-meta">
                      <span>Pending</span>
                      <span>{request.cost ?? 0} XP</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="card">
          <h2>Derived Stats</h2>
          {!summary ? <p>Select an OC to load derived stats.</p> : (
            <div className="summary vertical">
              {Object.entries(summary.derived || {}).map(([key, value]) => (
                <div key={key}>
                  <span>{key.replaceAll("_", " ")}</span>
                  <strong>{String(value)}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </RequireDiscord>
  );
}


// ============================================================
// LOADOUTS DASHBOARD
// Full loadout builder with CC tracking, worn/carried sections
// ============================================================

function LoadoutsDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
}) {
  const [characters, setCharacters] = useState<any[]>([]);
  const [localCharId, setLocalCharId] = useState(selectedCharacterId || "");
  const [loadouts, setLoadouts] = useState<any[]>([]);
  const [activeLoadoutName, setActiveLoadoutName] = useState("");
  const [baseCC, setBaseCC] = useState(4);
  const [strength, setStrength] = useState(0);
  const [selectedLoadout, setSelectedLoadout] = useState<any | null>(null);
  const [inventory, setInventory] = useState<any[]>([]);
  const [view, setView] = useState<"list" | "builder">("list");
  const [newLoadoutName, setNewLoadoutName] = useState("");
  const [msg, setMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [loading, setLoading] = useState(false);

  function flash(text: string, type: "ok" | "err" = "ok") {
    setMsg({ text, type });
    setTimeout(() => setMsg({ text: "", type: "ok" }), 4000);
  }

  async function loadCharacters() {
    if (!discordId) return;
    try {
      const result = await apiFetch("/api/characters/mine", {}, discordId);
      const rows = Array.isArray(result) ? result : result.characters || result.data || [];
      setCharacters(rows);
      if (!localCharId && rows.length > 0) {
        const id = String(rows[0].character_id || rows[0].id);
        setLocalCharId(id);
        setSelectedCharacterId(id);
      }
    } catch { /* silent */ }
  }

  async function loadLoadouts(cid = localCharId) {
    if (!discordId || !cid) return;
    setLoading(true);
    try {
      const data = await apiFetch(`/api/loadouts/${cid}`, {}, discordId);
      setLoadouts(data.loadouts || []);
      setActiveLoadoutName(data.active_loadout_name || "");
      setBaseCC(data.base_cc || 4);
      setStrength(data.strength || 0);
    } catch (e: any) {
      flash(e.message || "Could not load loadouts.", "err");
    } finally {
      setLoading(false);
    }
  }

  async function openLoadout(lo: any) {
    if (!localCharId) return;
    try {
      const data = await apiFetch(`/api/loadouts/${localCharId}/${encodeURIComponent(lo.loadout_name)}`, {}, discordId);
      setSelectedLoadout(data);
      setInventory(data.inventory || []);
      setView("builder");
    } catch (e: any) {
      flash(e.message || "Could not load loadout.", "err");
    }
  }

  async function createLoadout() {
    const name = newLoadoutName.trim();
    if (!name) { flash("Loadout name required.", "err"); return; }
    try {
      await apiFetch(`/api/loadouts/${localCharId}`, { method: "POST", body: JSON.stringify({ loadout_name: name }) }, discordId);
      setNewLoadoutName("");
      flash(`"${name}" created.`);
      loadLoadouts();
    } catch (e: any) {
      flash(e.message || "Could not create loadout.", "err");
    }
  }

  async function deleteLoadout(name: string) {
    if (!confirm(`Delete loadout "${name}"?`)) return;
    try {
      await apiFetch(`/api/loadouts/${localCharId}/${encodeURIComponent(name)}`, { method: "DELETE" }, discordId);
      if (selectedLoadout?.loadout_name === name) { setSelectedLoadout(null); setView("list"); }
      flash(`"${name}" deleted.`);
      loadLoadouts();
    } catch (e: any) {
      flash(e.message || "Could not delete.", "err");
    }
  }

  async function activateLoadout(name: string) {
    try {
      await apiFetch(`/api/loadouts/${localCharId}/${encodeURIComponent(name)}/activate`, { method: "POST" }, discordId);
      setActiveLoadoutName(name);
      flash(`"${name}" is now your active loadout.`);
      loadLoadouts();
    } catch (e: any) {
      flash(e.message || "Could not activate.", "err");
    }
  }

  async function updateItem(itemId: string, qty: number, worn: boolean) {
    if (!selectedLoadout || !localCharId) return;
    const changes: Record<string, any> = {};
    if (qty <= 0) {
      changes[itemId] = null; // remove
    } else {
      changes[itemId] = { qty, worn };
    }
    try {
      const data = await apiFetch(
        `/api/loadouts/${localCharId}/${encodeURIComponent(selectedLoadout.loadout_name)}`,
        { method: "PATCH", body: JSON.stringify({ items: changes }) },
        discordId
      );
      setSelectedLoadout(data.loadout);
    } catch (e: any) {
      flash(e.message || "Could not update.", "err");
    }
  }

  useEffect(() => { loadCharacters(); }, [discordId]);
  useEffect(() => { if (localCharId) loadLoadouts(localCharId); }, [localCharId]);

  const ccData = selectedLoadout?.cc;
  const totalCC = ccData ? ccData.total_cc : baseCC;
  const ccUsed = ccData ? ccData.cc_used : 0;
  const ccOver = ccData ? ccData.over_capacity : false;

  // Items in this loadout by id for quick lookup
  const loadoutItems: Record<string, { qty: number; worn: boolean }> = selectedLoadout?.items || {};

  // Inventory items not yet in loadout (for adding)
  const availableToAdd = inventory.filter(inv => {
    const inLoadout = loadoutItems[inv.item_id];
    return !inLoadout || inLoadout.qty < inv.qty_owned;
  });

  return (
    <section>
      <div className="card market-hero" style={{ marginBottom: "1rem" }}>
        <div>
          <span className="activity-type-label">Character Gear</span>
          <h2>Loadouts</h2>
          <p className="muted-text">Build and manage what your character carries into scenes. CC tracks carry capacity.</p>
        </div>
        <button className="ghost" onClick={() => loadLoadouts()}><RefreshCw size={16} /></button>
      </div>

      {msg.text && (
        <p style={{
          fontSize: 13, padding: "8px 12px", borderRadius: "var(--border-radius-md)", marginBottom: 12,
          background: msg.type === "ok" ? "var(--color-background-success)" : "var(--color-background-danger)",
          color: msg.type === "ok" ? "var(--color-text-success)" : "var(--color-text-danger)",
          border: `0.5px solid ${msg.type === "ok" ? "var(--color-border-success)" : "var(--color-border-danger)"}`,
        }}>{msg.text}</p>
      )}

      {/* Character selector */}
      <div className="card" style={{ padding: "12px 14px", marginBottom: "1rem", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>Character:</label>
        <select value={localCharId} onChange={(e) => { setLocalCharId(e.target.value); setSelectedCharacterId(e.target.value); setView("list"); setSelectedLoadout(null); }} style={{ flex: 1, minWidth: 160 }}>
          <option value="">Select character...</option>
          {characters.map((c: any) => (
            <option key={c.character_id || c.id} value={c.character_id || c.id}>{c.name}</option>
          ))}
        </select>
        <span className="muted-text" style={{ fontSize: 12 }}>STR {strength} → Base CC: {baseCC}</span>
      </div>

      {view === "list" && (
        <>
          {/* Create new loadout */}
          <div className="card" style={{ padding: "12px 14px", marginBottom: "1rem", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input
              value={newLoadoutName}
              onChange={(e) => setNewLoadoutName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createLoadout()}
              placeholder="New loadout name (e.g. Forest Run, PvP Kit)"
              style={{ flex: 1, minWidth: 200 }}
            />
            <button onClick={createLoadout} disabled={!localCharId || !newLoadoutName.trim()}>
              <Plus size={14} /> Create Loadout
            </button>
          </div>

          {loading && <p className="muted-text" style={{ fontSize: 13 }}>Loading...</p>}

          {loadouts.length === 0 && !loading && (
            <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-secondary)" }}>
              <Package size={36} style={{ marginBottom: 8, opacity: 0.25 }} />
              <p style={{ fontSize: 13 }}>No loadouts yet. Create one above.</p>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {loadouts.map((lo: any) => {
              const cc = lo.cc;
              const isActive = lo.loadout_name === activeLoadoutName;
              return (
                <div key={lo.loadout_name} className="card" style={{ padding: "12px 14px", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <p style={{ fontWeight: 500, fontSize: 14 }}>{lo.loadout_name}</p>
                      {isActive && <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 20, background: "var(--color-background-success)", color: "var(--color-text-success)" }}>⭐ Active</span>}
                    </div>
                    {cc && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <p className="muted-text" style={{ fontSize: 12 }}>CC: {cc.cc_used}/{cc.total_cc}</p>
                        <div style={{ width: 80, height: 4, borderRadius: 2, background: "var(--color-background-tertiary)", overflow: "hidden" }}>
                          <div style={{ height: "100%", borderRadius: 2, width: `${Math.min(100, (cc.cc_used / (cc.total_cc || 4)) * 100)}%`, background: cc.over_capacity ? "var(--color-background-danger)" : "var(--color-background-success)" }} />
                        </div>
                        {cc.over_capacity && <span style={{ fontSize: 11, color: "var(--color-text-danger)" }}>Over!</span>}
                        <p className="muted-text" style={{ fontSize: 12 }}>{(cc.worn_items?.length || 0) + (cc.carried_items?.length || 0)} items</p>
                      </div>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    <button className="ghost" onClick={() => openLoadout(lo)} style={{ fontSize: 12, padding: "4px 10px" }}><Edit size={13} /> Edit</button>
                    {!isActive && <button className="ghost" onClick={() => activateLoadout(lo.loadout_name)} style={{ fontSize: 12, padding: "4px 10px" }}>⭐ Set Active</button>}
                    <button className="ghost" onClick={() => deleteLoadout(lo.loadout_name)} style={{ fontSize: 12, padding: "4px 10px", color: "var(--color-text-danger)" }}><Trash2 size={13} /></button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {view === "builder" && selectedLoadout && (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "1rem", flexWrap: "wrap" }}>
            <button className="ghost" onClick={() => { setView("list"); loadLoadouts(); }} style={{ fontSize: 13 }}><X size={13} /> Back to loadouts</button>
            <h3 style={{ fontSize: 16, fontWeight: 500 }}>{selectedLoadout.loadout_name}</h3>
            {selectedLoadout.loadout_name === activeLoadoutName && <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 20, background: "var(--color-background-success)", color: "var(--color-text-success)" }}>⭐ Active</span>}
          </div>

          {/* CC Bar */}
          <div className="card" style={{ padding: "12px 16px", marginBottom: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <p style={{ fontWeight: 500, fontSize: 14 }}>Carry Capacity</p>
              <p style={{ fontSize: 18, fontWeight: 600, color: ccOver ? "var(--color-text-danger)" : "var(--color-text-success)" }}>{ccUsed} / {totalCC}</p>
            </div>
            <div style={{ height: 10, borderRadius: 5, background: "var(--color-background-tertiary)", overflow: "hidden", marginBottom: 4 }}>
              <div style={{ height: "100%", borderRadius: 5, width: `${Math.min(100, (ccUsed / (totalCC || 4)) * 100)}%`, background: ccOver ? "var(--color-background-danger)" : "var(--color-background-success)", transition: "width 0.3s ease" }} />
            </div>
            <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--color-text-secondary)" }}>
              <span>Base CC: {ccData?.base_cc || baseCC} (STR {strength})</span>
              {(ccData?.cc_bonus || 0) > 0 && <span>+{ccData.cc_bonus} bonus CC from worn items</span>}
              <span>{totalCC - ccUsed} remaining</span>
            </div>
            {ccOver && <p style={{ fontSize: 12, color: "var(--color-text-danger)", marginTop: 4 }}>⚠️ Over carry capacity! Remove items from CARRIED section.</p>}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* WORN column */}
            <div>
              <h4 style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                🧥 WORN <span className="muted-text" style={{ fontSize: 12, fontWeight: 400 }}>(armor, backpack — CC ignored)</span>
              </h4>
              {(ccData?.worn_items || []).length === 0 && (
                <div className="card" style={{ padding: "1rem", textAlign: "center", color: "var(--color-text-secondary)", fontSize: 13 }}>Nothing worn</div>
              )}
              {(ccData?.worn_items || []).map((item: any) => (
                <div key={item.item_id} className="card" style={{ padding: "8px 12px", marginBottom: 8, display: "flex", gap: 8, alignItems: "center" }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 500 }}>{item.name}</p>
                    <p className="muted-text" style={{ fontSize: 11 }}>{item.item_class} · CC {item.cc} (ignored) · ×{item.qty}</p>
                  </div>
                  <button className="ghost" onClick={() => updateItem(item.item_id, item.qty, false)} style={{ fontSize: 11, padding: "3px 8px" }}>→ Carry</button>
                  <button className="ghost" onClick={() => updateItem(item.item_id, 0, true)} style={{ fontSize: 11, padding: "3px 8px", color: "var(--color-text-danger)" }}><X size={11} /></button>
                </div>
              ))}
            </div>

            {/* CARRIED column */}
            <div>
              <h4 style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                🎒 CARRIED <span className="muted-text" style={{ fontSize: 12, fontWeight: 400 }}>(counts against CC)</span>
              </h4>
              {(ccData?.carried_items || []).length === 0 && (
                <div className="card" style={{ padding: "1rem", textAlign: "center", color: "var(--color-text-secondary)", fontSize: 13 }}>Nothing carried</div>
              )}
              {(ccData?.carried_items || []).map((item: any) => (
                <div key={item.item_id} className="card" style={{ padding: "8px 12px", marginBottom: 8, display: "flex", gap: 8, alignItems: "center" }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 500 }}>{item.name}</p>
                    <p className="muted-text" style={{ fontSize: 11 }}>{item.item_class} · {item.cc} CC each · ×{item.qty} = {item.cc_cost} CC</p>
                  </div>
                  <button className="ghost" onClick={() => updateItem(item.item_id, item.qty, true)} style={{ fontSize: 11, padding: "3px 8px" }}>→ Wear</button>
                  <button className="ghost" onClick={() => updateItem(item.item_id, 0, false)} style={{ fontSize: 11, padding: "3px 8px", color: "var(--color-text-danger)" }}><X size={11} /></button>
                </div>
              ))}
            </div>
          </div>

          {/* Add from inventory */}
          <div style={{ marginTop: "1.5rem" }}>
            <h4 style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>Add from inventory</h4>
            {availableToAdd.length === 0 && (
              <p className="muted-text" style={{ fontSize: 13 }}>All owned items are already in this loadout.</p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {availableToAdd.map((inv: any) => {
                const inLoadout = loadoutItems[inv.item_id];
                const maxQty = inv.qty_owned - (inLoadout?.qty || 0);
                return (
                  <div key={inv.item_id} className="card" style={{ padding: "8px 12px", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 500 }}>{inv.name}</p>
                      <p className="muted-text" style={{ fontSize: 11 }}>{inv.item_class} · {inv.cc} CC · {inv.qty_owned} owned{inLoadout ? ` · ${inLoadout.qty} already in loadout` : ""}</p>
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="ghost" onClick={() => updateItem(inv.item_id, Math.min(1, maxQty), true)} style={{ fontSize: 11, padding: "3px 8px" }}>+ Wear</button>
                      <button className="ghost" onClick={() => updateItem(inv.item_id, Math.min(1, maxQty), false)} style={{ fontSize: 11, padding: "3px 8px" }}>+ Carry</button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function InventoryDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
}) {
  const [characters, setCharacters] = useState<any[]>([]);
  const [data, setData] = useState<any>({ items: [], currencies: [], types: [] });
  const [search, setSearch] = useState("");
  const [itemType, setItemType] = useState("all");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadCharacters() {
    if (!discordId) return;

    try {
      const result = await apiFetch("/api/characters/mine", {}, discordId);
      const rows = Array.isArray(result) ? result : result.characters || result.data || [];
      setCharacters(rows);

      if (!selectedCharacterId && rows.length > 0 && shouldAutoSelectOc()) {
        setSelectedCharacterId(String(rows[0].character_id || rows[0].id));
      }
    } catch (error: any) {
      setMessage(error.message || "Could not load your OCs.");
    }
  }

  async function loadInventory() {
    if (!discordId || !selectedCharacterId) return;

    setLoading(true);
    setMessage("");

    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if (itemType !== "all") params.set("item_type", itemType);

      const suffix = params.toString() ? `?${params.toString()}` : "";
      const result = await apiFetch(`/api/inventory/characters/${selectedCharacterId}${suffix}`, {}, discordId);
      setData(result);
    } catch (error: any) {
      setData({ items: [], currencies: [], types: [] });
      setMessage(error.message || "Could not load inventory.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCharacters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  useEffect(() => {
    loadInventory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, selectedCharacterId, itemType]);

  const selected = characters.find(
    (character) => String(character.character_id || character.id) === String(selectedCharacterId)
  );

  const items = data.items || [];
  const currencies = data.currencies || [];
  const types = Array.from(new Set([...(data.types || []), ...items.map((item: any) => item.type || "Item")])).sort();

  function submitSearch(event: React.FormEvent) {
    event.preventDefault();
    loadInventory();
  }

  function itemBadge(item: any) {
    if (item.is_equipped) return "Equipped";
    if (item.is_locked) return "Locked";
    return item.type || "Item";
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="inventory-page">
        <div className="card inventory-hero">
          <div>
            <span className="activity-type-label">Character Goods</span>
            <h2>Inventory</h2>
            <p className="muted-text">
              Review an OC’s items, quantities, categories, sources, and currency balances.
            </p>
          </div>
          <button className="ghost" onClick={loadInventory} disabled={loading}>
            <RefreshCw size={16} /> {loading ? "Loading..." : "Refresh"}
          </button>
        </div>

        <div className="card inventory-controls">
          <label>
            <span>Choose OC</span>
            <select
              value={selectedCharacterId}
              onChange={(event) => setSelectedCharacterId(event.target.value)}
            >
              <option value="">Select an OC</option>
              {characters.map((character) => {
                const id = String(character.character_id || character.id || "");
                return (
                  <option value={id} key={id}>
                    {character.name || "Unnamed OC"}
                  </option>
                );
              })}
            </select>
          </label>

          <form onSubmit={submitSearch} className="inventory-search-form">
            <label>
              <span>Search</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search items, source, notes..."
              />
            </label>
            <button type="submit">Search</button>
          </form>

          <label>
            <span>Category</span>
            <select value={itemType} onChange={(event) => setItemType(event.target.value)}>
              <option value="all">All categories</option>
              {types.map((type: any) => (
                <option value={type} key={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
        </div>

        {message ? <p className="message">{message}</p> : null}

        {/* CC Meter */}
        {data.base_cc !== undefined && (
          <div className="card" style={{ padding: "12px 16px", marginBottom: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
              <div>
                <p style={{ fontWeight: 500, fontSize: 14 }}>Carry Capacity</p>
                {data.active_loadout_cc ? (
                  <p className="muted-text" style={{ fontSize: 12 }}>Active loadout: <strong>{data.active_loadout_cc.loadout_name}</strong></p>
                ) : (
                  <p className="muted-text" style={{ fontSize: 12 }}>No active loadout — CC shown for full inventory</p>
                )}
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: 18, fontWeight: 600, color: (data.active_loadout_cc?.over_capacity) ? "var(--color-text-danger)" : "var(--color-text-success)" }}>
                  {data.active_loadout_cc ? data.active_loadout_cc.cc_used : 0} / {data.base_cc}
                </p>
                <p className="muted-text" style={{ fontSize: 11 }}>CC used / total (STR {data.strength})</p>
              </div>
            </div>
            <div style={{ height: 8, borderRadius: 4, background: "var(--color-background-tertiary)", overflow: "hidden" }}>
              <div style={{
                height: "100%",
                borderRadius: 4,
                width: `${Math.min(100, ((data.active_loadout_cc?.cc_used || 0) / (data.base_cc || 4)) * 100)}%`,
                background: (data.active_loadout_cc?.over_capacity) ? "var(--color-background-danger)" : "var(--color-background-success)",
                transition: "width 0.3s ease",
              }} />
            </div>
            {data.active_loadout_cc?.over_capacity && (
              <p style={{ fontSize: 12, color: "var(--color-text-danger)", marginTop: 4 }}>⚠️ Over carry capacity!</p>
            )}
          </div>
        )}

        <div className="inventory-summary-grid">
          <div className="card inventory-summary-card">
            <span>Selected OC</span>
            <strong>{selected?.name || data.character?.name || "—"}</strong>
          </div>
          <div className="card inventory-summary-card">
            <span>Unique Items</span>
            <strong>{data.total_items ?? items.length}</strong>
          </div>
          <div className="card inventory-summary-card">
            <span>Total Quantity</span>
            <strong>{data.total_quantity ?? items.reduce((sum: number, item: any) => sum + Number(item.quantity || 0), 0)}</strong>
          </div>
        </div>

        <div className="card inventory-wallet-card">
          <div className="card-title-row">
            <div>
              <h3>Currency Balances</h3>
              <p className="muted-text">Quick money preview for this OC.</p>
            </div>
          </div>

          <div className="inventory-currency-grid">
            {currencies.length === 0 ? (
              <div className="inventory-empty-inline">
                <strong>No currency found.</strong>
                <span>Wallet balances will show here once this OC has money.</span>
              </div>
            ) : null}

            {currencies.map((currency: any, index: number) => (
              <div className="inventory-currency-tile" key={`${currency.currency_id || currency.name}-${index}`}>
                <span>
                  {currency.emoji ? `${currency.emoji} ` : ""}
                  {currency.ticker || currency.name || "Currency"}
                </span>
                <strong>{currency.balance ?? 0}</strong>
                {currency.name && currency.ticker ? <small>{currency.name}</small> : null}
              </div>
            ))}
          </div>
        </div>

        <div className="inventory-item-grid">
          {items.length === 0 ? (
            <div className="card inventory-empty-state">
              <strong>No items found.</strong>
              <p className="muted-text">
                This OC does not have inventory rows yet, or your search/filter did not match anything.
              </p>
            </div>
          ) : null}

          {items.map((item: any, index: number) => (
            <div className="card inventory-item-card" key={`${item.inventory_id || item.name}-${index}`}>
              <div className="inventory-item-top">
                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  {item.image_url && (
                    <img
                      src={item.image_url}
                      alt={item.name}
                      style={{ width: "52px", height: "52px", borderRadius: "8px", objectFit: "cover", flexShrink: 0, border: "1px solid rgba(255,255,255,0.1)" }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  )}
                  <div>
                    <span className="activity-type-label">{itemBadge(item)}</span>
                    <h3>{item.name || "Unnamed Item"}</h3>
                  </div>
                </div>
                <strong className="inventory-quantity">×{item.quantity ?? 1}</strong>
              </div>

              {item.description ? <p className="muted-text">{item.description}</p> : null}

              <div className="inventory-item-meta">
                <span>Type: {item.type || "Item"}</span>
                {item.source ? <span>Source: {item.source}</span> : null}
                {item.is_locked ? <span>Locked</span> : null}
                {item.is_equipped ? <span>Equipped</span> : null}
                {item.sheet_url ? <a href={item.sheet_url} target="_blank" rel="noopener noreferrer" style={{ fontSize:"12px" }}>📄 Item Docs</a> : null}
              </div>
            </div>
          ))}
        </div>
      </section>
    </RequireDiscord>
  );
}


// ====== SHOP HUB DASHBOARD (unified) ======

// ---- types ------------------------------------------------

interface Shop {
  shop_id: string;
  name: string;
  description?: string;
  owner_discord_id?: string;
  shop_type: "npc" | "player";
  status: string;
  is_active: boolean;
  image_url?: string;
  item_count: number;
}

interface ShopItem {
  item_id: string;
  shop_id: string;
  shop_name?: string;
  name: string;
  description?: string;
  category: string;
  price: number;
  stock?: number | null;
  currency_name?: string;
  currency_emoji?: string;
  currency_ticker?: string;
  requires_approval: boolean;
  is_active: boolean;
  image_url?: string;
}

interface Order {
  order_id: string;
  item_id?: string;
  item_name?: string;
  shop_name?: string;
  user_id?: string;
  buyer?: string;
  quantity: number;
  status: "pending" | "approved" | "denied" | "fulfilled";
  note?: string;
  created_at?: string;
}

type HubView = "browse" | "storefronts" | "manage" | "orders" | "create";

// ---- helpers ----------------------------------------------

function priceLabel(item: ShopItem) {
  const currency = item.currency_emoji || item.currency_ticker || item.currency_name || "";
  return `${item.price ?? 0}${currency ? ` ${currency}` : ""}`;
}

function stockLabel(item: ShopItem) {
  if (item.stock === null || item.stock === undefined) return "∞ stock";
  if (Number(item.stock) <= 0) return "Out of stock";
  return `${item.stock} in stock`;
}

function isOos(item: ShopItem) {
  return item.stock !== null && item.stock !== undefined && Number(item.stock) <= 0;
}

// ---- sub-components ----------------------------------------

function ItemImage({ url, alt, size = "card" }: { url?: string; alt: string; size?: "card" | "thumb" | "preview" }) {
  const [broken, setBroken] = useState(false);
  const heights: Record<string, string> = { card: "120px", thumb: "44px", preview: "56px" };
  const h = heights[size] || "120px";
  const w = size !== "card" ? h : "100%";

  if (!url || broken) {
    return (
      <div
        className="item-no-img"
        style={{
          width: w,
          height: h,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--color-background-tertiary)",
          borderRadius: size === "card" ? "0" : "var(--border-radius-md)",
          flexShrink: 0,
        }}
      >
        <Package size={size === "card" ? 32 : 18} style={{ opacity: 0.3 }} />
      </div>
    );
  }

  return (
    <img
      src={url}
      alt={alt}
      onError={() => setBroken(true)}
      style={{
        width: w,
        height: h,
        objectFit: "cover",
        display: "block",
        flexShrink: 0,
        borderRadius: size === "card" ? "0" : "var(--border-radius-md)",
      }}
    />
  );
}

function StoreBanner({ url, name }: { url?: string; name: string }) {
  const [broken, setBroken] = useState(false);
  return (
    <div
      style={{
        height: 72,
        background: "var(--color-background-tertiary)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {url && !broken ? (
        <img
          src={url}
          alt={name}
          onError={() => setBroken(true)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <Store size={30} style={{ opacity: 0.2 }} />
      )}
    </div>
  );
}

function ImagePreview({ url }: { url: string }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => { setBroken(false); }, [url]);
  return (
    <div
      style={{
        width: 56,
        height: 56,
        flexShrink: 0,
        borderRadius: "var(--border-radius-md)",
        overflow: "hidden",
        border: "0.5px solid var(--color-border-secondary)",
        background: "var(--color-background-tertiary)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {url && !broken ? (
        <img
          src={url}
          alt=""
          onError={() => setBroken(true)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <Package size={20} style={{ opacity: 0.25 }} />
      )}
    </div>
  );
}

function Badge({ label, variant = "default" }: { label: string; variant?: "default" | "success" | "danger" | "info" | "warn" | "muted" }) {
  const styles: Record<string, React.CSSProperties> = {
    default: { background: "var(--color-background-secondary)", color: "var(--color-text-secondary)" },
    success: { background: "var(--color-background-success)", color: "var(--color-text-success)" },
    danger: { background: "var(--color-background-danger)", color: "var(--color-text-danger)" },
    info: { background: "var(--color-background-info)", color: "var(--color-text-info)" },
    warn: { background: "var(--color-background-warning)", color: "var(--color-text-warning)" },
    muted: { background: "var(--color-background-secondary)", color: "var(--color-text-secondary)", border: "0.5px solid var(--color-border-secondary)" },
  };
  return (
    <span
      style={{
        fontSize: 11,
        padding: "2px 8px",
        borderRadius: 20,
        display: "inline-block",
        ...styles[variant],
      }}
    >
      {label}
    </span>
  );
}

function FlashMsg({ text, type }: { text: string; type: "ok" | "err" }) {
  if (!text) return null;
  return (
    <p
      style={{
        fontSize: 13,
        padding: "8px 12px",
        borderRadius: "var(--border-radius-md)",
        marginBottom: 10,
        background: type === "ok" ? "var(--color-background-success)" : "var(--color-background-danger)",
        color: type === "ok" ? "var(--color-text-success)" : "var(--color-text-danger)",
        border: `0.5px solid ${type === "ok" ? "var(--color-border-success)" : "var(--color-border-danger)"}`,
      }}
    >
      {text}
    </p>
  );
}

// ---- BROWSE VIEW ------------------------------------------

function BrowseView({
  discordId,
  selectedCharacterId,
  shops,
}: {
  discordId: string;
  selectedCharacterId?: string;
  shops: Shop[];
}) {
  const [items, setItems] = useState<ShopItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [summary, setSummary] = useState({ shops: 0, items: 0, approval_required: 0, out_of_stock: 0 });
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [shopFilter, setShopFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});

  async function load() {
    if (!discordId) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ category: categoryFilter, shop_id: shopFilter });
      if (search.trim()) params.set("search", search.trim());
      const data = await apiFetch(`/api/market/overview?${params}`, {}, discordId);
      setItems(data.items || []);
      setCategories(data.categories || []);
      setSummary(data.summary || {});
    } catch (e: any) {
      setMsg({ text: e.message || "Could not load market.", type: "err" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [discordId, categoryFilter, shopFilter]);

  async function buyItem(item: ShopItem) {
    const qty = quantities[item.item_id] || 1;
    if (!selectedCharacterId) {
      setMsg({ text: "No character selected — go to the OC tab and select your active character first.", type: "err" });
      return;
    }
    try {
      const result = await apiFetch(
        `/api/market/items/${item.item_id}/request`,
        {
          method: "POST",
          body: JSON.stringify({
            quantity: qty,
            character_id: selectedCharacterId,
            note: notes[item.item_id] || "",
          }),
        },
        discordId
      );
      setMsg({ text: result.message || "Request submitted.", type: "ok" });
      load();
    } catch (e: any) {
      setMsg({ text: e.message || "Could not submit request.", type: "err" });
    }
  }

  return (
    <div>
      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 10, marginBottom: "1.5rem" }}>
        {[
          { label: "Open shops", value: summary.shops },
          { label: "Items listed", value: summary.items },
          { label: "Needs approval", value: summary.approval_required },
          { label: "Out of stock", value: summary.out_of_stock },
        ].map(({ label, value }) => (
          <div key={label} className="card" style={{ padding: "12px 14px" }}>
            <p className="muted-text" style={{ fontSize: 12, marginBottom: 4 }}>{label}</p>
            <strong style={{ fontSize: 22 }}>{value ?? 0}</strong>
          </div>
        ))}
      </div>

      {/* Character indicator */}
      {!selectedCharacterId && (
        <div style={{ fontSize: 13, padding: "8px 12px", borderRadius: "var(--border-radius-md)", marginBottom: 12,
          background: "var(--color-background-warning)", color: "var(--color-text-warning)",
          border: "0.5px solid var(--color-border-warning)" }}>
          ⚠️ No character selected — go to the <strong>OC</strong> tab and select your active character before buying.
        </div>
      )}

      {/* Filters */}
      <div className="card" style={{ padding: 14, marginBottom: "1rem", display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 180 }}>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Search</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Items, shops, categories..."
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 130 }}>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Shop</span>
          <select value={shopFilter} onChange={(e) => setShopFilter(e.target.value)}>
            <option value="all">All shops</option>
            {shops.filter((s) => s.is_active).map((s) => (
              <option key={s.shop_id} value={s.shop_id}>{s.name}</option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 130 }}>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Category</span>
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="all">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <button className="ghost" onClick={load} disabled={loading}>
          <RefreshCw size={14} /> {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <FlashMsg text={msg.text} type={msg.type} />

      {/* Item grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
        {items.length === 0 && !loading && (
          <div className="card" style={{ gridColumn: "1/-1", textAlign: "center", padding: "2.5rem 1rem", color: "var(--color-text-secondary)" }}>
            <Package size={36} style={{ marginBottom: 8, opacity: 0.3 }} />
            <p>No items match your filters.</p>
          </div>
        )}
        {items.map((item) => {
          const oos = isOos(item);
          return (
            <div key={item.item_id} className="card" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
              <ItemImage url={item.image_url} alt={item.name} size="card" />
              <div style={{ padding: "12px 12px 0", flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                  <div>
                    <p style={{ fontWeight: 500, fontSize: 14, lineHeight: 1.3 }}>{item.name}</p>
                    <p className="muted-text" style={{ fontSize: 11 }}>{item.shop_name}</p>
                  </div>
                  <strong style={{ fontSize: 15, color: "var(--color-text-info)", whiteSpace: "nowrap" }}>{priceLabel(item)}</strong>
                </div>
                {item.description && <p className="muted-text" style={{ fontSize: 12, lineHeight: 1.5 }}>{item.description}</p>}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  <Badge label={item.category || "General"} variant="info" />
                  <Badge label={stockLabel(item)} variant={oos ? "danger" : "default"} />
                  {item.requires_approval && <Badge label="Approval required" variant="warn" />}
                </div>
              </div>
              <div style={{ padding: "10px 12px 12px", display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  type="number"
                  min={1}
                  value={quantities[item.item_id] || 1}
                  onChange={(e) => setQuantities((q) => ({ ...q, [item.item_id]: Math.max(1, Number(e.target.value)) }))}
                  style={{ width: 58, fontSize: 13, padding: "5px 8px" }}
                  aria-label="Quantity"
                />
                <button
                  style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                  onClick={() => buyItem(item)}
                  disabled={oos || !item.item_id}
                >
                  <ShoppingCart size={14} />
                  {item.requires_approval ? "Request" : "Buy"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---- STOREFRONTS VIEW -------------------------------------

function StorefrontsView({ shops, discordId, selectedCharacterId }: { shops: Shop[]; discordId: string; selectedCharacterId?: string }) {
  const [storeFilter, setStoreFilter] = useState<"all" | "npc" | "player">("all");
  const [selectedShop, setSelectedShop] = useState<Shop | null>(null);
  const [shopItems, setShopItems] = useState<ShopItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [msg, setMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const detailRef = useRef<HTMLDivElement>(null);

  const filtered = shops.filter((s) => storeFilter === "all" || s.shop_type === storeFilter);

  async function openShop(shop: Shop) {
    setSelectedShop(shop);
    setLoadingItems(true);
    try {
      const data = await apiFetch(`/api/market/overview?shop_id=${shop.shop_id}`, {}, discordId);
      setShopItems(data.items || []);
    } catch {
      setShopItems([]);
    } finally {
      setLoadingItems(false);
      setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 100);
    }
  }

  async function buyFromStore(item: ShopItem) {
    const qty = quantities[item.item_id] || 1;
    if (!selectedCharacterId) {
      setMsg({ text: "No character selected — go to the OC tab and select your active character first.", type: "err" });
      return;
    }
    try {
      const result = await apiFetch(
        `/api/market/items/${item.item_id}/request`,
        { method: "POST", body: JSON.stringify({ quantity: qty, character_id: selectedCharacterId }) },
        discordId
      );
      setMsg({ text: result.message || "Done.", type: "ok" });
    } catch (e: any) {
      setMsg({ text: e.message || "Error.", type: "err" });
    }
  }

  return (
    <div>
      {/* Filter buttons */}
      <div style={{ display: "flex", gap: 8, marginBottom: "1rem" }}>
        {(["all", "npc", "player"] as const).map((f) => (
          <button key={f} className={storeFilter === f ? "" : "ghost"} onClick={() => setStoreFilter(f)} style={{ fontSize: 13 }}>
            {f === "all" ? "All" : f === "npc" ? "NPC shops" : "Player shops"}
          </button>
        ))}
      </div>

      {/* Store cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 12, marginBottom: "1.5rem" }}>
        {filtered.map((shop) => (
          <div
            key={shop.shop_id}
            className="card"
            onClick={() => openShop(shop)}
            style={{
              padding: 0,
              overflow: "hidden",
              cursor: "pointer",
              border: selectedShop?.shop_id === shop.shop_id ? "1.5px solid var(--color-border-info)" : undefined,
              transition: "border-color 0.15s",
            }}
          >
            <StoreBanner url={shop.image_url} name={shop.name} />
            <div style={{ padding: "10px 12px" }}>
              <p style={{ fontWeight: 500, fontSize: 14, marginBottom: 2 }}>{shop.name}</p>
              <p className="muted-text" style={{ fontSize: 12 }}>{shop.item_count} items</p>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 6 }}>
                <Badge label={shop.status} variant={shop.is_active ? "success" : "danger"} />
                <Badge label={shop.shop_type === "npc" ? "NPC" : "Player"} variant="muted" />
              </div>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="muted-text" style={{ fontSize: 13, gridColumn: "1/-1" }}>No shops of this type found.</p>
        )}
      </div>

      {/* Selected shop detail */}
      {selectedShop && (
        <div ref={detailRef}>
          <hr style={{ borderColor: "var(--color-border-tertiary)", margin: "0 0 1rem" }} />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem", flexWrap: "wrap", gap: 8 }}>
            <div>
              <h3>{selectedShop.name}</h3>
              {selectedShop.description && <p className="muted-text" style={{ fontSize: 13 }}>{selectedShop.description}</p>}
            </div>
            <button className="ghost" onClick={() => setSelectedShop(null)} style={{ fontSize: 13 }}>
              <X size={14} /> Close
            </button>
          </div>
          <FlashMsg text={msg.text} type={msg.type} />
          {loadingItems ? (
            <p className="muted-text" style={{ fontSize: 13 }}>Loading items...</p>
          ) : shopItems.length === 0 ? (
            <p className="muted-text" style={{ fontSize: 13 }}>No items listed in this shop.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
              {shopItems.map((item) => {
                const oos = isOos(item);
                return (
                  <div key={item.item_id} className="card" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
                    <ItemImage url={item.image_url} alt={item.name} size="card" />
                    <div style={{ padding: "12px 12px 0", flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                        <p style={{ fontWeight: 500, fontSize: 14 }}>{item.name}</p>
                        <strong style={{ color: "var(--color-text-info)", fontSize: 15, whiteSpace: "nowrap" }}>{priceLabel(item)}</strong>
                      </div>
                      {item.description && <p className="muted-text" style={{ fontSize: 12 }}>{item.description}</p>}
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        <Badge label={item.category} variant="info" />
                        <Badge label={stockLabel(item)} variant={oos ? "danger" : "default"} />
                        {item.requires_approval && <Badge label="Approval required" variant="warn" />}
                      </div>
                    </div>
                    <div style={{ padding: "10px 12px 12px", display: "flex", gap: 6 }}>
                      <input
                        type="number"
                        min={1}
                        value={quantities[item.item_id] || 1}
                        onChange={(e) => setQuantities((q) => ({ ...q, [item.item_id]: Math.max(1, Number(e.target.value)) }))}
                        style={{ width: 58, fontSize: 13, padding: "5px 8px" }}
                      />
                      <button style={{ flex: 1 }} onClick={() => buyFromStore(item)} disabled={oos}>
                        <ShoppingCart size={13} /> {item.requires_approval ? "Request" : "Buy"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---- MANAGE VIEW ------------------------------------------

function ManageView({ discordId, isStaff }: { discordId: string; isStaff: boolean }) {
  const [shops, setShops] = useState<Shop[]>([]);
  const [selectedShopId, setSelectedShopId] = useState("");
  const [shopData, setShopData] = useState<{ shop: Shop | null; items: ShopItem[] }>({ shop: null, items: [] });
  const [shopForm, setShopForm] = useState({ name: "", description: "", image_url: "", status: "Open" });
  const [shopMsg, setShopMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [saving, setSaving] = useState(false);

  // item form
  const [showItemForm, setShowItemForm] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [itemMsg, setItemMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [itemForm, setItemForm] = useState({
    name: "",
    description: "",
    category: "General",
    price: "0",
    stock: "",
    cc: "0",
    image_url: "",
    requires_approval: false,
    is_active: true,
    item_type: "item",
  });

  async function loadMyShops() {
    if (!discordId) return;
    try {
      const data = await apiFetch("/api/shop-owner/shops", {}, discordId);
      const rows: Shop[] = data.shops || [];
      setShops(rows);
      if (!selectedShopId && rows.length > 0) setSelectedShopId(rows[0].shop_id);
    } catch {
      setShops([]);
    }
  }

  async function loadShop(sid = selectedShopId) {
    if (!discordId || !sid) return;
    try {
      const data = await apiFetch(`/api/shop-owner/shops/${sid}`, {}, discordId);
      setShopData({ shop: data.shop || null, items: data.items || [] });
      const s = data.shop || {};
      setShopForm({
        name: s.name || "",
        description: s.description || "",
        image_url: s.image_url || "",
        status: s.status || "Open",
      });
    } catch {
      setShopData({ shop: null, items: [] });
    }
  }

  useEffect(() => { loadMyShops(); }, [discordId]);
  useEffect(() => { if (selectedShopId) loadShop(selectedShopId); }, [selectedShopId]);

  async function saveShop() {
    setSaving(true);
    setShopMsg({ text: "", type: "ok" });
    try {
      const data = await apiFetch(
        `/api/market/shops/${selectedShopId}`,
        { method: "PATCH", body: JSON.stringify(shopForm) },
        discordId
      );
      setShopMsg({ text: data.message || "Saved.", type: "ok" });
      await loadMyShops();
      await loadShop(selectedShopId);
    } catch (e: any) {
      setShopMsg({ text: e.message || "Could not save.", type: "err" });
    } finally {
      setSaving(false);
    }
  }

  function openAddItem() {
    setEditingItemId(null);
    setItemForm({ name: "", description: "", category: "General", price: "0", stock: "", cc: "0", image_url: "", requires_approval: false, is_active: true, item_type: "item" });
    setShowItemForm(true);
    setItemMsg({ text: "", type: "ok" });
  }

  function openEditItem(item: ShopItem) {
    setEditingItemId(item.item_id);
    setItemForm({
      name: item.name,
      description: item.description || "",
      category: item.category || "General",
      price: String(item.price ?? 0),
      stock: item.stock !== null && item.stock !== undefined ? String(item.stock) : "",
      cc: String((item as any).cc || (item as any).wu || 0),
      image_url: item.image_url || "",
      requires_approval: item.requires_approval,
      is_active: item.is_active !== false,
      item_type: "item",
    });
    setShowItemForm(true);
    setItemMsg({ text: "", type: "ok" });
  }

  async function saveItem() {
    if (!itemForm.name.trim()) { setItemMsg({ text: "Item name is required.", type: "err" }); return; }
    const payload: Record<string, any> = {
      name: itemForm.name.trim(),
      description: itemForm.description.trim(),
      category: itemForm.category,
      price: parseInt(itemForm.price) || 0,
      stock: (itemForm.stock === "" || itemForm.stock === null) ? null : (isNaN(parseInt(itemForm.stock)) ? null : parseInt(itemForm.stock)),
      cc: parseInt(itemForm.cc || "0") || 0,
      image_url: itemForm.image_url.trim() || null,
      requires_approval: itemForm.requires_approval,
      is_active: itemForm.is_active,
      item_type: itemForm.item_type,
    };
    try {
      if (editingItemId) {
        const data = await apiFetch(`/api/shop-owner/items/${editingItemId}`, { method: "PATCH", body: JSON.stringify(payload) }, discordId);
        setItemMsg({ text: data.message || "Item updated.", type: "ok" });
      } else {
        const data = await apiFetch(`/api/shop-owner/shops/${selectedShopId}/items`, { method: "POST", body: JSON.stringify(payload) }, discordId);
        setItemMsg({ text: data.message || "Item created.", type: "ok" });
      }
      await loadShop(selectedShopId);
      setShowItemForm(false);
    } catch (e: any) {
      setItemMsg({ text: e.message || "Could not save item.", type: "err" });
    }
  }

  async function deleteItem() {
    if (!editingItemId) return;
    const item = shopData.items.find((i) => i.item_id === editingItemId);
    if (!window.confirm(`Delete "${item?.name || "this item"}" permanently?`)) return;
    try {
      const result = await apiFetch(`/api/shop-owner/items/${editingItemId}`, { method: "DELETE" }, discordId);
      setShowItemForm(false);
      if (result.soft_deleted) {
        setShopMsg({ text: result.message, type: "ok" });
      }
      await loadShop(selectedShopId);
    } catch (e: any) {
      setItemMsg({ text: e.message || "Could not delete.", type: "err" });
    }
  }

  async function forceDeleteItem(item: ShopItem) {
    if (!window.confirm(`Force delete "${item.name}"? This will permanently remove it and all its order history. This cannot be undone.`)) return;
    try {
      await apiFetch(`/api/shop-owner/items/${item.item_id}/force-delete`, { method: "DELETE" }, discordId);
      await loadShop(selectedShopId);
      setShopMsg({ text: `"${item.name}" permanently deleted.`, type: "ok" });
    } catch (e: any) {
      setShopMsg({ text: e.message || "Could not force delete.", type: "err" });
    }
  }

  async function toggleItem(item: ShopItem) {
    try {
      await apiFetch(`/api/shop-owner/items/${item.item_id}/toggle`, { method: "POST" }, discordId);
      await loadShop(selectedShopId);
    } catch { /* silent */ }
  }

  return (
    <div>
      {/* Shop selector */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <span className="muted-text" style={{ fontSize: 13 }}>Your shop:</span>
        <select value={selectedShopId} onChange={(e) => setSelectedShopId(e.target.value)} style={{ flex: 1, minWidth: 160 }}>
          <option value="">Select a shop...</option>
          {shops.map((s) => <option key={s.shop_id} value={s.shop_id}>{s.name}</option>)}
        </select>
      </div>

      {!selectedShopId ? (
        <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-secondary)" }}>
          <Store size={36} style={{ marginBottom: 8, opacity: 0.25 }} />
          <p style={{ fontSize: 13 }}>Select a shop to manage it, or create a new one from the Create tab.</p>
        </div>
      ) : (
        <>
          {/* Shop settings */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: 15, fontWeight: 500, marginBottom: 14 }}>Shop settings</h3>
            <FlashMsg text={shopMsg.text} type={shopMsg.type} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Shop name</span>
                <input value={shopForm.name} onChange={(e) => setShopForm((f) => ({ ...f, name: e.target.value }))} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Status</span>
                <select value={shopForm.status} onChange={(e) => setShopForm((f) => ({ ...f, status: e.target.value }))}>
                  <option>Open</option>
                  <option>Closed</option>
                  <option>Coming Soon</option>
                </select>
              </label>
            </div>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Description</span>
              <textarea value={shopForm.description} onChange={(e) => setShopForm((f) => ({ ...f, description: e.target.value }))} style={{ minHeight: 60, resize: "vertical" }} />
            </label>
            <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Banner / logo URL</span>
                <input
                  value={shopForm.image_url}
                  onChange={(e) => setShopForm((f) => ({ ...f, image_url: e.target.value }))}
                  placeholder="https://..."
                />
                <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>PNG, JPG, GIF, WebP — paste any image URL</span>
              </label>
              <ImagePreview url={shopForm.image_url} />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
              <button onClick={saveShop} disabled={saving}>
                <Save size={14} /> {saving ? "Saving..." : "Save settings"}
              </button>
            </div>
          </div>

          {/* Items list */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
            <h3 style={{ fontSize: 15, fontWeight: 500 }}>Items ({shopData.items.filter(i => i.is_active || showArchived).length})</h3>
            <div style={{ display: "flex", gap: 6 }}>
              {shopData.items.some(i => !i.is_active) && (
                <button className="ghost" onClick={() => setShowArchived(a => !a)} style={{ fontSize: 12 }}>
                  <Eye size={12} /> {showArchived ? "Hide archived" : `Show archived (${shopData.items.filter(i => !i.is_active).length})`}
                </button>
              )}
              <button onClick={openAddItem}>
                <Plus size={14} /> Add item
              </button>
            </div>
          </div>

          {shopData.items.filter(i => showArchived || i.is_active).length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: "1.5rem", color: "var(--color-text-secondary)" }}>
              <Package size={28} style={{ marginBottom: 6, opacity: 0.25 }} />
              <p style={{ fontSize: 13 }}>No items yet — add your first one above.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {shopData.items.filter(i => showArchived || i.is_active).map((item) => (
                <div key={item.item_id} className="card" style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 12px" }}>
                  <ItemImage url={item.image_url} alt={item.name} size="thumb" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontWeight: 500, fontSize: 13 }}>{item.name}</p>
                    <p className="muted-text" style={{ fontSize: 12 }}>
                      {item.category} · {priceLabel(item)} · {stockLabel(item)}{item.requires_approval ? " · Approval req." : ""}{!item.is_active ? " · Hidden" : ""}
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                    <button className="ghost" onClick={() => openEditItem(item)} style={{ padding: "4px 8px" }} title="Edit">
                      <Edit size={13} />
                    </button>
                    <button className="ghost" onClick={() => toggleItem(item)} style={{ padding: "4px 8px" }} title={item.is_active ? "Hide" : "Show"}>
                      {item.is_active ? <EyeOff size={13} /> : <Eye size={13} />}
                    </button>
                    {!item.is_active && isStaff && (
                      <button
                        className="ghost"
                        onClick={() => forceDeleteItem(item)}
                        style={{ padding: "4px 8px", color: "var(--color-text-danger)" }}
                        title="Force delete (staff only — removes order history)"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Item form */}
          {showItemForm && (
            <div className="card" style={{ marginTop: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 500, marginBottom: 14 }}>
                {editingItemId ? "Edit item" : "Add item"}
              </h3>
              <FlashMsg text={itemMsg.text} type={itemMsg.type} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Item name *</span>
                  <input value={itemForm.name} onChange={(e) => setItemForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. Iron Sword" />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Category</span>
                  <select value={itemForm.category} onChange={(e) => setItemForm((f) => ({ ...f, category: e.target.value }))}>
                    {["General", "Weapon", "Armor", "Consumable", "Material", "Misc", "Service", "Role"].map((c) => <option key={c}>{c}</option>)}
                  </select>
                </label>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Price *</span>
                  <input type="number" min={0} value={itemForm.price} onChange={(e) => setItemForm((f) => ({ ...f, price: e.target.value }))} />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Stock (blank = unlimited)</span>
                  <input type="text" inputMode="numeric" value={itemForm.stock} onChange={(e) => {
                    const v = e.target.value.replace(/[^0-9]/g, "");
                    setItemForm((f) => ({ ...f, stock: v }));
                  }} placeholder="∞ (leave blank for unlimited)" style={{ width: "100%" }} />
                </label>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>CC (Carry Capacity cost)</span>
                  <input type="text" inputMode="numeric" value={itemForm.cc} onChange={(e) => {
                    const v = e.target.value.replace(/[^0-9]/g, "");
                    setItemForm((f) => ({ ...f, cc: v || "0" }));
                  }} placeholder="0" />
                  <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>0 = free (trinkets, flavor items). Worn armor CC is ignored.</span>
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Item type</span>
                  <select value={itemForm.item_type || "item"} onChange={(e) => setItemForm((f) => ({ ...f, item_type: e.target.value }))}>
                    <option value="item">Item</option>
                    <option value="consumable">Consumable</option>
                    <option value="material">Material</option>
                  </select>
                </label>
              </div>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Description</span>
                <textarea value={itemForm.description} onChange={(e) => setItemForm((f) => ({ ...f, description: e.target.value }))} style={{ minHeight: 60, resize: "vertical" }} />
              </label>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginBottom: 10 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Item image URL</span>
                  <input value={itemForm.image_url} onChange={(e) => setItemForm((f) => ({ ...f, image_url: e.target.value }))} placeholder="https://..." />
                  <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>Shows on item card in the market</span>
                </label>
                <ImagePreview url={itemForm.image_url} />
              </div>
              <div style={{ display: "flex", gap: 20, marginBottom: 14 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                  <input type="checkbox" checked={itemForm.requires_approval} onChange={(e) => setItemForm((f) => ({ ...f, requires_approval: e.target.checked }))} style={{ width: "auto" }} />
                  Requires approval
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                  <input type="checkbox" checked={itemForm.is_active} onChange={(e) => setItemForm((f) => ({ ...f, is_active: e.target.checked }))} style={{ width: "auto" }} />
                  Visible / purchasable
                </label>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={saveItem}><Check size={14} /> Save item</button>
                <button className="ghost" onClick={() => setShowItemForm(false)}><X size={14} /> Cancel</button>
                {editingItemId && (
                  <button className="ghost" onClick={deleteItem} style={{ marginLeft: "auto", color: "var(--color-text-danger)" }}>
                    <Trash2 size={14} /> Delete
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---- ORDERS VIEW ------------------------------------------

function OrdersView({ discordId, isStaff }: { discordId: string; isStaff: boolean }) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [role, setRole] = useState<"buyer" | "seller" | "staff">("buyer");
  const [msg, setMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [working, setWorking] = useState("");

  async function load() {
    if (!discordId) return;
    try {
      let endpoint = "";
      if (role === "buyer") {
        endpoint = `/api/market/orders?status=${statusFilter}`;
      } else if (role === "seller") {
        const shopsData = await apiFetch("/api/shop-owner/shops", {}, discordId);
        const firstShop = (shopsData.shops || [])[0];
        endpoint = firstShop
          ? `/api/shop-owner/shops/${firstShop.shop_id}/orders?status=${statusFilter}`
          : `/api/market/orders?status=${statusFilter}`;
      } else {
        endpoint = `/api/market/orders?status=${statusFilter}`;
      }
      const data = await apiFetch(endpoint, {}, discordId);
      setOrders(data.orders || []);
    } catch {
      setOrders([]);
    }
  }

  useEffect(() => { load(); }, [discordId, statusFilter, role]);

  async function act(order: Order, action: "approve" | "deny" | "fulfill") {
    let reason = "";
    if (action === "deny") {
      reason = window.prompt("Reason for denial (required):") || "";
      if (!reason.trim()) return;
    }
    setWorking(order.order_id);
    try {
      const body = action === "deny" ? { reason } : {};
      const data = await apiFetch(
        `/api/shop-owner/orders/${order.order_id}/${action}`,
        { method: "POST", body: JSON.stringify(body) },
        discordId
      );
      setMsg({ text: data.message || "Updated.", type: "ok" });
      load();
    } catch (e: any) {
      setMsg({ text: e.message || "Error.", type: "err" });
    } finally {
      setWorking("");
    }
  }

  const statusVariant: Record<string, "default" | "warn" | "success" | "danger" | "info" | "muted"> = {
    pending: "warn",
    paid: "warn",
    approved: "success",
    denied: "danger",
    fulfilled: "info",
  };

  return (
    <div>
      <div className="card" style={{ padding: 14, marginBottom: "1rem", display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
        {isStaff && (
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>View as</span>
            <select value={role} onChange={(e) => setRole(e.target.value as any)}>
              <option value="buyer">My orders (buyer)</option>
              <option value="seller">My shop orders (seller)</option>
              <option value="staff">All orders (staff)</option>
            </select>
          </label>
        )}
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Status</span>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="pending">Pending / Awaiting Approval</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="fulfilled">Fulfilled</option>
            <option value="all">All</option>
          </select>
        </label>
        <button className="ghost" onClick={load}><RefreshCw size={14} /> Refresh</button>
      </div>

      <FlashMsg text={msg.text} type={msg.type} />

      {orders.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--color-text-secondary)" }}>
          <Package size={28} style={{ opacity: 0.25, marginBottom: 6 }} />
          <p style={{ fontSize: 13 }}>No orders match this filter.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {orders.map((order) => (
            <div key={order.order_id} className="card" style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 14px", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 500, fontSize: 13 }}>{order.item_name || "Item"}</p>
                <p className="muted-text" style={{ fontSize: 12 }}>
                  {order.shop_name || ""}{order.shop_name && " · "}
                  Qty: {order.quantity}{order.note ? ` · "${order.note}"` : ""}
                </p>
              </div>
              <Badge label={order.status} variant={statusVariant[order.status] || "default"} />
              <div style={{ display: "flex", gap: 4 }}>
                {(order.status === "pending" || order.status === "PENDING" || order.status === "PAID" || order.status === "paid") && (
                  <>
                    <button
                      className="ghost"
                      onClick={() => act(order, "approve")}
                      disabled={working === order.order_id}
                      style={{ padding: "4px 10px", color: "var(--color-text-success)" }}
                    >
                      <Check size={13} /> Approve
                    </button>
                    <button
                      className="ghost"
                      onClick={() => act(order, "deny")}
                      disabled={working === order.order_id}
                      style={{ padding: "4px 10px", color: "var(--color-text-danger)" }}
                    >
                      <X size={13} /> Deny
                    </button>
                  </>
                )}
                {(order.status === "approved" || order.status === "APPROVED") && (
                  <button
                    className="ghost"
                    onClick={() => act(order, "fulfill")}
                    disabled={working === order.order_id}
                    style={{ padding: "4px 10px" }}
                  >
                    <Package size={13} /> Fulfill
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- CREATE VIEW ------------------------------------------

function CreateView({ discordId, isStaff, onCreated }: { discordId: string; isStaff: boolean; onCreated: () => void }) {
  const [form, setForm] = useState({ name: "", description: "", image_url: "", shop_type: "player" });
  const [msg, setMsg] = useState({ text: "", type: "ok" as "ok" | "err" });
  const [saving, setSaving] = useState(false);

  async function create() {
    if (!form.name.trim()) { setMsg({ text: "Shop name is required.", type: "err" }); return; }
    setSaving(true);
    try {
      let endpoint = "/api/shop-owner/shops";
      const payload: Record<string, any> = { name: form.name.trim(), description: form.description.trim(), image_url: form.image_url.trim() || null };

      if (form.shop_type === "npc") {
        // Staff-only NPC shop endpoint
        endpoint = "/api/market/shops";
      }

      const data = await apiFetch(endpoint, { method: "POST", body: JSON.stringify(payload) }, discordId);
      setMsg({ text: data.message || "Shop created!", type: "ok" });
      setForm({ name: "", description: "", image_url: "", shop_type: "player" });
      setTimeout(() => onCreated(), 1200);
    } catch (e: any) {
      setMsg({ text: e.message || "Could not create shop.", type: "err" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 500, marginBottom: 14 }}>Create storefront</h3>
        <FlashMsg text={msg.text} type={msg.type} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Shop name *</span>
            <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. The Wanderer's Goods" />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Type</span>
            <select value={form.shop_type} onChange={(e) => setForm((f) => ({ ...f, shop_type: e.target.value }))} disabled={!isStaff}>
              <option value="player">Player-owned shop</option>
              {isStaff && <option value="npc">NPC shop (staff-run)</option>}
            </select>
          </label>
        </div>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Description</span>
          <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="What does this shop sell?" style={{ minHeight: 60, resize: "vertical" }} />
        </label>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Shop banner URL</span>
            <input value={form.image_url} onChange={(e) => setForm((f) => ({ ...f, image_url: e.target.value }))} placeholder="https://..." />
            <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>Appears on the storefront card</span>
          </label>
          <ImagePreview url={form.image_url} />
        </div>
        <button style={{ marginTop: 14 }} onClick={create} disabled={saving}>
          <Plus size={14} /> {saving ? "Creating..." : "Create shop"}
        </button>
      </div>

      {isStaff && (
        <div
          className="card"
          style={{
            marginTop: 12,
            background: "var(--color-background-secondary)",
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
            padding: "12px 14px",
            fontSize: 13,
            color: "var(--color-text-secondary)",
          }}
        >
          <ShieldCheck size={16} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>Staff can create NPC shops — they have no owner and are managed through the Manage Shop tab. Player shops are tied to the logged-in Discord account.</span>
        </div>
      )}
    </div>
  );
}

// ---- ROOT COMPONENT ---------------------------------------

export function ShopHubDashboard({
  discordId,
  selectedCharacterId,
  initialView = "browse",
}: {
  discordId: string;
  selectedCharacterId?: string;
  initialView?: HubView;
}) {
  const [view, setView] = useState<HubView>(initialView);
  const [shops, setShops] = useState<Shop[]>([]);
  const [isStaff, setIsStaff] = useState(false);
  const permissions = usePermissions(discordId);

  async function loadShops() {
    if (!discordId) return;
    try {
      const data = await apiFetch("/api/market/overview?active_only=false", {}, discordId);
      setShops(data.shops || []);
      setIsStaff(data.is_staff || false);
    } catch { /* silent */ }
  }

  useEffect(() => { loadShops(); }, [discordId]);
  useEffect(() => { setView(initialView); }, [initialView]);

  const canManage = isStaff || permissions?.is_shop_owner;
  const tabs: { key: HubView; label: string }[] = [
    { key: "browse", label: "Browse" },
    { key: "storefronts", label: "Storefronts" },
    ...(canManage ? [{ key: "manage" as HubView, label: "Manage Shop" }] : []),
    { key: "orders", label: "Orders" },
    ...(canManage ? [{ key: "create" as HubView, label: "Create" }] : []),
  ];

  return (
    <section>
      {/* Header */}
      <div className="card market-hero" style={{ marginBottom: "1rem" }}>
        <div>
          <span className="activity-type-label">Market District</span>
          <h2>Shop Hub</h2>
          <p className="muted-text">Browse storefronts, manage your shop, and process orders — all in one place.</p>
        </div>
        <button className="ghost" onClick={loadShops}><RefreshCw size={16} /></button>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 4, borderBottom: "0.5px solid var(--color-border-tertiary)", marginBottom: "1.5rem", overflowX: "auto" }}>
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            className="ghost"
            onClick={() => setView(key)}
            style={{
              fontSize: 14,
              padding: "8px 16px",
              borderRadius: 0,
              borderBottom: view === key ? "2px solid var(--color-text-primary)" : "2px solid transparent",
              color: view === key ? "var(--color-text-primary)" : "var(--color-text-secondary)",
              whiteSpace: "nowrap",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Views */}
      {view === "browse" && <BrowseView discordId={discordId} selectedCharacterId={selectedCharacterId} shops={shops} />}
      {view === "storefronts" && <StorefrontsView shops={shops} discordId={discordId} selectedCharacterId={selectedCharacterId} />}
      {view === "manage" && <ManageView discordId={discordId} isStaff={isStaff} />}
      {view === "orders" && <OrdersView discordId={discordId} isStaff={isStaff} />}
      {view === "create" && <CreateView discordId={discordId} isStaff={isStaff} onCreated={() => { loadShops(); setView("manage"); }} />}
    </section>
  );
}

// Keep these as thin aliases so any leftover references in main.tsx don't break
export function ShopDashboard({ discordId, selectedCharacterId }: { discordId: string; selectedCharacterId?: string }) {
  return <ShopHubDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} initialView="browse" />;
}

export function ShopOwnerDashboard({ discordId }: { discordId: string }) {
  return <ShopHubDashboard discordId={discordId} initialView="manage" />;
}

// ====== END SHOP HUB DASHBOARD ======

function SkillsDashboard({ discordId, selectedCharacterId, setSelectedCharacterId }: { discordId: string; selectedCharacterId: string; setSelectedCharacterId: (id: string) => void }) {
  const [skills, setSkills] = useState<any[]>([]);
  const [ownedKeys, setOwnedKeys] = useState<string[]>([]);
  const [pendingKeys, setPendingKeys] = useState<string[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [wallet, setWallet] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [treeFilter, setTreeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchText, setSearchText] = useState("");
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});

  async function load() {
    setMessage("");

    const catalog = await apiFetch("/api/skills", {}, discordId);
    setSkills(catalog.skills || []);

    if (selectedCharacterId) {
      const mine = await apiFetch(`/api/characters/${selectedCharacterId}/skills`, {}, discordId);
      setOwnedKeys(mine.owned_keys || []);
      setPendingKeys(mine.pending_keys || []);
      setRequests(mine.requests || []);
      setWallet(mine.wallet);
    } else {
      setOwnedKeys([]);
      setPendingKeys([]);
      setRequests([]);
      setWallet(null);
    }
  }

  useEffect(() => {
    if (discordId) {
      load().catch((error) => setMessage(error.message));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, selectedCharacterId]);

  const trees = useMemo(
    () => ["all", ...Array.from(new Set(skills.map((skill) => String(skill.tree || "General")))).sort()],
    [skills]
  );

  function parsePrereqKeys(skill: any): string[] {
    const prereq = skill.prerequisites;

    if (!prereq) return [];

    if (Array.isArray(prereq)) {
      return prereq
        .map((item) => {
          if (typeof item === "string") return item;
          return item?.skill_key || item?.skill || item?.key || item?.prereq_key || "";
        })
        .filter(Boolean);
    }

    if (typeof prereq === "object") {
      const raw =
        prereq.skills ||
        prereq.skill_keys ||
        prereq.requires ||
        prereq.prerequisites ||
        prereq.required_skills ||
        [];

      if (Array.isArray(raw)) {
        return raw
          .map((item) => {
            if (typeof item === "string") return item;
            return item?.skill_key || item?.skill || item?.key || item?.prereq_key || "";
          })
          .filter(Boolean);
      }

      if (typeof raw === "string") return [raw];
    }

    return [];
  }

  function prereqSummary(skill: any) {
    const keys = parsePrereqKeys(skill);

    if (keys.length === 0) return "None";

    return keys
      .map((key) => skills.find((skillDef) => skillDef.skill_key === key)?.name || key)
      .join(", ");
  }

  function missingPrereqs(skill: any) {
    return parsePrereqKeys(skill).filter((key) => !ownedKeys.includes(key));
  }

  function skillState(skill: any) {
    const owned = ownedKeys.includes(skill.skill_key);
    const pending = pendingKeys.includes(skill.skill_key);
    const missing = missingPrereqs(skill);
    const availableXp = Number(wallet?.available_xp ?? 0);
    const cost = Number(skill.cost ?? 0);
    const affordable = availableXp >= cost;

    if (owned) return { label: "Owned", className: "good", requestable: false };
    if (pending) return { label: "Pending", className: "", requestable: false };
    if (missing.length > 0) return { label: "Locked", className: "bad", requestable: false };
    if (!affordable) return { label: "Need XP", className: "bad", requestable: false };
    return { label: "Requestable", className: "good", requestable: true };
  }

  const visibleSkills = skills
    .filter((skill) => treeFilter === "all" || skill.tree === treeFilter)
    .filter((skill) => {
      const needle = searchText.trim().toLowerCase();
      if (!needle) return true;

      return (
        String(skill.name || "").toLowerCase().includes(needle) ||
        String(skill.skill_key || "").toLowerCase().includes(needle) ||
        String(skill.tree || "").toLowerCase().includes(needle) ||
        String(skill.description || "").toLowerCase().includes(needle) ||
        String(skill.effects || "").toLowerCase().includes(needle) ||
        String(skill.usage || "").toLowerCase().includes(needle)
      );
    })
    .filter((skill) => {
      if (statusFilter === "all") return true;

      const state = skillState(skill);

      if (statusFilter === "owned") return state.label === "Owned";
      if (statusFilter === "pending") return state.label === "Pending";
      if (statusFilter === "locked") return state.label === "Locked";
      if (statusFilter === "requestable") return state.label === "Requestable";
      if (statusFilter === "need_xp") return state.label === "Need XP";

      return true;
    });

  const groupedSkills = visibleSkills.reduce<Record<string, any[]>>((groups, skill) => {
    const tree = String(skill.tree || "General");
    if (!groups[tree]) groups[tree] = [];
    groups[tree].push(skill);
    return groups;
  }, {});

  async function requestSkill(skillKey: string) {
    if (!selectedCharacterId) {
      setMessage("Select an OC first.");
      return;
    }

    const note = window.prompt("Optional note for staff?") || "Requested from Railbound Tools dashboard.";

    await apiFetch(
      "/api/skill-requests",
      {
        method: "POST",
        body: JSON.stringify({
          character_id: selectedCharacterId,
          skill_key: skillKey,
          requested_by_discord_id: Number(discordId),
          submitter_note: note,
        }),
      },
      discordId
    );

    setMessage("Skill request submitted for staff review.");
    await load();
  }

  function toggleExpanded(skillKey: string) {
    setExpandedKeys((current) => ({
      ...current,
      [skillKey]: !current[skillKey],
    }));
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="card skills-catalog-card">
        <div className="card-title-row">
          <div>
            <h2>Skill Manager</h2>
            <p className="muted-text">
              Browse skill trees, check requirements, and submit purchase requests for staff review.
            </p>
          </div>
          <button className="ghost" onClick={load}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>

        <CharacterSelect
          discordId={discordId}
          selectedCharacterId={selectedCharacterId}
          setSelectedCharacterId={setSelectedCharacterId}
        />

        {wallet ? (
          <div className="summary">
            <div>
              <span>Available XP</span>
              <strong>{wallet.available_xp}</strong>
            </div>
            <div>
              <span>Owned</span>
              <strong>{ownedKeys.length}</strong>
            </div>
            <div>
              <span>Pending</span>
              <strong>{pendingKeys.length}</strong>
            </div>
          </div>
        ) : null}

        {message && <p className="message">{message}</p>}

        <div className="skill-toolbar">
          <label>
            Search
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Search name, effects, usage..."
            />
          </label>

          <label>
            Skill Tree
            <select value={treeFilter} onChange={(event) => setTreeFilter(event.target.value)}>
              {trees.map((tree) => (
                <option key={tree} value={tree}>
                  {tree === "all" ? "All Trees" : tree}
                </option>
              ))}
            </select>
          </label>

          <label>
            Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All Skills</option>
              <option value="requestable">Requestable</option>
              <option value="owned">Owned</option>
              <option value="pending">Pending</option>
              <option value="locked">Locked</option>
              <option value="need_xp">Need XP</option>
            </select>
          </label>
        </div>

        <div className="skill-results-strip">
          <span>{visibleSkills.length} visible skills</span>
          <span>{trees.length - 1} trees</span>
          <span>{skills.length} total catalog entries</span>
        </div>

        <div className="skill-tree-list">
          {Object.keys(groupedSkills).length === 0 ? <p>No skills match these filters.</p> : null}

          {Object.entries(groupedSkills).map(([tree, treeSkills]) => (
            <div className="skill-tree-section" key={tree}>
              <div className="skill-tree-heading">
                <h3>{tree}</h3>
                <span className="pill">{treeSkills.length} skills</span>
              </div>

              <div className="item-list skill-grid">
                {treeSkills.map((skill) => {
                  const state = skillState(skill);
                  const missing = missingPrereqs(skill);
                  const expanded = !!expandedKeys[skill.skill_key];

                  return (
                    <div className={`item-card skill-card-v2 ${state.label.toLowerCase().replace(" ", "-")}`} key={skill.skill_key}>
                      <div className="card-title-row">
                        <div>
                          <h3>{ownedKeys.includes(skill.skill_key) ? "✅ " : ""}{skill.name}</h3>
                          <p>
                            Tier {skill.tier ?? "—"} • {skill.cost} XP • {skill.skill_key}
                          </p>
                        </div>
                        <span className={`pill ${state.className}`}>{state.label}</span>
                      </div>

                      <p>{skill.description || "No description yet."}</p>

                      <div className="skill-meta-grid">
                        <div>
                          <span>Prerequisites</span>
                          <strong className={missing.length > 0 ? "bad" : ""}>
                            {missing.length > 0 ? `${missing.length} missing` : "Met"}
                          </strong>
                        </div>
                        <div>
                          <span>Source</span>
                          <strong>{skill.source_label || "—"}</strong>
                        </div>
                      </div>

                      {expanded ? (
                        <div className="skill-details">
                          <p><strong>Prereqs:</strong> {prereqSummary(skill)}</p>
                          {skill.chain ? <p><strong>Chain:</strong> {skill.chain}</p> : null}
                          {skill.usage ? <p><strong>Usage:</strong> {skill.usage}</p> : null}
                          {skill.effects ? <p><strong>Effects:</strong> {skill.effects}</p> : null}
                          {missing.length > 0 ? (
                            <p className="bad">
                              Missing: {missing.map((key) => skills.find((s) => s.skill_key === key)?.name || key).join(", ")}
                            </p>
                          ) : null}
                        </div>
                      ) : null}

                      <div className="actions">
                        <button className="ghost" onClick={() => toggleExpanded(skill.skill_key)}>
                          {expanded ? "Hide Details" : "Details"}
                        </button>
                        <button disabled={!state.requestable} onClick={() => requestSkill(skill.skill_key)}>
                          <Send size={16} /> {state.requestable ? "Request" : state.label}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {requests.length > 0 ? (
          <div className="skill-request-history">
            <h3>Recent Skill Requests</h3>
            <div className="item-list">
              {requests.slice(0, 8).map((request) => (
                <div className="request-card" key={request.request_id}>
                  <div>
                    <h3>{skills.find((skill) => skill.skill_key === request.skill_key)?.name || request.skill_key}</h3>
                    <p>
                      {String(request.status || "unknown").toUpperCase()} • {request.cost} XP
                    </p>
                    {request.staff_note ? <small>Staff note: {request.staff_note}</small> : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </RequireDiscord>
  );
}

function OCRegistrationDashboard({ discordId, jump }: { discordId: string; jump: (tab: Tab) => void }) {
  const [options, setOptions] = useState<any>({ traits: [], max_starting_traits: 8 });
  const [message, setMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState<any>(null);
  const [traitSearch, setTraitSearch] = useState("");
  const [traitTierFilter, setTraitTierFilter] = useState("all");
  const [createdCharacterId, setCreatedCharacterId] = useState("");
  const [registrationSkills, setRegistrationSkills] = useState<any[]>([]);
  const [form, setForm] = useState({
    name: "",
    sheet_url: "",
    occupation: "",
    affiliation: "",
    blurb: "",
    origin_trait_id: "",
    trait_ids: [] as string[],
    benefit_skill_key: "",
  });

  async function loadOptions() {
    const data = await apiFetch("/api/oc-registration/options", {}, discordId);
    setOptions(data);

    try {
      const skillData = await apiFetch("/api/skills", {}, discordId);
      setRegistrationSkills(skillData.skills || []);
    } catch {
      setRegistrationSkills([]);
    }
  }

  useEffect(() => {
    if (discordId) loadOptions().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  async function validate(nextForm = form) {
    try {
      const data = await apiFetch(
        "/api/oc-registration/validate",
        {
          method: "POST",
          body: JSON.stringify({
            origin_trait_id: nextForm.origin_trait_id,
            trait_ids: nextForm.trait_ids,
          }),
        },
        discordId
      );
      setValidation(data);
      return data;
    } catch (error: any) {
      const data = { ok: false, error: error.message };
      setValidation(data);
      return data;
    }
  }

  function updateForm(patch: Partial<typeof form>) {
    const next = { ...form, ...patch };
    setForm(next);
    setSuccessMessage("");
    setCreatedCharacterId("");
    validate(next);
  }

  function toggleTrait(traitId: string) {
    const exists = form.trait_ids.includes(traitId);
    const nextTraitIds = exists
      ? form.trait_ids.filter((id) => id !== traitId)
      : [...form.trait_ids, traitId];

    updateForm({ trait_ids: nextTraitIds });
  }

  async function submit() {
    setSaving(true);
    setMessage("");
    setSuccessMessage("");

    try {
      const check = await validate();
      if (check?.ok === false) {
        setMessage(check.error || "Please fix the registration errors first.");
        return;
      }

      const registrationPayload = {
        name: form.name,
        sheet_url: form.sheet_url,
        occupation: form.occupation,
        affiliation: form.affiliation,
        blurb: form.blurb,
        origin_trait_id: form.origin_trait_id,
        trait_ids: form.trait_ids,
      };

      const data = await apiFetch(
        "/api/oc-registration/characters",
        {
          method: "POST",
          body: JSON.stringify(registrationPayload),
        },
        discordId
      );

      const newCharacterId = data.character_id || data.character?.character_id || "";
      let extraMessage = "";

      if (newCharacterId && form.benefit_skill_key) {
        const chosenSkill = registrationSkills.find((skill: any) => skill.skill_key === form.benefit_skill_key);
        const chosenOrigin = traits.find((trait: any) => trait.trait_id === form.origin_trait_id);
        await apiFetch(
          "/api/skill-requests",
          {
            method: "POST",
            body: JSON.stringify({
              character_id: newCharacterId,
              skill_key: form.benefit_skill_key,
              requested_by_discord_id: Number(discordId),
              submitter_note: `Trait benefit request from ${chosenOrigin?.name || "selected Origin trait"}: ${chosenSkill?.name || form.benefit_skill_key}. Staff should approve as a free 0 XP trait benefit if valid.`,
            }),
          },
          discordId
        );
        extraMessage = " Trait benefit skill request submitted for staff review.";
      }

      setCreatedCharacterId(newCharacterId);
      setSuccessMessage((data.message || "OC registered.") + extraMessage);
      setMessage("");

      setForm({
        name: "",
        sheet_url: "",
        occupation: "",
        affiliation: "",
        blurb: "",
        origin_trait_id: "",
        trait_ids: [],
        benefit_skill_key: "",
      });
      setValidation(null);
    } catch (error: any) {
      setMessage(error.message || "Could not register OC.");
    } finally {
      setSaving(false);
    }
  }

  function prettyTraitTier(trait: any) {
    const tier = String(trait.tier || "Trait").toLowerCase();

    if (tier === "keystone") return "Keystone Trait";
    if (tier === "minor") return "Minor Trait";
    if (tier === "reliable") return "Reliable Trait";
    if (tier === "negative") return "Negative Trait";
    if (tier === "origin") return "Origin Trait";

    return `${tier.slice(0, 1).toUpperCase()}${tier.slice(1)} Trait`;
  }

  function traitLabel(trait: any) {
    const cost = Number(trait.cost || 0);
    const sign = cost > 0 ? `+${cost}` : String(cost);
    return `${trait.name || "Trait"} (${trait.tier || "?"}, ${sign})`;
  }

  function tierLabel(value: string) {
    if (value === "all") return "All";
    if (value === "keystone") return "Keystone";
    return value.slice(0, 1).toUpperCase() + value.slice(1);
  }

  const traits = options.traits || [];
  const originTraits = traits.filter((trait: any) => String(trait.tier || "").toLowerCase() === "origin");
  const startingTraits = traits.filter((trait: any) => String(trait.tier || "").toLowerCase() !== "origin");

  const selectedTraitObjects = [
    ...traits.filter((trait: any) => trait.trait_id === form.origin_trait_id),
    ...traits.filter((trait: any) => form.trait_ids.includes(trait.trait_id)),
  ];

  const query = traitSearch.trim().toLowerCase();

  const filteredStartingTraits = startingTraits.filter((trait: any) => {
    const tier = String(trait.tier || "").toLowerCase();
    const haystack = [
      trait.name,
      trait.slug,
      trait.tier,
      trait.cost,
      trait.exclusive_group,
      JSON.stringify(trait.requirements_json || {}),
    ]
      .join(" ")
      .toLowerCase();

    if (traitTierFilter !== "all" && tier !== traitTierFilter) return false;
    if (query && !haystack.includes(query)) return false;

    return true;
  });

  const selectedOriginTrait = traits.find((trait: any) => trait.trait_id === form.origin_trait_id);

  function traitGrantConfig(trait: any) {
    const effects = trait?.effects_json || {};
    const grants = effects.grants || effects.grant || effects.benefit || effects.benefits || {};
    const rawSkills = grants.skills || grants.skill_keys || grants.choices || grants.allowed_skills || grants.eligible_skills || [];

    if (Array.isArray(rawSkills)) {
      return rawSkills
        .map((item: any) => (typeof item === "string" ? item : item?.skill_key || item?.key || item?.skill || ""))
        .filter(Boolean);
    }

    if (typeof rawSkills === "string") return [rawSkills];
    return [];
  }

  const benefitSkillKeys = traitGrantConfig(selectedOriginTrait);
  const eligibleBenefitSkills = benefitSkillKeys.length > 0
    ? registrationSkills.filter((skill: any) => benefitSkillKeys.includes(skill.skill_key))
    : registrationSkills;

  const summary = validation?.summary || {
    positive: 0,
    negative: 0,
    overdraft_limit: 5,
  };

  const canSubmit = Boolean(form.name.trim()) && validation?.ok !== false && !saving;

  return (
    <RequireDiscord discordId={discordId}>
      <section className="oc-register-page">
        <div className="card oc-register-hero">
          <div>
            <span className="activity-type-label">Guided Intake</span>
            <h2>Register a New OC</h2>
            <p className="muted-text">
              Register the character, connect their sheet, set public registry basics, and select starting traits.
            </p>
          </div>
          <button className="ghost" onClick={loadOptions}>
            <RefreshCw size={16} /> Refresh Options
          </button>
        </div>

        {successMessage ? (
          <div className="card oc-register-success">
            <div>
              <span className="activity-type-label">Registration Complete</span>
              <h3>{successMessage}</h3>
              <p className="muted-text">The OC has been created and should now appear in the Citizen Registry.</p>
            </div>
            <div className="auth-actions">
              <button onClick={() => jump("registry")}>View Citizen Registry</button>
              <button className="ghost" onClick={() => jump("oc")}>Go to OC Page</button>
            </div>
          </div>
        ) : null}

        <div className="oc-register-layout">
          <div className="card">
            <h3>1. Character Basics</h3>
            <p className="muted-text">
              Your full sheet still handles appearance, wardrobe, health, backstory, inventory, skills, relationships,
              missions, events, and XP audit. This form makes the official OC record.
            </p>

            <div className="oc-register-form">
              <label>
                <span>Character Name</span>
                <input
                  value={form.name}
                  onChange={(event) => updateForm({ name: event.target.value })}
                  placeholder="Meris Philon"
                />
              </label>

              <label>
                <span>Character Sheet Link</span>
                <input
                  value={form.sheet_url}
                  onChange={(event) => updateForm({ sheet_url: event.target.value })}
                  placeholder="https://..."
                />
              </label>

              <label>
                <span>Occupation</span>
                <input
                  value={form.occupation}
                  onChange={(event) => updateForm({ occupation: event.target.value })}
                  placeholder="Engineer, medic, smuggler..."
                />
              </label>

              <label>
                <span>Affiliation</span>
                <input
                  value={form.affiliation}
                  onChange={(event) => updateForm({ affiliation: event.target.value })}
                  placeholder="Guild, crew, company, faction..."
                />
              </label>

              <label className="oc-register-wide">
                <span>Public Blurb</span>
                <textarea
                  value={form.blurb}
                  onChange={(event) => updateForm({ blurb: event.target.value })}
                  placeholder="A short public-facing description for the Citizen Registry."
                  rows={4}
                />
              </label>
            </div>
          </div>

          <div className="card">
            <h3>2. Starting Traits</h3>
            <p className="muted-text">
              Choose one Origin trait, then select up to {options.max_starting_traits || 8} starting traits.
            </p>

            <label>
              <span>Origin Trait</span>
              <select
                value={form.origin_trait_id}
                onChange={(event) => updateForm({ origin_trait_id: event.target.value, benefit_skill_key: "" })}
              >
                <option value="">No Origin selected</option>
                {originTraits.map((trait: any) => (
                  <option value={trait.trait_id} key={trait.trait_id}>
                    {traitLabel(trait)}
                  </option>
                ))}
              </select>
            </label>

            <div className="trait-benefit-request-card">
              <h4>Origin / Trait Free Skill Request</h4>
              <p className="muted-text">
                If your Origin or trait grants a free skill choice, select it here. Keystone will submit it for staff review after registration.
              </p>

              {selectedOriginTrait ? (
                <div className="request-note-block">
                  <span>Selected Origin</span>
                  <p>{selectedOriginTrait.name || "Origin Trait"}</p>
                </div>
              ) : null}

              <label>
                <span>Free Skill Choice</span>
                <select
                  value={form.benefit_skill_key}
                  onChange={(event) => updateForm({ benefit_skill_key: event.target.value })}
                  disabled={!form.origin_trait_id}
                >
                  <option value="">No free skill request</option>
                  {eligibleBenefitSkills.map((skill: any) => (
                    <option key={skill.skill_key} value={skill.skill_key}>
                      {skill.name || skill.skill_key}{skill.tree ? ` / ${skill.tree}` : ""}{skill.cost !== undefined ? ` / ${skill.cost} XP normally` : ""}
                    </option>
                  ))}
                </select>
              </label>

              {selectedOriginTrait && benefitSkillKeys.length === 0 ? (
                <p className="muted-text">
                  This trait does not have encoded skill options yet, so the list shows all active skills for beta. Staff will verify the choice before approving it as free.
                </p>
              ) : null}

              {form.benefit_skill_key ? (
                <p className="good-text">
                  This will create a pending trait benefit request after the OC is registered.
                </p>
              ) : null}
            </div>

            <div className="trait-polish-toolbar">
              <input
                value={traitSearch}
                onChange={(event) => setTraitSearch(event.target.value)}
                placeholder="Search traits..."
              />

              <div className="trait-tier-filters">
                {["all", "minor", "reliable", "keystone", "negative"].map((tier) => (
                  <button
                    type="button"
                    key={tier}
                    className={traitTierFilter === tier ? "selected" : ""}
                    onClick={() => setTraitTierFilter(tier)}
                  >
                    {tierLabel(tier)}
                  </button>
                ))}
              </div>
            </div>

            <div className="trait-count-row">
              <span>{form.trait_ids.length}/{options.max_starting_traits || 8} starting traits selected</span>
              <span>{filteredStartingTraits.length} visible</span>
            </div>

            <div className="trait-picker-grid polished">
              {filteredStartingTraits.length === 0 ? (
                <p className="muted-text">No traits match that filter.</p>
              ) : null}

              {filteredStartingTraits.map((trait: any) => {
                const selected = form.trait_ids.includes(trait.trait_id);
                const disabled = !selected && form.trait_ids.length >= (options.max_starting_traits || 8);

                return (
                  <button
                    type="button"
                    key={trait.trait_id}
                    className={`trait-picker-card ${selected ? "selected" : ""}`}
                    disabled={disabled}
                    onClick={() => toggleTrait(trait.trait_id)}
                  >
                    <strong>{trait.name || "Trait"}</strong>
                    <span className="trait-display-meta">{prettyTraitTier(trait)}</span>
                    
                  </button>
                );
              })}
            </div>
          </div>

          <div className="card oc-register-summary-card">
            <h3>3. Review & Submit</h3>

            <div className="summary">
              <div>
                <span>Positive</span>
                <strong>{summary.positive}</strong>
              </div>
              <div>
                <span>Negative</span>
                <strong>{summary.negative}</strong>
              </div>
              <div>
                <span>Limit</span>
                <strong>{summary.overdraft_limit}</strong>
              </div>
            </div>

            {validation?.error ? <p className="message">{validation.error}</p> : null}
            {validation?.ok ? <p className="good-text">✅ Trait build is legal.</p> : null}

            <h4>Selected Traits</h4>
            <div className="selected-trait-list">
              {selectedTraitObjects.length === 0 ? <p className="muted-text">No traits selected yet.</p> : null}

              {selectedTraitObjects.map((trait: any) => {
                const isOrigin = trait.trait_id === form.origin_trait_id;

                return (
                  <div className="selected-trait-row" key={trait.trait_id}>
                    <div>
                      <strong>{trait.name}</strong>
                      <span className="trait-display-meta">{prettyTraitTier(trait)}</span>
                    </div>
                    {isOrigin ? (
                      <em>Origin</em>
                    ) : (
                      <button type="button" className="ghost" onClick={() => toggleTrait(trait.trait_id)}>
                        Remove
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            {message ? <p className="message">{message}</p> : null}

            <button onClick={submit} disabled={!canSubmit}>
              {saving ? "Registering..." : "Register OC"}
            </button>
          </div>
        </div>
      </section>
    </RequireDiscord>
  );
}

function OCRegistry({ discordId }: { discordId: string }) {
  const [characters, setCharacters] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [search, setSearch] = useState("");
  const [guildFilter, setGuildFilter] = useState("all");
  const [message, setMessage] = useState("");
  const [profileTab, setProfileTab] = useState("overview");
  const [profileForm, setProfileForm] = useState({
    occupation: "",
    affiliation: "",
    sheet_url: "",
    portrait_url: "",
    blurb: "",
  });
  const [profileMessage, setProfileMessage] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [balanceData, setBalanceData] = useState<any>(null);

  function syncProfileForm(character: any) {
    setProfileForm({
      occupation: character?.occupation || "",
      affiliation: character?.affiliation || "",
      sheet_url: character?.sheet_url || "",
      portrait_url: character?.portrait_url || "",
      blurb: character?.blurb || "",
    });
  }

  async function loadRegistry(query = search) {
    setMessage("");

    const params = new URLSearchParams({
      limit: "120",
    });

    if (query.trim()) params.set("search", query.trim());

    const data = await apiFetch(`/api/registry/characters?${params.toString()}`, {}, discordId);
    const rows = data.characters || [];

    setCharacters(rows);

    if (!selected && rows.length > 0) {
      openCharacter(rows[0].character_id).catch(() => {
        setSelected(rows[0]);
        syncProfileForm(rows[0]);
      });
    }
  }

  async function openCharacter(characterId: string) {
    setMessage("");
    setProfileMessage("");
    setProfileTab("overview");
    setBalanceData(null);

    const data = await apiFetch(`/api/registry/characters/${characterId}`, {}, discordId);
    setSelected(data.character);
    syncProfileForm(data.character);
  }

  async function loadBalances(characterId: string) {
    if (!discordId || !characterId) return;

    try {
      const data = await apiFetch(`/api/characters/${characterId}/balances`, {}, discordId);
      setBalanceData(data);
    } catch {
      setBalanceData(null);
    }
  }

  async function savePublicProfile() {
    if (!selected?.character_id) return;

    setSavingProfile(true);
    setProfileMessage("");

    try {
      const data = await apiFetch(
        `/api/registry/characters/${selected.character_id}/profile`,
        {
          method: "PATCH",
          body: JSON.stringify(profileForm),
        },
        discordId
      );

      const updated = data.character;
      setSelected(updated);
      syncProfileForm(updated);

      setCharacters((current) =>
        current.map((character) =>
          character.character_id === updated.character_id ? { ...character, ...updated } : character
        )
      );

      setProfileMessage("Public profile updated.");
    } catch (error: any) {
      setProfileMessage(error.message || "Could not update public profile.");
    } finally {
      setSavingProfile(false);
    }
  }

  async function uploadPortraitFile(file: File | null) {
    if (!file || !selected?.character_id) return;

    setSavingProfile(true);
    setProfileMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/api/registry/characters/${selected.character_id}/portrait`, {
        method: "POST",
        headers: {
          "X-Discord-ID": discordId,
        },
        credentials: "include",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Could not upload portrait.");
      }

      const updated = data.character;
      setSelected(updated);
      syncProfileForm(updated);

      setCharacters((current) =>
        current.map((character) =>
          character.character_id === updated.character_id ? { ...character, ...updated } : character
        )
      );

      setProfileMessage("Portrait uploaded.");
    } catch (error: any) {
      setProfileMessage(error.message || "Could not upload portrait.");
    } finally {
      setSavingProfile(false);
    }
  }

  useEffect(() => {
    if (discordId) loadRegistry().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  const canEditSelected =
    selected?.owner_discord_id && discordId && String(selected.owner_discord_id) === String(discordId);

  useEffect(() => {
    if (canEditSelected && selected?.character_id) {
      loadBalances(selected.character_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canEditSelected, selected?.character_id, discordId]);

  function formatKey(value: string) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function formatDate(value: string | null | undefined) {
    if (!value) return "No recent sightings";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);

    return date.toLocaleString();
  }

  function fieldValue(value: any) {
    return value ? String(value) : "—";
  }

  function cleanAffiliation(value: any) {
    return String(value || "").trim();
  }

  function affiliationMatchesGuild(character: any, guild: string) {
    if (guild === "all") return true;
    if (guild === "none") return !cleanAffiliation(character.affiliation);

    const affiliation = cleanAffiliation(character.affiliation).toLowerCase();
    return affiliation.includes(guild.toLowerCase());
  }

  function statusClass(status: string | null | undefined) {
    const normalized = String(status || "unknown").toLowerCase();

    if (normalized === "active") return "active";
    if (normalized === "quiet") return "quiet";
    if (normalized === "inactive") return "inactive";
    if (normalized === "archived") return "inactive";
    return "unknown";
  }

  function visibleStats(stats: any) {
    if (!stats) return [];

    const hidden = new Set(["guild_id", "character_id", "id", "created_at", "updated_at"]);
    const preferredOrder = [
      "strength",
      "dexterity",
      "stamina",
      "magic_affinity",
      "mana",
      "hp",
      "health",
      "max_hp",
      "speed",
      "movement",
      "dodge",
      "blitz",
      "carry_capacity",
      "carrying_capacity",
      "safe_output",
      "fortitude",
      "reaction_score",
      "reaction",
      "accuracy",
      "evasion",
      "defense",
      "physical_defense",
      "magical_defense",
      "available_xp",
      "spent_xp",
      "total_xp",
      "xp",
    ];

    const entries = Object.entries(stats).filter(
      ([key, value]) => !hidden.has(key) && value !== null && value !== undefined && typeof value !== "object"
    );

    return entries.sort(([a], [b]) => {
      const ai = preferredOrder.indexOf(a);
      const bi = preferredOrder.indexOf(b);

      if (ai === -1 && bi === -1) return a.localeCompare(b);
      if (ai === -1) return 1;
      if (bi === -1) return -1;

      return ai - bi;
    });
  }

  function publicTabs() {
    const tabs = [
      ["overview", "Overview"],
      ["stats", "Stats"],
      ["traits", "Traits"],
      ["skills", "Skills"],
      ["inventory", "Inventory"],
      ["activity", "RP Activity"],
    ];

    if (canEditSelected) tabs.push(["edit", "Edit"]);

    return tabs;
  }

  const xp = balanceData?.xp || {};
  const currencies = balanceData?.currencies || [];

  const affiliationOptions = Array.from(
    new Set(
      characters
        .map((character) => cleanAffiliation(character.affiliation))
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));

  const visibleCharacters = characters.filter((character) => affiliationMatchesGuild(character, guildFilter));
  const lastSeen = selected?.last_seen;

  return (
    <RequireDiscord discordId={discordId}>
      <section className="registry-page-v2 registry-polish-page">
        <div className="card registry-hero-card">
          <div className="card-title-row">
            <div>
              <span className="activity-type-label">Public Records</span>
              <h2>Citizen Registry</h2>
              <p className="muted-text">
                Browse Railbound citizens, open public character files, and review stats, skills, inventory, and RP activity.
              </p>
            </div>
            <button className="ghost" onClick={() => loadRegistry()}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>

          <div className="registry-search-row">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") loadRegistry();
              }}
              placeholder="Search name, occupation, affiliation, origin..."
            />

            <select
              value={guildFilter}
              onChange={(event) => setGuildFilter(event.target.value)}
              title="Filter by affiliation / mercenary guild"
            >
              <option value="all">All guilds / affiliations</option>
              <option value="none">No affiliation listed</option>
              {affiliationOptions.map((affiliation) => (
                <option value={affiliation} key={affiliation}>
                  {affiliation}
                </option>
              ))}
            </select>

            <button onClick={() => loadRegistry()}>Search</button>
          </div>

          {message && <p className="message">{message}</p>}
        </div>

        <div className="registry-layout registry-layout-v2 registry-polish-layout">
          <div className="registry-list card">
            <div className="card-title-row">
              <h3>Roster</h3>
              <span className="pill">{visibleCharacters.length}/{characters.length} citizens</span>
            </div>

            <div className="registry-card-scroll">
              {characters.length === 0 ? <p className="muted-text">No citizens found yet.</p> : null}
              {characters.length > 0 && visibleCharacters.length === 0 ? <p className="muted-text">No citizens match that guild/affiliation filter.</p> : null}

              {visibleCharacters.map((character) => (
                <button
                  type="button"
                  key={character.character_id}
                  className={`citizen-registry-card ${selected?.character_id === character.character_id ? "active" : ""}`}
                  onClick={() => openCharacter(character.character_id)}
                >
                  <div className="citizen-card-topline">
                    <div>
                      <strong>{character.name}</strong>
                      <span>{fieldValue(character.occupation)}</span>
                    </div>
                    <em className={`citizen-status ${statusClass(character.status)}`}>{character.status || "Unknown"}</em>
                  </div>

                  <dl className="citizen-card-fields">
                    <div>
                      <dt>Affiliation</dt>
                      <dd>{fieldValue(character.affiliation)}</dd>
                    </div>
                    <div>
                      <dt>Last Seen</dt>
                      <dd>{character.last_seen?.label || "No recent sightings"}</dd>
                    </div>
                  </dl>
                </button>
              ))}
            </div>
          </div>

          <div className="registry-profile card registry-polish-profile">
            {!selected ? (
              <p className="muted-text">Select a citizen to view their public file.</p>
            ) : (
              <>
                <div className="registry-profile-header citizen-file-header registry-polish-header">
                  {selected.portrait_url ? (
                    <img src={selected.portrait_url} alt="" />
                  ) : (
                    <div className="registry-profile-placeholder">{String(selected.name || "?").slice(0, 1)}</div>
                  )}

                  <div className="registry-polish-heading">
                    <span className="activity-type-label">Citizen File</span>
                    <h2>{selected.name}</h2>
                    <p className="muted-text">
                      {[selected.occupation, selected.affiliation, selected.origin].filter(Boolean).join(" • ") ||
                        "Public character file"}
                    </p>

                    <div className="citizen-file-meta registry-polish-actions">
                      <span className={`citizen-status ${statusClass(selected.status)}`}>{selected.status || "Unknown"}</span>
                      {selected.owner_display_name ? <small>Player: {selected.owner_display_name}</small> : null}
                      {selected.sheet_url ? (
                        <a href={selected.sheet_url} target="_blank" rel="noreferrer">
                          Open Sheet
                        </a>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="registry-profile-tabs">
                  {publicTabs().map(([key, label]) => (
                    <button
                      type="button"
                      key={key}
                      className={profileTab === key ? "active" : ""}
                      onClick={() => setProfileTab(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {profileTab === "overview" ? (
                  <div className="registry-tab-panel">
                    <div className="citizen-file-grid polished">
                      <div>
                        <span>Name</span>
                        <strong>{selected.name}</strong>
                      </div>
                      <div>
                        <span>Occupation</span>
                        <strong>{fieldValue(selected.occupation)}</strong>
                      </div>
                      <div>
                        <span>Status</span>
                        <strong>{selected.status || "Unknown"}</strong>
                      </div>
                      <div>
                        <span>Affiliation</span>
                        <strong>{fieldValue(selected.affiliation)}</strong>
                      </div>
                      <div>
                        <span>Origin</span>
                        <strong>{fieldValue(selected.origin)}</strong>
                      </div>
                      <div>
                        <span>Last Seen</span>
                        <strong>{lastSeen?.label || "No recent sightings"}</strong>
                        {lastSeen?.at ? <small>{formatDate(lastSeen.at)}</small> : null}
                      </div>
                    </div>

                    {canEditSelected && (balanceData || currencies.length > 0) ? (
                      <div className="registry-section registry-wallet-preview">
                        <h3>Private Balance Preview</h3>
                        <div className="registry-wallet-grid">
                          <div>
                            <span>Available XP</span>
                            <strong>{xp.available_xp ?? xp.current_xp ?? "—"}</strong>
                          </div>
                          {currencies.map((currency: any, index: number) => (
                            <div key={`${currency.currency_id || currency.name}-${index}`}>
                              <span>{currency.ticker || currency.name || "Currency"}</span>
                              <strong>{currency.balance ?? 0}</strong>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {selected.blurb ? (
                      <div className="registry-section registry-overview-blurb">
                        <h3>Overview</h3>
                        <p>{selected.blurb}</p>
                      </div>
                    ) : (
                      <div className="registry-empty-state">
                        <strong>No public overview yet.</strong>
                        <p className="muted-text">This citizen has not added a public blurb.</p>
                      </div>
                    )}
                  </div>
                ) : null}

                {profileTab === "stats" ? (
                  <div className="registry-tab-panel">
                    <div className="registry-stat-grid polished">
                      {visibleStats(selected.stats).length === 0 ? (
                        <div className="registry-empty-state">
                          <strong>No public stats found yet.</strong>
                          <p className="muted-text">Stats will appear here once this OC has registered stat data.</p>
                        </div>
                      ) : null}

                      {visibleStats(selected.stats).map(([key, value]) => (
                        <div className="registry-stat" key={key}>
                          <span>{formatKey(key)}</span>
                          <strong>{String(value)}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {profileTab === "traits" ? (
                  <div className="registry-tab-panel">
                    <div className="registry-chip-list polished">
                      {(selected.traits || []).length === 0 ? (
                        <div className="registry-empty-state">
                          <strong>No public traits found yet.</strong>
                          <p className="muted-text">Traits will appear here once attached to this OC.</p>
                        </div>
                      ) : null}

                      {(selected.traits || []).map((trait: any, index: number) => (
                        <span className="registry-chip" key={`${trait.name}-${index}`}>
                          {trait.name}
                          {trait.type ? <small>{formatKey(trait.type)}</small> : null}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {profileTab === "skills" ? (
                  <div className="registry-tab-panel">
                    <div className="registry-chip-list polished">
                      {(selected.skills || []).length === 0 ? (
                        <div className="registry-empty-state">
                          <strong>No public skills found yet.</strong>
                          <p className="muted-text">Purchased or granted skills will appear here.</p>
                        </div>
                      ) : null}

                      {(selected.skills || []).map((skill: any, index: number) => (
                        <span className="registry-chip" key={`${skill.skill_key || skill.name}-${index}`}>
                          {skill.name || formatKey(skill.skill_key)}
                          {skill.tree ? <small>{skill.tree}</small> : null}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {profileTab === "inventory" ? (
                  <div className="registry-tab-panel">
                    <div className="registry-inventory-list polished">
                      {(selected.inventory || []).length === 0 ? (
                        <div className="registry-empty-state">
                          <strong>No public inventory found yet.</strong>
                          <p className="muted-text">Inventory items will appear here once logged.</p>
                        </div>
                      ) : null}

                      {(selected.inventory || []).map((item: any, index: number) => (
                        <div className="registry-inventory-item" key={`${item.name}-${index}`}>
                          <strong>{item.name}</strong>
                          <span>Qty: {item.quantity || 1}</span>
                          {item.type ? <small>{item.type}</small> : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {profileTab === "activity" ? (
                  <div className="registry-tab-panel">
                    <div className="registry-inventory-list polished">
                      {(selected.recent_posts || []).length === 0 ? (
                        <div className="registry-empty-state">
                          <strong>No recent RP activity found.</strong>
                          <p className="muted-text">Last Seen and recent RP posts will appear here after tracked RP activity.</p>
                        </div>
                      ) : null}

                      {(selected.recent_posts || []).map((post: any, index: number) => (
                        <div className="registry-inventory-item registry-rp-row" key={`${post.created_at}-${index}`}>
                          <div>
                            <strong>{post.channel_label || "Unknown location"}</strong>
                            <small>{formatDate(post.created_at)}</small>
                          </div>
                          {post.jump_url ? (
                            <a href={post.jump_url} target="_blank" rel="noreferrer">
                              Open
                            </a>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {profileTab === "edit" && canEditSelected ? (
                  <div className="registry-tab-panel">
                    <div className="registry-section public-profile-editor compact">
                      <div className="card-title-row">
                        <div>
                          <h3>Edit Public Profile</h3>
                          <p className="muted-text">
                            These fields appear on the Citizen Registry and public character file.
                          </p>
                        </div>
                      </div>

                      <div className="public-profile-form">
                        <label>
                          <span>Occupation</span>
                          <input
                            value={profileForm.occupation}
                            onChange={(event) => setProfileForm((current) => ({ ...current, occupation: event.target.value }))}
                            placeholder="Engineer, Mercenary, Doctor, Smuggler..."
                          />
                        </label>

                        <label>
                          <span>Affiliation</span>
                          <input
                            value={profileForm.affiliation}
                            onChange={(event) => setProfileForm((current) => ({ ...current, affiliation: event.target.value }))}
                            placeholder="Guild, crew, company, faction..."
                          />
                        </label>

                        <label>
                          <span>Character Sheet Link</span>
                          <input
                            value={profileForm.sheet_url}
                            onChange={(event) => setProfileForm((current) => ({ ...current, sheet_url: event.target.value }))}
                            placeholder="https://..."
                          />
                        </label>

                        <label>
                          <span>Portrait/Image Link</span>
                          <input
                            value={profileForm.portrait_url}
                            onChange={(event) => setProfileForm((current) => ({ ...current, portrait_url: event.target.value }))}
                            placeholder="https://..."
                          />
                        </label>

                        <label className="public-profile-upload-row">
                          <span>Upload Portrait</span>
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp,image/gif"
                            onChange={(event) => uploadPortraitFile(event.target.files?.[0] || null)}
                            disabled={savingProfile}
                          />
                        </label>

                        <label className="public-profile-form-wide">
                          <span>Public Blurb</span>
                          <textarea
                            value={profileForm.blurb}
                            onChange={(event) => setProfileForm((current) => ({ ...current, blurb: event.target.value }))}
                            placeholder="A short public-facing description for other players."
                            rows={4}
                          />
                        </label>
                      </div>

                      <div className="auth-actions">
                        <button onClick={savePublicProfile} disabled={savingProfile}>
                          {savingProfile ? "Saving..." : "Save Public Profile"}
                        </button>
                        {profileMessage ? <span className="muted-text">{profileMessage}</span> : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>
      </section>
    </RequireDiscord>
  );
}

function ProductionQADashboard({ discordId, jump }: { discordId: string; jump: (tab: Tab) => void }) {
  const checklistGroups = [
    {
      title: "Access & Welcome to Railbound Tools",
      items: [
        "Open Railway frontend on desktop",
        "Open Railway frontend on mobile",
        "Login with Discord",
        "Confirm Dev Welcome to Railbound Tools is not visible publicly",
        "Confirm user avatar/name loads after login",
      ],
    },
    {
      title: "Core Player Flow",
      items: [
        "Dashboard loads without overlap on desktop",
        "Dashboard loads without overlap on mobile",
        "Register a test OC",
        "Confirm test OC appears in Citizen Registry",
        "Open OC tab and select the new OC",
        "Confirm XP & Currency card loads",
        "Confirm owned skills section loads",
      ],
    },
    {
      title: "Citizen Registry",
      items: [
        "Search by OC name",
        "Open a citizen profile",
        "Check Overview tab",
        "Check Stats tab",
        "Check Traits tab",
        "Check Skills tab",
        "Check Inventory tab",
        "Check RP Activity tab",
        "Owner can access Edit tab",
        "Non-owner cannot access Edit tab",
      ],
    },
    {
      title: "OC Management",
      items: [
        "Open Manage OC tab",
        "Edit name/occupation/affiliation",
        "Edit sheet link",
        "Edit public blurb",
        "Archive OC",
        "Restore OC",
        "Staff-only delete test OC works",
        "Non-staff cannot delete OC",
      ],
    },
    {
      title: "Staff & Requests",
      items: [
        "Staff Queue loads",
        "Pending stat requests load",
        "Pending skill requests load",
        "Approve flow works",
        "Deny flow works",
        "Activity page shows recent updates",
      ],
    },
    {
      title: "Railway Deployment",
      items: [
        "Frontend deploy succeeds",
        "Backend deploy succeeds",
        "Frontend VITE_API_BASE_URL points to backend",
        "Backend FRONTEND_URL points to frontend",
        "Discord OAuth redirect URI matches backend callback",
        "CORS_ORIGINS includes frontend URL",
      ],
    },
  ];

  const storageKey = "railbound-production-qa-v1";

  const [checked, setChecked] = useState<Record<string, boolean>>(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch {
      return {};
    }
  });

  const [notes, setNotes] = useState(() => {
    try {
      return localStorage.getItem(`${storageKey}-notes`) || "";
    } catch {
      return "";
    }
  });

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(checked));
  }, [checked]);

  useEffect(() => {
    localStorage.setItem(`${storageKey}-notes`, notes);
  }, [notes]);

  function keyFor(groupTitle: string, item: string) {
    return `${groupTitle}::${item}`;
  }

  const allItems = checklistGroups.flatMap((group) => group.items.map((item) => keyFor(group.title, item)));
  const completed = allItems.filter((key) => checked[key]).length;
  const total = allItems.length;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  function toggle(groupTitle: string, item: string) {
    const key = keyFor(groupTitle, item);
    setChecked((current) => ({ ...current, [key]: !current[key] }));
  }

  function resetChecklist() {
    setChecked({});
    setNotes("");
    localStorage.removeItem(storageKey);
    localStorage.removeItem(`${storageKey}-notes`);
  }

  function copySummary() {
    const lines = [
      `Railbound Tools Production QA: ${completed}/${total} complete (${percent}%)`,
      "",
      ...checklistGroups.flatMap((group) => [
        group.title,
        ...group.items.map((item) => `${checked[keyFor(group.title, item)] ? "✅" : "⬜"} ${item}`),
        "",
      ]),
      notes ? `Notes:\n${notes}` : "",
    ];

    navigator.clipboard?.writeText(lines.join("\n"));
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="qa-page">
        <div className="card qa-hero">
          <div>
            <span className="activity-type-label">Release Readiness</span>
            <h2>Production QA Checklist</h2>
            <p className="muted-text">
              Use this before staff/player testing. Progress saves in this browser so you can refresh without losing checks.
            </p>
          </div>

          <div className="qa-progress-card">
            <strong>{percent}%</strong>
            <span>{completed}/{total} checks complete</span>
          </div>
        </div>

        <div className="card qa-actions-card">
          <div className="auth-actions">
            <button onClick={() => jump("dashboard")}>Open Dashboard</button>
            <button className="ghost" onClick={() => jump("register")}>Test Register OC</button>
            <button className="ghost" onClick={() => jump("registry")}>Test Registry</button>
            <button className="ghost" onClick={() => jump("manage_oc")}>Test Manage OC</button>
            <button className="ghost" onClick={copySummary}>Copy QA Summary</button>
            <button className="ghost" onClick={resetChecklist}>Reset</button>
          </div>
        </div>

        <div className="qa-grid">
          {checklistGroups.map((group) => {
            const groupCompleted = group.items.filter((item) => checked[keyFor(group.title, item)]).length;

            return (
              <div className="card qa-group-card" key={group.title}>
                <div className="card-title-row">
                  <div>
                    <h3>{group.title}</h3>
                    <p className="muted-text">{groupCompleted}/{group.items.length} complete</p>
                  </div>
                  <span className="pill">{Math.round((groupCompleted / group.items.length) * 100)}%</span>
                </div>

                <div className="qa-checklist">
                  {group.items.map((item) => {
                    const key = keyFor(group.title, item);
                    const isChecked = Boolean(checked[key]);

                    return (
                      <label className={`qa-check-row ${isChecked ? "done" : ""}`} key={key}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggle(group.title, item)}
                        />
                        <span>{item}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <div className="card qa-notes-card">
          <h3>QA Notes</h3>
          <p className="muted-text">Track bugs, weird behavior, or staff feedback here while testing.</p>
          <textarea
            rows={8}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Example: Mobile dashboard looks good. Registry search works. Need to retest staff delete after backend redeploy..."
          />
        </div>
      </section>
    </RequireDiscord>
  );
}

function ActivityDashboard({ discordId }: { discordId: string }) {
  const [events, setEvents] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [eventType, setEventType] = useState("all");
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");

  async function loadActivity() {
    if (!discordId) return;

    setLoading(true);
    setMessage("");

    try {
      const params = new URLSearchParams({ limit: "120" });
      if (eventType !== "all") params.set("event_type", eventType);
      if (status !== "all") params.set("status", status);

      const data = await apiFetch(`/api/activity-log?${params.toString()}`, {}, discordId);
      setEvents(data.events || []);
      if (data.message) setMessage(data.message);
    } catch (error: any) {
      setMessage(error.message || "Could not load activity.");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadActivity();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, eventType, status]);

  function formatDate(value: string | null | undefined) {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
  }

  function eventIcon(type: string) {
    const normalized = String(type || "").toLowerCase();

    if (normalized.includes("oc")) return <UserRound size={18} />;
    if (normalized.includes("skill")) return <Sparkles size={18} />;
    if (normalized.includes("stat")) return <Calculator size={18} />;
    if (normalized.includes("xp")) return <Sparkles size={18} />;
    if (normalized.includes("currency")) return <Package size={18} />;
    return <ClipboardList size={18} />;
  }

  function prettyText(value: string) {
    return String(value || "info").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function statusClass(value: string) {
    const normalized = String(value || "").toLowerCase();
    if (["approved", "complete", "completed", "created", "restored"].includes(normalized)) return "approved";
    if (["denied", "deleted", "archived", "rejected"].includes(normalized)) return "denied";
    if (["pending", "submitted", "open"].includes(normalized)) return "pending";
    return "info";
  }

  const visibleEvents = events.filter((event) => {
    const query = search.trim().toLowerCase();
    if (!query) return true;

    const haystack = [
      event.label,
      event.event_type,
      event.status,
      event.character_name,
      event.character_id,
      event.actor_id,
      event.note,
      event.source,
    ].join(" ").toLowerCase();

    return haystack.includes(query);
  });

  const eventTypes = Array.from(new Set(events.map((event) => event.event_type).filter(Boolean))).sort();
  const statuses = Array.from(new Set(events.map((event) => event.status).filter(Boolean))).sort();

  return (
    <RequireDiscord discordId={discordId}>
      <section className="activity-log-page">
        <div className="card activity-log-hero">
          <div>
            <span className="activity-type-label">Recent Activity</span>
            <h2>Activity Log</h2>
            <p className="muted-text">
              Track OC registration, staff requests, XP/currency changes, and recent system activity in one place.
            </p>
          </div>
          <button className="ghost" onClick={loadActivity} disabled={loading}>
            <RefreshCw size={16} /> {loading ? "Loading..." : "Refresh"}
          </button>
        </div>

        <div className="card activity-log-filters">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search activity..."
          />

          <select value={eventType} onChange={(event) => setEventType(event.target.value)}>
            <option value="all">All event types</option>
            {eventTypes.map((type) => (
              <option value={type} key={type}>
                {prettyText(type)}
              </option>
            ))}
          </select>

          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">All statuses</option>
            {statuses.map((item) => (
              <option value={item} key={item}>
                {prettyText(item)}
              </option>
            ))}
          </select>
        </div>

        {message ? <p className="message">{message}</p> : null}

        <div className="activity-log-list">
          {visibleEvents.length === 0 ? (
            <div className="card activity-empty-state">
              <strong>No activity found.</strong>
              <p className="muted-text">Try refreshing, clearing filters, or performing an action like registering an OC.</p>
            </div>
          ) : null}

          {visibleEvents.map((event, index) => (
            <div className="card activity-log-row" key={`${event.source}-${event.created_at}-${index}`}>
              <div className={`activity-log-icon ${statusClass(event.status)}`}>{eventIcon(event.event_type)}</div>

              <div className="activity-log-main">
                <div className="activity-log-title-row">
                  <div>
                    <strong>{event.label || prettyText(event.event_type)}</strong>
                    <span>{prettyText(event.event_type)} • {formatDate(event.created_at)}</span>
                  </div>
                  <em className={`activity-status-pill ${statusClass(event.status)}`}>{prettyText(event.status)}</em>
                </div>

                <div className="activity-log-meta">
                  {event.character_name ? <span>OC: {event.character_name}</span> : null}
                  {!event.character_name && event.character_id ? <span>OC ID: {event.character_id}</span> : null}
                  {event.actor_id ? <span>Actor: {event.actor_id}</span> : null}
                  {event.amount !== null && event.amount !== undefined ? <span>Amount: {String(event.amount)}</span> : null}
                  {event.source ? <span>Source: {event.source}</span> : null}
                </div>

                {event.note ? <p className="activity-log-note">{event.note}</p> : null}
              </div>
            </div>
          ))}
        </div>
      </section>
    </RequireDiscord>
  );
}

function RpHubDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
}) {
  const [data, setData] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [sceneFilter, setSceneFilter] = useState<"active" | "closed" | "claims">("active");

  async function load() {
    setMessage("");

    const suffix = selectedCharacterId
      ? `?character_id=${encodeURIComponent(selectedCharacterId)}`
      : "";

    const result = await apiFetch(`/api/rp/me${suffix}`, {}, discordId);
    setData(result);
  }

  useEffect(() => {
    if (discordId) {
      load().catch((error) => setMessage(error.message));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, selectedCharacterId]);

  const scenes = sceneFilter === "closed" ? data?.closed_scenes || [] : data?.active_scenes || [];
  const claims = data?.xp_claims || [];
  const totals = data?.totals || {};

  function statusLabel(value: string | undefined) {
    return String(value || "unknown").replaceAll("_", " ").toUpperCase();
  }

  function claimStatusClass(value: string | undefined) {
    const normalized = String(value || "").toLowerCase();

    if (normalized.includes("approved") || normalized.includes("paid")) {
      return "good";
    }

    if (normalized.includes("denied") || normalized.includes("error")) {
      return "bad";
    }

    return "";
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid rp-hub-grid">
        <div className="card">
          <div className="card-title-row">
            <div>
              <h2>RP Hub</h2>
              <p className="muted-text">
                Track the scenes, posts, XP claims, and Discord jump links tied to your OCs.
              </p>
            </div>
            <button className="ghost" onClick={load}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>

          <CharacterSelect
            discordId={discordId}
            selectedCharacterId={selectedCharacterId}
            setSelectedCharacterId={setSelectedCharacterId}
            label="Filter by OC"
          />

          {message && <p className="message">{message}</p>}

          <div className="summary">
            <div>
              <span>Active RPs</span>
              <strong>{totals.active_scene_count ?? 0}</strong>
            </div>
            <div>
              <span>Posts</span>
              <strong>{totals.post_count ?? 0}</strong>
            </div>
            <div>
              <span>Words</span>
              <strong>{totals.word_count ?? 0}</strong>
            </div>
          </div>

          <div className="summary">
            <div>
              <span>Estimated XP</span>
              <strong>{totals.estimated_xp ?? 0}</strong>
            </div>
            <div>
              <span>Approved XP</span>
              <strong>{totals.approved_xp ?? 0}</strong>
            </div>
            <div>
              <span>Closed RPs</span>
              <strong>{totals.closed_scene_count ?? 0}</strong>
            </div>
          </div>
        </div>

        <div className="card rp-recent-posts-card">
          <h2>Recent Posts</h2>

          <div className="item-list scroll-list">
            {(data?.recent_posts || []).length === 0 ? <p>No tracked posts found yet.</p> : null}

            {(data?.recent_posts || []).slice(0, 8).map((post: any) => (
              <div className="request-card" key={post.post_id}>
                <div>
                  <h3>{post.character_name}</h3>
                  <p>
                    {post.word_count} words • {new Date(post.posted_at).toLocaleString()}
                  </p>
                  {post.content_preview ? <small>{post.content_preview}</small> : null}
                </div>

                {post.discord_url ? (
                  <a href={post.discord_url} target="_blank" rel="noreferrer">
                    Open post
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        <div className="card rp-main-panel">
          <div className="card-title-row">
            <h2>
              {sceneFilter === "claims"
                ? "XP Claims"
                : sceneFilter === "closed"
                  ? "Closed RPs"
                  : "Active RPs"}
            </h2>

            <div className="actions">
              <button
                className={sceneFilter === "active" ? "" : "ghost"}
                onClick={() => setSceneFilter("active")}
              >
                Active
              </button>
              <button
                className={sceneFilter === "closed" ? "" : "ghost"}
                onClick={() => setSceneFilter("closed")}
              >
                Closed
              </button>
              <button
                className={sceneFilter === "claims" ? "" : "ghost"}
                onClick={() => setSceneFilter("claims")}
              >
                Claims
              </button>
            </div>
          </div>

          {sceneFilter !== "claims" ? (
            <div className="item-list">
              {scenes.length === 0 ? <p>No scenes found for this filter.</p> : null}

              {scenes.map((scene: any) => (
                <div className="request-card rp-scene-card" key={scene.scene_id}>
                  <div>
                    <h3>{scene.title}</h3>
                    <p>
                      {statusLabel(scene.status)} • {scene.scene_type || "scene"} •{" "}
                      {scene.xp_eligible ? "XP eligible" : "No XP"}
                    </p>

                    {scene.event?.title ? (
                      <p>
                        <strong>Event:</strong> {scene.event.title}
                      </p>
                    ) : null}

                    <p>
                      Your posts: {scene.my_post_count || 0} • Your words:{" "}
                      {scene.my_word_count || 0}
                    </p>

                    {scene.latest_post?.content_preview ? (
                      <small>Latest: {scene.latest_post.content_preview}</small>
                    ) : null}
                  </div>

                  <div className="actions">
                    {scene.discord_url ? (
                      <a href={scene.discord_url} target="_blank" rel="noreferrer">
                        Open thread
                      </a>
                    ) : null}

                    {scene.latest_post?.discord_url ? (
                      <a href={scene.latest_post.discord_url} target="_blank" rel="noreferrer">
                        Latest post
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="item-list">
              {claims.length === 0 ? <p>No RP XP claims found yet.</p> : null}

              {claims.map((claim: any) => (
                <div className="request-card rp-claim-card" key={claim.claim_id}>
                  <div>
                    <h3>{claim.character_name}</h3>
                    <p>
                      {claim.claim_type} • {claim.word_count} words • {claim.post_count} posts
                    </p>
                    <p>
                      Estimated: {claim.estimated_xp} XP • Approved:{" "}
                      {claim.approved_xp ?? "—"} XP
                    </p>
                    <p>
                      Status:{" "}
                      <strong className={claimStatusClass(claim.status)}>
                        {statusLabel(claim.status)}
                      </strong>{" "}
                      • Payout:{" "}
                      <strong className={claimStatusClass(claim.payout_status)}>
                        {statusLabel(claim.payout_status)}
                      </strong>
                    </p>

                    {claim.scene?.title ? (
                      <small>Scene: {claim.scene.title}</small>
                    ) : null}

                    {claim.review_reason ? <small>Review: {claim.review_reason}</small> : null}
                    {claim.payout_error ? <small className="bad">Payout error: {claim.payout_error}</small> : null}
                  </div>

                  {claim.scene?.discord_url ? (
                    <a href={claim.scene.discord_url} target="_blank" rel="noreferrer">
                      Open scene
                    </a>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </RequireDiscord>
  );
}

function CompanionDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
}) {
  const permissions = usePermissions(discordId);
  const [data, setData] = useState<any>(null);
  const [form, setForm] = useState<any>({
    beast_name: "",
    beast_type: "utility",
    description: "",
    bond_notes: "",
    image_url: "",
    xp: 0,
    base_strength: 5,
    base_dexterity: 5,
    base_stamina: 5,
    base_magic_affinity: 5,
    base_mana: 5,
    current_skills: "",
    notes: "",
  });
  const [skillRequestForm, setSkillRequestForm] = useState<any>({ skill_key: "", note: "" });
  const [catalogSkills, setCatalogSkills] = useState<any[]>([]);
  const [showSkillPicker, setShowSkillPicker] = useState(false);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState("");
  const [skillMessage, setSkillMessage] = useState("");

  async function loadCompanion(characterId = selectedCharacterId) {
    setMessage("");
    if (!characterId) return;
    const result = await apiFetch(`/api/companions/${characterId}`, {}, discordId);
    setData(result);
    setForm((current: any) => ({ ...current, ...(result.beast || {}) }));
  }

  async function loadCatalogSkills() {
    try {
      const result = await apiFetch("/api/staff/source-beast-skills", {}, discordId);
      setCatalogSkills((result.skills || []).filter((s: any) => s.is_active && s.is_purchasable));
    } catch (_) {
      setCatalogSkills([]);
    }
  }

  useEffect(() => {
    if (discordId && selectedCharacterId) {
      loadCompanion(selectedCharacterId).catch((error) => setMessage(error.message));
      loadCatalogSkills().catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, selectedCharacterId]);

  async function saveCompanion() {
    setMessage("");
    try {
      const result = await apiFetch(
        `/api/companions/${selectedCharacterId}`,
        { method: "PUT", body: JSON.stringify(form) },
        discordId
      );
      setMessage(result.message || "LC Unit saved.");
      setEditing(false);
      await loadCompanion(selectedCharacterId);
    } catch (error: any) {
      setMessage(error.message || "Could not save LC Unit.");
    }
  }

  async function requestBeastSkill() {
    setSkillMessage("");
    if (!skillRequestForm.skill_key) { setSkillMessage("Select a skill first."); return; }
    try {
      const result = await apiFetch(
        `/api/companions/${selectedCharacterId}/skill-request`,
        { method: "POST", body: JSON.stringify(skillRequestForm) },
        discordId
      );
      setSkillMessage(result.message || "Skill request submitted.");
      setSkillRequestForm({ skill_key: "", note: "" });
      setShowSkillPicker(false);
      await loadCompanion(selectedCharacterId);
    } catch (error: any) {
      setSkillMessage(error.message || "Could not submit skill request.");
    }
  }

  async function saveBaseStats() {
    setMessage("");
    if (!permissions?.is_staff) return;
    try {
      const result = await apiFetch(
        `/api/companions/${selectedCharacterId}/base-stats`,
        { method: "PUT", body: JSON.stringify(form) },
        discordId
      );
      setMessage(result.message || "Base stats updated.");
      await loadCompanion(selectedCharacterId);
    } catch (error: any) {
      setMessage(error.message || "Could not update base stats.");
    }
  }

  const computed = data?.computed_stats || {};
  const rules = data?.type_rules || {};
  const wallet = data?.wallet || {};
  const beastSkillRequests: any[] = data?.beast_skill_requests || [];
  const beast = data?.beast || {};
  const isStaff = Boolean(permissions?.is_staff);

  const acquiredRequests = beastSkillRequests.filter(
    (r: any) => ["approved", "accepted"].includes(String(r.status || "").toLowerCase())
  );
  const pendingRequests = beastSkillRequests.filter(
    (r: any) => String(r.status || "").toLowerCase() === "pending"
  );
  const acquiredSkillKeys = new Set(acquiredRequests.map((r: any) => r.skill_key));
  const pendingSkillKeys = new Set(pendingRequests.map((r: any) => r.skill_key));
  const availableSkills = catalogSkills.filter(
    (s: any) => !acquiredSkillKeys.has(s.skill_key) && !pendingSkillKeys.has(s.skill_key)
  );

  const statLabels: [string, string][] = [
    ["strength", "Strength"],
    ["dexterity", "Dexterity"],
    ["stamina", "Stamina"],
    ["magic_affinity", "Magic Affinity"],
    ["mana", "Mana"],
  ];

  const beastTypeLabel = (t: string) =>
    t === "combat" ? "Combat" : t === "mount" ? "Mount" : "Utility";

  return (
    <RequireDiscord discordId={discordId}>
      <section className="request-workflow-page">
        <div className="card request-workflow-hero">
          <div>
            <span className="activity-type-label">Loyal Companion</span>
            <h2>Companion</h2>
            <p className="muted-text">Your OC's Source Beast — identity, stats, and skills all in one place.</p>
          </div>
          <button className="ghost" onClick={() => loadCompanion()}><RefreshCw size={16} /> Refresh</button>
        </div>

        <CharacterSelect discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />
        {message ? <p className="message">{message}</p> : null}

        {data && !data.eligible ? (
          <div className="card">
            <h3>No Loyal Companion Trait</h3>
            <p className="muted-text">This OC doesn't have the Loyal Companion trait. Switch to an eligible OC or ask staff to grant the trait.</p>
          </div>
        ) : null}

        {data?.eligible ? (
          <section className="grid oc-dashboard-grid">

            <div className="card">
              <div className="card-title-row">
                <h2>Beast Dashboard</h2>
                <button className="ghost" onClick={() => setEditing(!editing)}>
                  {editing ? <><X size={14} /> Cancel</> : <><Save size={14} /> Edit</>}
                </button>
              </div>

              {!editing ? (
                <>
                  <h3>{beast.beast_name || "Unnamed Beast"}</h3>
                  <div className="stat-strip"><span>Type</span><strong>{beastTypeLabel(beast.beast_type || "utility")}</strong></div>
                  <div className="stat-strip"><span>Beast XP</span><strong>{beast.xp ?? 0}</strong></div>
                  {beast.description ? <p className="muted-text" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>{beast.description}</p> : null}
                  {beast.bond_notes ? <p className="muted-text" style={{ marginTop: "0.5rem", fontSize: "0.85rem", fontStyle: "italic" }}>"{beast.bond_notes}"</p> : null}
                </>
              ) : (
                <div className="request-actions-panel">
                  <label><span>Beast name</span><input value={form.beast_name || ""} onChange={(e) => setForm((c: any) => ({ ...c, beast_name: e.target.value }))} placeholder="Vespera, Ricardo, Nero…" /></label>
                  <label><span>Beast type</span>
                    <select value={form.beast_type || "utility"} onChange={(e) => setForm((c: any) => ({ ...c, beast_type: e.target.value }))}>
                      <option value="combat">Combat</option>
                      <option value="mount">Mount</option>
                      <option value="utility">Utility</option>
                    </select>
                  </label>
                  <label><span>Image URL</span><input value={form.image_url || ""} onChange={(e) => setForm((c: any) => ({ ...c, image_url: e.target.value }))} placeholder="Optional portrait link" /></label>
                  <label><span>Description</span><textarea rows={3} value={form.description || ""} onChange={(e) => setForm((c: any) => ({ ...c, description: e.target.value }))} placeholder="Appearance and behavior" /></label>
                  <label><span>Bond notes</span><textarea rows={2} value={form.bond_notes || ""} onChange={(e) => setForm((c: any) => ({ ...c, bond_notes: e.target.value }))} placeholder="How did your OC encounter this beast?" /></label>
                  <label><span>Notes</span><textarea rows={2} value={form.notes || ""} onChange={(e) => setForm((c: any) => ({ ...c, notes: e.target.value }))} placeholder="Staff or sheet notes" /></label>
                  <div className="actions"><button onClick={saveCompanion}><Save size={16} /> Save</button></div>
                </div>
              )}

              <h3 style={{ marginTop: "1.25rem" }}>Beast Stats</h3>
              <p className="muted-text" style={{ fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                Final = base + 10% of OC stat.{!isStaff ? " Base stats are set by staff." : ""}
              </p>
              <div className="mini-stat-grid">
                {statLabels.map(([key, label]) => (
                  <div key={key} className="mini-stat">
                    <span>{label}</span>
                    <strong>{computed[key]?.final ?? "—"}</strong>
                    <small className="muted-text" style={{ fontSize: "0.7rem" }}>{computed[key]?.base ?? 5}+{computed[key]?.modifier ?? 0}</small>
                  </div>
                ))}
              </div>

              {isStaff ? (
                <>
                  <h3 style={{ marginTop: "1.25rem" }}>Edit Base Stats</h3>
                  <div className="mini-stat-grid">
                    {statLabels.map(([key, label]) => (
                      <div key={key} className="mini-stat">
                        <span>{label}</span>
                        <input type="number" min="0" style={{ width: "100%", textAlign: "center" }}
                          value={form[`base_${key}`] ?? 5}
                          onChange={(e) => setForm((c: any) => ({ ...c, [`base_${key}`]: Number(e.target.value) }))} />
                      </div>
                    ))}
                  </div>
                  <div className="request-actions-panel" style={{ marginTop: "0.75rem" }}>
                    <label><span>Beast XP</span><input type="number" min="0" value={form.xp ?? 0} onChange={(e) => setForm((c: any) => ({ ...c, xp: Number(e.target.value) }))} /></label>
                    <div className="actions"><button onClick={saveBaseStats}><Save size={16} /> Update base stats</button></div>
                  </div>
                </>
              ) : null}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

              <div className="card oc-skills-card">
                <div className="card-title-row">
                  <div>
                    <h2>Beast Skills</h2>
                    <p className="muted-text">Skills your companion has or has requested.</p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span className="pill good">{acquiredRequests.length} acquired</span>
                    <div className="muted-text" style={{ fontSize: "0.75rem", marginTop: "4px" }}>{wallet.available_xp ?? "—"} XP available</div>
                  </div>
                </div>

                {acquiredRequests.length > 0 ? (
                  <div className="owned-skill-group">
                    <div className="owned-skill-group-heading"><h3>Acquired</h3><span>{acquiredRequests.length}</span></div>
                    <div className="owned-skill-list">
                      {acquiredRequests.map((req: any) => (
                        <div className="owned-skill-row" key={req.request_id || req.skill_key}>
                          <div><strong>{req.skill_name || req.skill_key}</strong></div>
                          <div className="owned-skill-meta"><span>Beast Skill</span><span>{req.cost ?? 0} XP</span></div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="muted-text" style={{ marginTop: "0.5rem" }}>No beast skills acquired yet.</p>
                )}

                {pendingRequests.length > 0 ? (
                  <div className="oc-pending-skills">
                    <h3>Pending Requests</h3>
                    <div className="owned-skill-list">
                      {pendingRequests.map((req: any) => (
                        <div className="owned-skill-row pending" key={req.request_id || req.skill_key}>
                          <div><strong>{req.skill_name || req.skill_key}</strong></div>
                          <div className="owned-skill-meta"><span>Pending</span><span>{req.cost ?? 0} XP</span></div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {skillMessage ? <p className="message" style={{ marginTop: "0.75rem" }}>{skillMessage}</p> : null}

                {!showSkillPicker ? (
                  <div style={{ marginTop: "1rem" }}>
                    <button onClick={() => { setShowSkillPicker(true); setSkillMessage(""); }}>
                      <Plus size={16} /> Request beast skill
                    </button>
                  </div>
                ) : (
                  <div className="request-actions-panel" style={{ marginTop: "0.75rem" }}>
                    <label>
                      <span>Select skill</span>
                      <select value={skillRequestForm.skill_key} onChange={(e) => setSkillRequestForm((c: any) => ({ ...c, skill_key: e.target.value }))}>
                        <option value="">— choose a skill —</option>
                        {availableSkills.map((s: any) => (
                          <option key={s.skill_key} value={s.skill_key}>{s.name} · {s.beast_skill_type} T{s.tier} · {s.cost} XP</option>
                        ))}
                      </select>
                    </label>
                    {skillRequestForm.skill_key ? (() => {
                      const skill = catalogSkills.find((s: any) => s.skill_key === skillRequestForm.skill_key);
                      return skill ? (
                        <div className="card">
                          <p><strong>{skill.name}</strong> — {skill.beast_skill_type} · Tier {skill.tier} · {skill.cost} XP</p>
                          {skill.description ? <p className="muted-text">{skill.description}</p> : null}
                          {skill.effects ? <p><strong>Effect:</strong> {skill.effects}</p> : null}
                        </div>
                      ) : null;
                    })() : null}
                    <label><span>Note to staff (optional)</span><input value={skillRequestForm.note} onChange={(e) => setSkillRequestForm((c: any) => ({ ...c, note: e.target.value }))} placeholder="Any context for staff" /></label>
                    <div className="actions">
                      <button onClick={requestBeastSkill}><Send size={16} /> Submit request</button>
                      <button className="ghost" onClick={() => { setShowSkillPicker(false); setSkillMessage(""); setSkillRequestForm({ skill_key: "", note: "" }); }}>Cancel</button>
                    </div>
                  </div>
                )}
              </div>

              <div className="card">
                <h2>Role Rules</h2>
                <p className="muted-text">Skill tier limits for a <strong>{beastTypeLabel(beast.beast_type || "utility")}</strong> type beast.</p>
                <div className="summary vertical" style={{ marginTop: "0.75rem" }}>
                  <div><span>Combat tier max</span><strong>{rules.combat ?? "—"}</strong></div>
                  <div><span>Mount tier max</span><strong>{rules.mount ?? "—"}</strong></div>
                  <div><span>Utility tier max</span><strong>{rules.utility ?? "—"}</strong></div>
                  <div><span>Own-type cap</span><strong>{rules.own_type_skill_cap_per_tier ?? 3} / tier</strong></div>
                  <div><span>Non-type cap</span><strong>{rules.non_type_skill_cap_per_tier ?? 2} / tier</strong></div>
                </div>
              </div>

            </div>
          </section>
        ) : null}
      </section>
    </RequireDiscord>
  );
}
function MissionBoardDashboard({
  discordId,
  selectedCharacterId,
  setSelectedCharacterId,
}: {
  discordId: string;
  selectedCharacterId: string;
  setSelectedCharacterId: (id: string) => void;
}) {
  const permissions = usePermissions(discordId);
  const [missions, setMissions] = useState<any[]>([]);
  const [characters, setCharacters] = useState<any[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState("");
  const [signups, setSignups] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [signupContext, setSignupContext] = useState<any>(null);
  const [signupForm, setSignupForm] = useState({
    guild_name: "",
    bst: "",
    other_active_missions: "",
    note: "",
  });
  const [missionForm, setMissionForm] = useState({
    title: "",
    status: "open",
    description: "",
    reward: "",
    location: "",
    difficulty: "",
    party_size: "4",
    min_bst: "",
    max_bst: "",
    guild_policy: "open",
    priority_guilds: "",
    restricted_guilds: "",
    bonus_pay: "",
    priority_window_hours: "24",
  });

  async function loadMissions() {
    setMessage("");
    const data = await apiFetch("/api/missions", {}, discordId);
    setMissions(data.missions || []);
  }

  async function loadCharacters() {
    const data = await apiFetch("/api/characters/mine", {}, discordId);
    const rows = Array.isArray(data) ? data : data.characters || data.data || [];
    setCharacters(rows);

    if (!selectedCharacterId && rows[0]?.character_id && shouldAutoSelectOc()) {
      setSelectedCharacterId(rows[0].character_id);
    }
  }

  async function loadSignupContext(characterId = selectedCharacterId) {
    if (!characterId) {
      setSignupContext(null);
      return;
    }

    try {
      const data = await apiFetch(`/api/missions/context/${characterId}`, {}, discordId);
      const context = data.context || {};
      setSignupContext(context);

      setSignupForm((current) => ({
        ...current,
        guild_name: current.guild_name || context.default_guild || "",
        bst: current.bst || String(context.bst ?? ""),
        other_active_missions:
          current.other_active_missions || context.other_active_missions_text || "",
      }));
    } catch (error: any) {
      console.warn("Could not load mission signup context", error);
    }
  }

  async function loadSignups(missionId = selectedMissionId) {
    if (!missionId || !permissions?.is_staff) return;
    const data = await apiFetch(`/api/missions/${missionId}/signups`, {}, discordId);
    setSignups(data.signups || []);
  }

  useEffect(() => {
    if (discordId) {
      loadMissions().catch((error) => setMessage(error.message));
      loadCharacters().catch(() => {});
      if (selectedCharacterId) {
        loadSignupContext(selectedCharacterId).catch(() => {});
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  async function createMission() {
    setMessage("");
    try {
      const data = await apiFetch(
        "/api/missions",
        {
          method: "POST",
          body: JSON.stringify({
            ...missionForm,
            priority_guilds: missionForm.priority_guilds,
            restricted_guilds: missionForm.restricted_guilds,
          }),
        },
        discordId
      );
      setMessage(data.message || "Mission created.");
      setMissionForm((current) => ({
        ...current,
        title: "",
        description: "",
        reward: "",
        location: "",
        bonus_pay: "",
      }));
      await loadMissions();
    } catch (error: any) {
      setMessage(error.message || "Could not create mission.");
    }
  }

  async function signup(missionId: string) {
    setMessage("");

    if (!selectedCharacterId) {
      setMessage("Choose an OC first.");
      return;
    }

    if (!signupForm.guild_name.trim()) {
      setMessage("Guild is required for mission signup.");
      return;
    }

    try {
      const data = await apiFetch(
        `/api/missions/${missionId}/signup`,
        {
          method: "POST",
          body: JSON.stringify({
            character_id: selectedCharacterId,
            guild_name: signupForm.guild_name,
            bst: signupForm.bst,
            other_active_missions: signupForm.other_active_missions,
            note: signupForm.note,
          }),
        },
        discordId
      );
      setMessage(data.message || "Mission signup submitted.");
      setSignupForm((current) => ({ ...current, other_active_missions: "", note: "" }));
      await loadMissions();
    } catch (error: any) {
      setMessage(error.message || "Could not sign up.");
    }
  }

  async function updateSignupStatus(signupId: string, status: string) {
    setMessage("");
    try {
      const data = await apiFetch(
        `/api/missions/signups/${signupId}`,
        { method: "PATCH", body: JSON.stringify({ status }) },
        discordId
      );
      setMessage(data.message || "Signup updated.");
      await loadSignups();
    } catch (error: any) {
      setMessage(error.message || "Could not update signup.");
    }
  }

  function guildList(value: any) {
    if (Array.isArray(value)) return value.join(", ");
    return String(value || "");
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="request-workflow-page">
        <div className="card request-workflow-hero">
          <div>
            <span className="activity-type-label">Mission Board</span>
            <h2>Missions</h2>
            <p className="muted-text">
              Browse mission openings, sign up with the standard template, and track priority or restricted placements.
            </p>
          </div>
          <button className="ghost" onClick={loadMissions}>
            <RefreshCw size={16} /> Refresh Missions
          </button>
        </div>

        {message ? <p className="message">{message}</p> : null}

        <div className="card">
          <h3>Mission Signup Template</h3>
          <p className="muted-text">
            Select your OC once, fill in the template fields, then click Sign Up on the mission you want.
          </p>

          <div className="request-actions-panel">
            <label>
              <span>OC</span>
              <select
                value={selectedCharacterId}
                onChange={(event) => {
                  const nextCharacterId = event.target.value;
                  setSelectedCharacterId(nextCharacterId);
                  setSignupForm((current) => ({
                    ...current,
                    guild_name: "",
                    bst: "",
                    other_active_missions: "",
                  }));
                  loadSignupContext(nextCharacterId);
                }}
              >
                <option value="">Select an OC</option>
                {characters.map((character: any) => (
                  <option key={character.character_id} value={character.character_id}>
                    {character.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Guild</span>
              <input
                value={signupForm.guild_name}
                onChange={(event) => setSignupForm((current) => ({ ...current, guild_name: event.target.value }))}
                placeholder="Guild name"
              />
            </label>

            <label>
              <span>BST</span>
              <input
                type="number"
                value={signupForm.bst}
                onChange={(event) => setSignupForm((current) => ({ ...current, bst: event.target.value }))}
                placeholder="Total of all core stats"
              />
            </label>

            <label>
              <span>Other Active Missions</span>
              <textarea
                rows={2}
                value={signupForm.other_active_missions}
                onChange={(event) => setSignupForm((current) => ({ ...current, other_active_missions: event.target.value }))}
                placeholder="List active missions or write None."
              />
            </label>

            <label>
              <span>Extra Note</span>
              <textarea
                rows={2}
                value={signupForm.note}
                onChange={(event) => setSignupForm((current) => ({ ...current, note: event.target.value }))}
                placeholder="Optional."
              />
            </label>
          </div>

          {signupContext ? (
            <div className="request-note-block">
              <span>Keystone Auto-Check</span>
              <p><strong>Name:</strong> {signupContext.character_name || "—"}</p>
              <p><strong>Guild:</strong> {signupForm.guild_name || signupContext.default_guild || "—"}</p>
              <p><strong>EXP:</strong> {signupContext.exp_label || `${signupForm.bst || "0"} BST`}</p>
              <p><strong>Other Active Missions:</strong> {signupForm.other_active_missions || signupContext.other_active_missions_text || "None"}</p>
              <p>
                <strong>Traits with Modifiers:</strong>{" "}
                {(signupContext.traits_with_modifiers || []).length
                  ? signupContext.traits_with_modifiers.map((trait: any) => trait.name || trait.slug).join(", ")
                  : "None detected"}
              </p>
              <p>
                <strong>Skills with Modifiers:</strong>{" "}
                {(signupContext.skills_with_modifiers || []).length
                  ? signupContext.skills_with_modifiers.map((skill: any) => skill.name || skill.skill_key).join(", ")
                  : "None detected"}
              </p>
            </div>
          ) : null}
        </div>

        {permissions?.is_staff ? (
          <div className="card">
            <span className="activity-type-label">Staff</span>
            <h3>Create Mission</h3>
            <div className="request-actions-panel">
              <label>
                <span>Title</span>
                <input value={missionForm.title} onChange={(event) => setMissionForm((current) => ({ ...current, title: event.target.value }))} />
              </label>

              <label>
                <span>Location</span>
                <input value={missionForm.location} onChange={(event) => setMissionForm((current) => ({ ...current, location: event.target.value }))} />
              </label>

              <label>
                <span>Difficulty</span>
                <input value={missionForm.difficulty} onChange={(event) => setMissionForm((current) => ({ ...current, difficulty: event.target.value }))} />
              </label>

              <label>
                <span>Party Size</span>
                <input type="number" value={missionForm.party_size} onChange={(event) => setMissionForm((current) => ({ ...current, party_size: event.target.value }))} />
              </label>

              <label>
                <span>Min BST</span>
                <input type="number" value={missionForm.min_bst} onChange={(event) => setMissionForm((current) => ({ ...current, min_bst: event.target.value }))} />
              </label>

              <label>
                <span>Max BST</span>
                <input type="number" value={missionForm.max_bst} onChange={(event) => setMissionForm((current) => ({ ...current, max_bst: event.target.value }))} />
              </label>

              <label>
                <span>Placement Rule</span>
                <select value={missionForm.guild_policy} onChange={(event) => setMissionForm((current) => ({ ...current, guild_policy: event.target.value }))}>
                  <option value="open">Open to all</option>
                  <option value="priority">Priority guilds first 24 hours</option>
                  <option value="restricted">Restricted guilds only</option>
                </select>
              </label>

              <label>
                <span>Priority Guilds</span>
                <input value={missionForm.priority_guilds} onChange={(event) => setMissionForm((current) => ({ ...current, priority_guilds: event.target.value }))} placeholder="Comma separated" />
              </label>

              <label>
                <span>Restricted Guilds</span>
                <input value={missionForm.restricted_guilds} onChange={(event) => setMissionForm((current) => ({ ...current, restricted_guilds: event.target.value }))} placeholder="Comma separated" />
              </label>

              <label>
                <span>Bonus Pay</span>
                <input value={missionForm.bonus_pay} onChange={(event) => setMissionForm((current) => ({ ...current, bonus_pay: event.target.value }))} placeholder="Example: +25% for Guild members" />
              </label>

              <label>
                <span>Reward</span>
                <textarea rows={2} value={missionForm.reward} onChange={(event) => setMissionForm((current) => ({ ...current, reward: event.target.value }))} />
              </label>

              <label>
                <span>Description</span>
                <textarea rows={4} value={missionForm.description} onChange={(event) => setMissionForm((current) => ({ ...current, description: event.target.value }))} />
              </label>

              <div className="actions">
                <button onClick={createMission}>
                  <ShieldCheck size={16} /> Create Mission
                </button>
              </div>
            </div>
          </div>
        ) : null}

        <div className="request-card-list">
          {missions.length === 0 ? (
            <div className="card request-empty-state">
              <strong>No missions posted yet.</strong>
              <p className="muted-text">Check back once staff posts mission openings.</p>
            </div>
          ) : null}

          {missions.map((mission: any) => (
            <div className="card request-review-card" key={mission.mission_id}>
              <div className="request-review-top">
                <div>
                  <span className="activity-type-label">{mission.guild_policy || "open"} mission</span>
                  <h3>{mission.title}</h3>
                  <p className="muted-text">
                    {mission.location || "Location TBA"} - {mission.difficulty || "Difficulty TBA"}
                  </p>
                </div>
                <em className={`request-status-pill ${mission.status === "open" ? "approved" : "pending"}`}>
                  {mission.status}
                </em>
              </div>

              {mission.description ? <p>{mission.description}</p> : null}
              {mission.reward ? <p><strong>Reward:</strong> {mission.reward}</p> : null}
              {mission.bonus_pay ? <p><strong>Bonus Pay:</strong> {mission.bonus_pay}</p> : null}

              <div className="request-meta-grid">
                <div><span>Party Size</span><strong>{mission.party_size || "—"}</strong></div>
                <div><span>BST Range</span><strong>{mission.min_bst || "—"} - {mission.max_bst || "—"}</strong></div>
                <div><span>Priority</span><strong>{guildList(mission.priority_guilds) || "None"}</strong></div>
                <div><span>Restricted</span><strong>{guildList(mission.restricted_guilds) || "None"}</strong></div>
              </div>

              <div className="actions">
                <button onClick={() => signup(mission.mission_id)}>
                  <Send size={16} /> Sign Up
                </button>

                {permissions?.is_staff ? (
                  <button className="ghost" onClick={() => { setSelectedMissionId(mission.mission_id); loadSignups(mission.mission_id); }}>
                    <ClipboardList size={16} /> View Signups
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        {permissions?.is_staff && selectedMissionId ? (
          <div className="card">
            <h3>Mission Signups</h3>
            <div className="request-card-list">
              {signups.length === 0 ? <p className="muted-text">No signups for this mission yet.</p> : null}
              {signups.map((signup: any) => (
                <div className="request-note-block" key={signup.signup_id}>
                  <span>{signup.character_name} - {signup.guild_name} - BST {signup.bst} - {signup.placement_group}</span>
                  <p>Other active missions: {signup.other_active_missions || "None listed."}</p>
                  <p>Status: {signup.status}</p>
                  <div className="actions">
                    <button onClick={() => updateSignupStatus(signup.signup_id, "accepted")}>Accept</button>
                    <button className="ghost" onClick={() => updateSignupStatus(signup.signup_id, "waitlisted")}>Waitlist</button>
                    <button className="danger-button" onClick={() => updateSignupStatus(signup.signup_id, "denied")}>Deny</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </RequireDiscord>
  );
}

function isOriginTraitFreeSkillRequest(request: any) {
  const raw = request?.raw || {};
  const haystack = [
    request?.reason,
    request?.staff_note,
    request?.summary,
    request?.title,
    raw?.request_source,
    raw?.source,
    raw?.source_type,
    raw?.submitter_note,
    raw?.reason,
    raw?.notes,
    raw?.note,
    raw?.staff_note,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return [
    "origin / trait free skill",
    "origin/trait free skill",
    "origin trait free skill",
    "trait free skill",
    "free skill choice",
    "free skill request",
    "trait benefit",
    "origin benefit",
    "registration free skill",
    "submitted for staff review after registration",
  ].some((marker) => haystack.includes(marker));
}

function BeastSkillCatalogDashboard({ discordId }: { discordId: string }) {
  const blankSkill = { skill_key: "", name: "", beast_skill_type: "utility", tier: 1, cost: 0, action_type: "", prerequisites: "", chain: "", effects: "", description: "", source_label: "Source Beast Skill Catalog", sort_order: 0, is_active: true, is_purchasable: false };
  const [skills, setSkills] = useState<any[]>([]);
  const [form, setForm] = useState<any>(blankSkill);
  const [editingKey, setEditingKey] = useState("");
  const [message, setMessage] = useState("");
  async function loadSkills() { setMessage(""); const data = await apiFetch("/api/staff/source-beast-skills", {}, discordId); setSkills(data.skills || []); }
  useEffect(() => { if (discordId) loadSkills().catch((error) => setMessage(error.message)); }, [discordId]);
  function editSkill(skill: any) { setEditingKey(skill.skill_key); setForm({ ...blankSkill, ...skill, prerequisites: Array.isArray(skill.prerequisites) ? skill.prerequisites.join(", ") : String(skill.prerequisites || "") }); window.scrollTo({ top: 0, behavior: "smooth" }); }
  function resetForm() { setEditingKey(""); setForm(blankSkill); }
  async function saveSkill() { setMessage(""); try { const payload = { ...form, tier: Number(form.tier || 0), cost: Number(form.cost || 0), sort_order: Number(form.sort_order || 0) }; const path = editingKey ? `/api/staff/source-beast-skills/${editingKey}` : "/api/staff/source-beast-skills"; const data = await apiFetch(path, { method: editingKey ? "PUT" : "POST", body: JSON.stringify(payload) }, discordId); setMessage(data.message || "Beast Skill saved."); resetForm(); await loadSkills(); } catch (error: any) { setMessage(error.message || "Could not save Beast Skill."); } }
  async function deleteSkill(skill: any) {
    const confirmed = window.confirm(`Delete Beast Skill "${skill.name || skill.skill_key}"? This removes it from the catalog.`);
    if (!confirmed) return;

    setMessage("");
    try {
      const data = await apiFetch(
        `/api/staff/source-beast-skills/${skill.skill_key}`,
        { method: "DELETE" },
        discordId
      );
      setMessage(data.message || "Beast Skill deleted.");
      if (editingKey === skill.skill_key) resetForm();
      await loadSkills();
    } catch (error: any) {
      setMessage(error.message || "Could not delete Beast Skill.");
    }
  }

  async function toggleSkill(skill: any, patch: any) { setMessage(""); try { const data = await apiFetch(`/api/staff/source-beast-skills/${skill.skill_key}/toggle`, { method: "PATCH", body: JSON.stringify(patch) }, discordId); setMessage(data.message || "Beast Skill updated."); await loadSkills(); } catch (error: any) { setMessage(error.message || "Could not update Beast Skill."); } }
  return <StaffOnly discordId={discordId}><section className="request-workflow-page"><div className="card request-workflow-hero"><div><span className="activity-type-label">Staff Catalog</span><h2>Source Beast Skill Builder</h2><p className="muted-text">Create and edit Beast Skill definitions without touching Supabase. Purchasing stays locked until staff marks a skill purchasable.</p></div><button className="ghost" onClick={loadSkills}><RefreshCw size={16} /> Refresh</button></div>{message ? <p className="message">{message}</p> : null}<div className="card"><h3>{editingKey ? "Edit Beast Skill" : "Create Beast Skill"}</h3><div className="request-actions-panel"><label><span>Skill Name</span><input value={form.name} onChange={(event) => setForm((current: any) => ({ ...current, name: event.target.value }))} placeholder="Ravaged Strike" /></label><label><span>Internal Key</span><input value={form.skill_key} onChange={(event) => setForm((current: any) => ({ ...current, skill_key: event.target.value }))} placeholder="Auto-generated from skill name" disabled={Boolean(editingKey)} /></label><label><span>Beast Skill Type</span><select value={form.beast_skill_type} onChange={(event) => setForm((current: any) => ({ ...current, beast_skill_type: event.target.value }))}><option value="combat">Combat</option><option value="mount">Mount</option><option value="utility">Utility</option></select></label><label><span>Tier</span><input type="number" min="0" max="3" value={form.tier} onChange={(event) => setForm((current: any) => ({ ...current, tier: Number(event.target.value) }))} /></label><label><span>XP Cost</span><input type="number" min="0" value={form.cost} onChange={(event) => setForm((current: any) => ({ ...current, cost: Number(event.target.value) }))} /></label><label><span>Action Type</span><input value={form.action_type || ""} onChange={(event) => setForm((current: any) => ({ ...current, action_type: event.target.value }))} placeholder="Passive, Action, Bonus Action, Reaction" /></label><label><span>Prerequisites</span><input value={form.prerequisites || ""} onChange={(event) => setForm((current: any) => ({ ...current, prerequisites: event.target.value }))} placeholder="Choose prerequisite skills below. Keystone stores the keys automatically." /></label><label><span>Upgrade Line</span><input value={form.chain || ""} onChange={(event) => setForm((current: any) => ({ ...current, chain: event.target.value }))} placeholder="Example: Magical Attack I → Magical Attack II → Magical Attack III. Leave blank if standalone." /></label><label><span>Source Label</span><input value={form.source_label || ""} onChange={(event) => setForm((current: any) => ({ ...current, source_label: event.target.value }))} /></label><label><span>Display Order</span><input type="number" value={form.sort_order || 0} onChange={(event) => setForm((current: any) => ({ ...current, sort_order: Number(event.target.value) }))} /></label><label><span>Status</span><select value={form.is_active ? "active" : "inactive"} onChange={(event) => setForm((current: any) => ({ ...current, is_active: event.target.value === "active" }))}><option value="active">Active</option><option value="inactive">Inactive / Hidden</option></select></label><label><span>Purchasing</span><select value={form.is_purchasable ? "yes" : "no"} onChange={(event) => setForm((current: any) => ({ ...current, is_purchasable: event.target.value === "yes" }))}><option value="no">Locked / Not Purchasable</option><option value="yes">Purchasable</option></select></label><label><span>Effects</span><textarea rows={4} value={form.effects || ""} onChange={(event) => setForm((current: any) => ({ ...current, effects: event.target.value }))} placeholder="Mechanical effects, bonuses, AP/action cost, restrictions..." /></label><label><span>Description</span><textarea rows={5} value={form.description || ""} onChange={(event) => setForm((current: any) => ({ ...current, description: event.target.value }))} placeholder="Player-facing description." /></label></div><div className="actions"><button onClick={saveSkill}><Save size={16} /> {editingKey ? "Update Beast Skill" : "Create Beast Skill"}</button>{editingKey ? <button className="ghost" onClick={resetForm}>Cancel Edit</button> : null}</div></div><div className="request-card-list">{skills.length === 0 ? <div className="card request-empty-state"><strong>No Beast Skills created yet.</strong><p className="muted-text">Create the first Source Beast Skill above.</p></div> : null}{skills.map((skill: any) => <div className="card request-review-card" key={skill.skill_key}><div className="request-review-top"><div><span className="activity-type-label">{skill.beast_skill_type} • Tier {skill.tier}</span><h3>{skill.name}</h3><p className="muted-text">{skill.skill_key} • {skill.cost} Beast XP • {skill.action_type || "Action type TBA"}</p></div><em className={`request-status-pill ${skill.is_purchasable ? "approved" : "pending"}`}>{skill.is_purchasable ? "Purchasable" : "Locked"}</em></div>{skill.description ? <p>{skill.description}</p> : null}{skill.effects ? <p><strong>Effects:</strong> {skill.effects}</p> : null}<div className="actions"><button className="ghost" onClick={() => editSkill(skill)}>Edit</button><button className="ghost" onClick={() => toggleSkill(skill, { is_purchasable: !skill.is_purchasable })}>{skill.is_purchasable ? "Lock Purchasing" : "Enable Purchasing"}</button><button className="ghost" onClick={() => toggleSkill(skill, { is_active: !skill.is_active })}>{skill.is_active ? "Hide" : "Unhide"}</button><button className="danger-button" onClick={() => deleteSkill(skill)}>Delete</button></div></div>)}</div></section></StaffOnly>;
}

// ── Staff Player Lookup ──────────────────────────────────────────────────────

function StaffPlayerLookup({ discordId }: { discordId: string }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [characterId, setCharacterId] = useState("");

  // Same data as OCDashboard
  const [summary, setSummary] = useState<any>(null);
  const [ownedSkills, setOwnedSkills] = useState<any[]>([]);
  const [invData, setInvData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Item removal
  const [removeTarget, setRemoveTarget] = useState<any>(null);
  const [removeReason, setRemoveReason] = useState("");
  const [removing, setRemoving] = useState(false);

  async function searchOCs() {
    if (!query.trim()) return;
    setSearching(true); setMessage("");
    try {
      const params = new URLSearchParams({ search: query.trim(), limit: "20" });
      const data = await apiFetch(`/api/registry/characters?${params}`, {}, discordId);
      setResults(data.characters || []);
    } catch (err: any) { setMessage(err.message || "Could not search OCs."); }
    finally { setSearching(false); }
  }

  async function loadProfile(cid: string) {
    setCharacterId(cid); setResults([]); setSummary(null); setInvData(null); setOwnedSkills([]); setMessage(""); setLoading(true);
    try {
      const [summaryData, catalogData, skillData, inv] = await Promise.all([
        apiFetch(`/api/characters/${cid}/summary`, {}, discordId).catch(() => ({})),
        apiFetch("/api/skills", {}, discordId).catch(() => ({ skills: [] })),
        apiFetch(`/api/characters/${cid}/skills`, {}, discordId).catch(() => ({ owned_keys: [] })),
        apiFetch(`/api/inventory/characters/${cid}`, {}, discordId).catch(() => ({ items: [], currencies: [] })),
      ]);
      setSummary(summaryData);
      setInvData(inv);
      // Enrich skills exactly like OCDashboard does
      const catalog = catalogData.skills || [];
      const ownedKeys: string[] = skillData.owned_keys || [];
      const enriched = ownedKeys
        .map((key: string) => {
          const def = catalog.find((s: any) => s.skill_key === key);
          return { skill_key: key, ...(def || {}) };
        })
        .sort((a: any, b: any) => {
          const t = String(a.tree || "").localeCompare(String(b.tree || ""));
          if (t !== 0) return t;
          const tier = Number(a.tier ?? 0) - Number(b.tier ?? 0);
          if (tier !== 0) return tier;
          return String(a.name || a.skill_key).localeCompare(String(b.name || b.skill_key));
        });
      setOwnedSkills(enriched);
    } catch (err: any) { setMessage(err.message || "Could not load profile."); }
    finally { setLoading(false); }
  }

  async function removeItem() {
    if (!removeTarget || !removeReason.trim()) { setMessage("A staff reason is required."); return; }
    setRemoving(true); setMessage("");
    try {
      const data = await apiFetch("/api/staff/maintenance/item/remove", {
        method: "POST",
        body: JSON.stringify({ character_id: characterId, inventory_id: removeTarget.inventory_id, item_id: removeTarget.item_id, reason: removeReason }),
      }, discordId);
      setMessage(data.message || "Item removed.");
      setRemoveTarget(null); setRemoveReason("");
      // Refresh just the inventory
      const inv = await apiFetch(`/api/inventory/characters/${characterId}`, {}, discordId).catch(() => ({ items: [], currencies: [] }));
      setInvData(inv);
    } catch (err: any) { setMessage(err.message || "Could not remove item."); }
    finally { setRemoving(false); }
  }

  const groupedSkills = ownedSkills.reduce<Record<string, any[]>>((acc, skill) => {
    const tree = String(skill.tree || "Other");
    if (!acc[tree]) acc[tree] = [];
    acc[tree].push(skill);
    return acc;
  }, {});

  const items: any[] = invData?.items || [];
  const currencies: any[] = invData?.currencies || [];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>

      {/* Search bar */}
      <div className="card" style={{ display:"flex", gap:"10px", alignItems:"flex-end", flexWrap:"wrap" }}>
        <label style={{ flex:1, minWidth:"200px" }}>
          <span>Search OC or Player</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && searchOCs()} placeholder="OC name, player username..." />
        </label>
        <button onClick={searchOCs} disabled={searching} style={{ flexShrink:0 }}>
          <Search size={15} /> {searching ? "Searching..." : "Search"}
        </button>
      </div>

      {/* Search results */}
      {results.length > 0 && (
        <div className="card">
          <span className="activity-type-label">Results</span>
          <div style={{ display:"flex", flexDirection:"column", gap:"8px", marginTop:"10px" }}>
            {results.map((c: any) => (
              <button key={c.character_id || c.id} className="ghost" onClick={() => loadProfile(c.character_id || c.id)}
                style={{ textAlign:"left", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <span><strong>{c.name}</strong>{(c.owner_name || c.username) ? ` — ${c.owner_name || c.username}` : ""}</span>
                <Eye size={14} />
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && <div className="card" style={{ textAlign:"center", padding:"24px", color:"var(--muted)" }}>Loading profile...</div>}
      {message && <p className="message">{message}</p>}

      {/* Remove confirm dialog */}
      {removeTarget && (
        <div className="card" style={{ border:"1px solid rgba(180,68,68,0.45)", background:"rgba(180,68,68,0.06)" }}>
          <span className="activity-type-label" style={{ color:"#c55" }}>Confirm Item Removal</span>
          <h4 style={{ margin:"6px 0 4px" }}>{removeTarget.name}</h4>
          <p className="muted-text">Permanently removes this item from the player's inventory. This cannot be undone.</p>
          <label style={{ marginTop:"10px" }}>
            <span>Staff Reason (required)</span>
            <textarea rows={2} value={removeReason} onChange={(e) => setRemoveReason(e.target.value)} placeholder="Why is this item being removed?" />
          </label>
          <div className="actions" style={{ marginTop:"10px" }}>
            <button className="danger-button" onClick={removeItem} disabled={removing}><Trash2 size={14} /> {removing ? "Removing..." : "Confirm Remove"}</button>
            <button className="ghost" onClick={() => { setRemoveTarget(null); setRemoveReason(""); }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Full profile — mirrors OCDashboard layout */}
      {summary && !loading && (
        <>
          {/* Header hero */}
          <div className="card request-workflow-hero">
            <div>
              <span className="activity-type-label">Staff — Player Profile</span>
              <h2>{summary.character?.name || "OC"}</h2>
              <p className="muted-text">
                Discord: {summary.character?.user_id || summary.character?.discord_id || "—"}
                {summary.wallet?.available_xp !== undefined ? ` · Available XP: ${summary.wallet.available_xp}` : ""}
              </p>
            </div>
            <button className="ghost" onClick={() => loadProfile(characterId)}><RefreshCw size={15} /> Refresh</button>
          </div>

          <OCMoneyCard discordId={discordId} characterId={characterId} />

          <section className="grid oc-dashboard-grid">
            {/* Core stats — same card as OCDashboard */}
            <div className="card">
              <div className="card-title-row">
                <h2>Core Stats</h2>
              </div>
              <div className="mini-stat-grid">
                {(Object.keys(STAT_LABELS) as Array<keyof CoreStats>).map((key) => (
                  <div key={key} className="mini-stat"><span>{STAT_LABELS[key]}</span><strong>{summary.stats?.[key] ?? 0}</strong></div>
                ))}
              </div>
            </div>

            {/* Traits — exact copy of OC traits card */}
            <div className="card oc-traits-card">
              <div className="card-title-row">
                <div>
                  <h2>Traits</h2>
                  <p className="muted-text">Traits attached to this OC.</p>
                </div>
                <span className="pill">{(summary.traits || []).length} traits</span>
              </div>
              {(summary.traits || []).length === 0 ? <p>No traits found.</p> : (
                <div className="owned-skill-list">
                  {(summary.traits || []).map((trait: any, i: number) => (
                    <div className="owned-skill-row" key={`${trait.slug || trait.trait_id}-${i}`}>
                      <div>
                        <strong>{trait.name || trait.slug || "Trait"}</strong>
                        {trait.description ? <small>{trait.description}</small> : null}
                      </div>
                      <div className="owned-skill-meta">
                        <span>{trait.tier || trait.category || "Trait"}</span>
                        {trait.cost != null ? <span>{trait.cost} pts</span> : null}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Skills — exact copy of OC skills card */}
            <div className="card oc-skills-card">
              <div className="card-title-row">
                <div>
                  <h2>Owned Skills</h2>
                  <p className="muted-text">Skills this OC currently owns.</p>
                </div>
                <span className="pill good">{ownedSkills.length} owned</span>
              </div>
              {ownedSkills.length === 0 ? <p>No owned skills found.</p> : null}
              {Object.entries(groupedSkills).map(([tree, skills]) => (
                <div className="owned-skill-group" key={tree}>
                  <div className="owned-skill-group-heading"><h3>{tree}</h3><span>{skills.length}</span></div>
                  <div className="owned-skill-list">
                    {skills.map((skill: any) => (
                      <div className="owned-skill-row" key={skill.skill_key}>
                        <div><strong>{skill.name || skill.skill_key}</strong></div>
                        <div className="owned-skill-meta">
                          <span>Tier {skill.tier ?? "—"}</span>
                          <span>{skill.cost ?? 0} XP</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Derived stats — same card as OCDashboard */}
            <div className="card">
              <h2>Derived Stats</h2>
              <div className="summary vertical">
                {Object.entries(summary.derived || {}).map(([key, value]) => (
                  <div key={key}>
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>{String(value)}</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* Inventory — staff-only card with GM remove buttons */}
            <div className="card" style={{ gridColumn:"1 / -1" }}>
              <div className="card-title-row">
                <div>
                  <h2>Inventory</h2>
                  <p className="muted-text">{items.length} item{items.length !== 1 ? "s" : ""} · Staff can remove items below.</p>
                </div>
                {currencies.length > 0 && (
                  <div style={{ display:"flex", gap:"12px", alignItems:"center", flexWrap:"wrap" }}>
                    {currencies.map((c: any, i: number) => (
                      <span key={i} style={{ fontSize:"13px" }}>{c.emoji ? `${c.emoji} ` : ""}<strong>{c.balance ?? 0}</strong> {c.name}{c.ticker ? ` (${c.ticker})` : ""}</span>
                    ))}
                  </div>
                )}
              </div>
              {items.length === 0 ? (
                <p className="muted-text">No items in inventory.</p>
              ) : (
                <div className="owned-skill-list" style={{ marginTop:"10px" }}>
                  {items.map((item: any, i: number) => (
                    <div className="owned-skill-row" key={item.inventory_id || i} style={{ alignItems: "flex-start", gap: "12px" }}>
                      {item.image_url && (
                        <img
                          src={item.image_url}
                          alt={item.name}
                          style={{ width:"44px", height:"44px", borderRadius:"7px", objectFit:"cover", flexShrink:0, border:"1px solid rgba(255,255,255,0.1)", marginTop:"2px" }}
                          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                      )}
                      <div style={{ flex: 1 }}>
                        <strong>{item.name}</strong>
                        {item.description && <small style={{ display:"block", marginTop:"3px", opacity:0.75 }}>{item.description}</small>}
                        {item.sheet_url && <a href={item.sheet_url} target="_blank" rel="noopener noreferrer" style={{ fontSize:"11px", opacity:0.7 }}>📄 Item Docs</a>}
                      </div>
                      <div className="owned-skill-meta" style={{ alignItems:"center", flexShrink: 0 }}>
                        <span>{item.type}</span>
                        {item.quantity !== 1 ? <span>× {item.quantity}</span> : null}
                        <button className="danger-button" style={{ fontSize:"12px", padding:"3px 10px", marginLeft:"6px" }}
                          onClick={() => setRemoveTarget(item)}>
                          <Trash2 size={12} /> Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          <button className="ghost" style={{ alignSelf:"flex-start", marginTop:"4px" }}
            onClick={() => { setSummary(null); setCharacterId(""); setInvData(null); setOwnedSkills([]); setQuery(""); }}>
            ← Back to Search
          </button>
        </>
      )}
    </div>
  );
}

function StaffQueue({ discordId }: { discordId: string }) {
  const [staffTab, setStaffTab] = useState<"queue" | "lookup" | "actions">("queue");
  const [requests, setRequests] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [staffConfirmation, setStaffConfirmation] = useState("");
  const [status, setStatus] = useState("pending");
  const [requestType, setRequestType] = useState("all");
  const [search, setSearch] = useState("");
  const [overrideCharacters, setOverrideCharacters] = useState<any[]>([]);
  const [overrideSkills, setOverrideSkills] = useState<any[]>([]);
  const [overrideForm, setOverrideForm] = useState({
    character_id: "",
    skill_key: "",
    source_trait: "Origin Trait",
    reason: "",
  });
  const [resourceCharacters, setResourceCharacters] = useState<any[]>([]);
  const [resourceCurrencies, setResourceCurrencies] = useState<any[]>([]);
  const [resourceForm, setResourceForm] = useState({
    character_id: "",
    grant_type: "xp",
    amount: "600",
    currency_id: "",
    reason: "Starting OC setup grant.",
  });
  const [traitBenefitTraits, setTraitBenefitTraits] = useState<any[]>([]);
  const [traitBenefitSkills, setTraitBenefitSkills] = useState<any[]>([]);
  const [traitBenefitCharacters, setTraitBenefitCharacters] = useState<any[]>([]);
  const [traitBenefitForm, setTraitBenefitForm] = useState({
    character_id: "",
    trait_slug: "",
    skill_key: "",
    reason: "",
  });
  const [loading, setLoading] = useState(false);
  const [workingKey, setWorkingKey] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [overrideByRequest, setOverrideByRequest] = useState<Record<string, boolean>>({});

  const [discordRoleSyncing, setDiscordRoleSyncing] = useState(false);
  const [discordRoleSyncResult, setDiscordRoleSyncResult] = useState<any>(null);

  async function syncAllDiscordLoreRoles(dryRun = false) {
    setMessage("");
    setStaffConfirmation("");
    setDiscordRoleSyncing(true);

    try {
      const data = await apiFetch(
        "/api/staff/discord-roles/sync-all",
        {
          method: "POST",
          body: JSON.stringify({ dry_run: dryRun }),
        },
        discordId
      );

      setDiscordRoleSyncResult(data);
      const successMessage = data.message || "Discord lore role sync complete.";
      setMessage(successMessage);
      setStaffConfirmation(successMessage);
      if (!dryRun) {
        window.alert(successMessage);
      }
    } catch (error: any) {
      setMessage(error?.message || "Could not sync Discord lore roles.");
    } finally {
      setDiscordRoleSyncing(false);
    }
  }

  const [maintenanceOptions, setMaintenanceOptions] = useState<any>({ characters: [], skills: [], traits: [] });
  const [maintenanceForm, setMaintenanceForm] = useState({
    action: "remove_xp",
    character_id: "",
    amount: "",
    skill_key: "",
    trait_slug: "",
    custom_name: "",
    custom_key: "",
    custom_tree: "Staff Custom",
    custom_tier: "0",
    custom_cost: "0",
    custom_category: "custom",
    custom_description: "",
    reason: "",
  });

  async function loadMaintenanceOptions() {
    try {
      const data = await apiFetch("/api/staff/maintenance/options", {}, discordId);
      setMaintenanceOptions(data || { characters: [], skills: [], traits: [] });
    } catch (error: any) {
      console.warn("Could not load staff maintenance options", error);
    }
  }

  async function runMaintenanceAction() {
    setMessage("");
    setStaffConfirmation("");

    if (!maintenanceForm.character_id) {
      setMessage("Choose an OC first.");
      return;
    }
    const actionNeedsReason = ![
      "apply_trait_benefit",
      "preview_city_lore_roles",
      "backfill_city_lore_roles",
    ].includes(maintenanceForm.action);

    if (actionNeedsReason && !maintenanceForm.reason.trim()) {
      setMessage("Add a staff reason for the correction.");
      return;
    }

    const action = maintenanceForm.action;
    let endpoint = "";
    let body: any = { character_id: maintenanceForm.character_id, reason: maintenanceForm.reason };

    if (action === "grant_resources") {
      const payload = {
        ...resourceForm,
        character_id: maintenanceForm.character_id,
        reason: maintenanceForm.reason,
        amount: Number(resourceForm.amount || maintenanceForm.amount || 0),
      };

      if (!payload.amount || payload.amount <= 0) {
        setMessage("Enter a positive amount.");
        return;
      }

      try {
        const data = await apiFetch(
          "/api/staff/resource-grants/grant",
          { method: "POST", body: JSON.stringify(payload) },
          discordId
        );
        const successMessage = data.message || "Resource grant complete.";
        setMessage(successMessage);
        setStaffConfirmation(successMessage);
        window.alert(successMessage);
        setMaintenanceForm((current) => ({ ...current, amount: "", reason: "" }));
        await Promise.all([loadQueue(), loadStaffResourceOptions(), loadMaintenanceOptions()]);
      } catch (error: any) {
        setMessage(error?.message || "Could not grant resources.");
      }
      return;
    }

    if (action === "grant_skill_override") {
      if (!overrideForm.skill_key) {
        setMessage("Choose a skill before granting a skill override.");
        return;
      }

      try {
        const data = await apiFetch(
          "/api/staff/skill-overrides/grant",
          {
            method: "POST",
            body: JSON.stringify({
              ...overrideForm,
              character_id: maintenanceForm.character_id,
              reason: maintenanceForm.reason,
            }),
          },
          discordId
        );
        const successMessage = data.message || "Skill override granted.";
        setMessage(successMessage);
        setStaffConfirmation(successMessage);
        window.alert(successMessage);
        setOverrideForm((current) => ({ ...current, skill_key: "", reason: "" }));
        setMaintenanceForm((current) => ({ ...current, reason: "" }));
        await Promise.all([loadQueue(), loadSkillOverrideOptions(), loadMaintenanceOptions()]);
      } catch (error: any) {
        setMessage(error?.message || "Could not grant skill override.");
      }
      return;
    }

    if (action === "apply_trait_benefit") {
      if (!traitBenefitForm.trait_slug) {
        setMessage("Choose a trait or origin first.");
        return;
      }

      if (!traitBenefitForm.skill_key) {
        setMessage("Choose the free skill to grant.");
        return;
      }

      try {
        const traitName = selectedTraitBenefit?.name || traitBenefitForm.trait_slug;
        const selectedSkill = traitBenefitSkills.find((skill: any) => skill.skill_key === traitBenefitForm.skill_key);
        const reason = maintenanceForm.reason.trim()
          || traitBenefitForm.reason.trim()
          || `Granted ${selectedSkill?.name || traitBenefitForm.skill_key} from ${traitName} trait benefit.`;

        const data = await apiFetch(
          "/api/staff/trait-benefits/apply",
          {
            method: "POST",
            body: JSON.stringify({
              ...traitBenefitForm,
              character_id: maintenanceForm.character_id,
              reason,
            }),
          },
          discordId
        );

        const successMessage = data.message || "Trait benefit applied.";
        setMessage(successMessage);
        setStaffConfirmation(successMessage);
        window.alert(successMessage);
        setTraitBenefitForm((current) => ({ ...current, skill_key: "", reason: "" }));
        setMaintenanceForm((current) => ({ ...current, reason: "" }));
        await Promise.all([loadQueue(), loadTraitBenefitOptions(), loadSkillOverrideOptions(), loadMaintenanceOptions()]);
      } catch (error: any) {
        setMessage(error?.message || "Could not apply trait benefit.");
      }
      return;
    }

    if (action === "backfill_city_lore_roles") {
      await syncAllDiscordLoreRoles(false);
      return;
    }

    if (action === "preview_city_lore_roles") {
      await syncAllDiscordLoreRoles(true);
      return;
    }

    if (action === "remove_xp") {
      endpoint = "/api/staff/maintenance/xp/remove";
      body.amount = Number(maintenanceForm.amount || 0);
      if (!body.amount || body.amount <= 0) {
        setMessage("Enter the XP amount to remove.");
        return;
      }
    } else if (action === "remove_skill") {
      endpoint = "/api/staff/maintenance/skill/remove";
      body.skill_key = maintenanceForm.skill_key;
      if (!body.skill_key) {
        setMessage("Choose the skill to remove.");
        return;
      }
    } else if (action === "remove_trait") {
      endpoint = "/api/staff/maintenance/trait/remove";
      body.trait_slug = maintenanceForm.trait_slug;
      if (!body.trait_slug) {
        setMessage("Choose the trait to remove.");
        return;
      }
    } else if (action === "grant_custom_skill") {
      endpoint = "/api/staff/maintenance/custom-skill/grant";
      body = { ...body, name: maintenanceForm.custom_name, skill_key: maintenanceForm.custom_key, tree: maintenanceForm.custom_tree, tier: Number(maintenanceForm.custom_tier || 0), cost: Number(maintenanceForm.custom_cost || 0), description: maintenanceForm.custom_description };
      if (!body.name) {
        setMessage("Enter a custom skill name.");
        return;
      }
    } else if (action === "grant_custom_trait") {
      endpoint = "/api/staff/maintenance/custom-trait/grant";
      body = { ...body, name: maintenanceForm.custom_name, slug: maintenanceForm.custom_key, tier: maintenanceForm.custom_tier || "reliable", cost: Number(maintenanceForm.custom_cost || 0), category: maintenanceForm.custom_category || "custom", description: maintenanceForm.custom_description };
      if (!body.name) {
        setMessage("Enter a custom trait name.");
        return;
      }
    }

    try {
      const data = await apiFetch(endpoint, { method: "POST", body: JSON.stringify(body) }, discordId);
      const successMessage = data.message || "Staff maintenance action complete.";
      setMessage(successMessage);
      setStaffConfirmation(successMessage);
      window.alert(successMessage);
      setMaintenanceForm((current) => ({ ...current, amount: "", skill_key: "", trait_slug: "", custom_name: "", custom_key: "", custom_description: "", reason: "" }));
      await Promise.all([loadQueue(), loadMaintenanceOptions(), loadSkillOverrideOptions(), loadTraitBenefitOptions(), loadStaffResourceOptions()]);
    } catch (error: any) {
      setMessage(error?.message || "Could not complete staff maintenance action.");
    }
  }

  useEffect(() => {
    loadMaintenanceOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadQueue() {
    if (!discordId) return;

    setLoading(true);
    setMessage("");
    try {
      const params = new URLSearchParams({
        status,
        request_type: requestType,
      });

      const data = await apiFetch(`/api/requests/queue?${params.toString()}`, {}, discordId);
      setRequests(data.requests || []);
    } catch (error: any) {
      setRequests([]);
      setMessage(error.message || "Could not load request queue.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId, status, requestType]);

  function requestKey(request: any) {
    return `${request.request_type}:${request.request_id}`;
  }

  async function approveRequest(request: any) {
    const key = requestKey(request);
    setWorkingKey(key);
    setMessage("");

    try {
      const body = JSON.stringify({
        staff_note: notes[key] || "",
        override_requirements: Boolean(overrideByRequest[key]),
        staff_override: Boolean(overrideByRequest[key]),
        override_reason: notes[key] || "",
      });
      const data = await apiFetch(
        `/api/requests/${request.request_type}/${request.request_id}/approve`,
        { method: "POST", body },
        discordId
      );

      setMessage(data.message || "Request approved.");
      setStaffConfirmation(data.message || "Request approved.");
      await loadQueue();
    } catch (error: any) {
      setMessage(error.message || "Could not approve request.");
    } finally {
      setWorkingKey("");
    }
  }

  async function denyRequest(request: any) {
    const key = requestKey(request);
    const reason = (notes[key] || "").trim();

    if (!reason) {
      setMessage("A denial reason is required.");
      return;
    }

    setWorkingKey(key);
    setMessage("");

    try {
      const body = JSON.stringify({ reason });
      const data = await apiFetch(
        `/api/requests/${request.request_type}/${request.request_id}/deny`,
        { method: "POST", body },
        discordId
      );

      setMessage(data.message || "Request denied.");
      setStaffConfirmation(data.message || "Request denied.");
      await loadQueue();
    } catch (error: any) {
      setMessage(error.message || "Could not deny request.");
    } finally {
      setWorkingKey("");
    }
  }

  function pretty(value: string) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function formatDate(value: string | null | undefined) {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
  }

  function statusClass(value: string) {
    const normalized = String(value || "").toLowerCase();

    if (normalized === "approved") return "approved";
    if (normalized === "denied") return "denied";
    if (normalized === "pending") return "pending";

    return "info";
  }

  const visibleRequests = requests.filter((request) => {
    const query = search.trim().toLowerCase();
    if (!query) return true;

    const haystack = [
      request.title,
      request.summary,
      request.character_name,
      request.actor_id,
      request.request_type,
      request.status,
      request.reason,
      request.staff_note,
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });

  const counts = {
    total: requests.length,
    pending: requests.filter((request) => request.status === "pending").length,
    approved: requests.filter((request) => request.status === "approved").length,
    denied: requests.filter((request) => request.status === "denied").length,
  };

  useEffect(() => {
    loadSkillOverrideOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadSkillOverrideOptions() {
    try {
      const data = await apiFetch("/api/staff/skill-overrides/options", {}, discordId);
      setOverrideCharacters(data.characters || []);
      setOverrideSkills(data.skills || []);
    } catch (error: any) {
      console.warn("Could not load staff skill override options", error);
    }
  }

  async function grantSkillOverride() {
    setMessage("");

    if (!overrideForm.character_id) {
      setMessage("Choose an OC before granting a skill override.");
      return;
    }

    if (!overrideForm.skill_key) {
      setMessage("Choose a skill before granting a skill override.");
      return;
    }

    if (!overrideForm.reason.trim()) {
      setMessage("Add a staff override reason before granting the skill.");
      return;
    }

    try {
      const data = await apiFetch(
        "/api/staff/skill-overrides/grant",
        {
          method: "POST",
          body: JSON.stringify(overrideForm),
        },
        discordId
      );

      setMessage(data.message || "Skill override granted.");
      setStaffConfirmation(data.message || "Skill override granted.");
      window.alert(data.message || "Skill override granted.");
      setOverrideForm((current) => ({ ...current, skill_key: "", reason: "" }));
      await Promise.all([loadQueue(), loadSkillOverrideOptions()]);
    } catch (error: any) {
      setMessage(error?.message || "Could not grant skill override.");
    }
  }

  useEffect(() => {
    loadStaffResourceOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadStaffResourceOptions() {
    try {
      const data = await apiFetch("/api/staff/resource-grants/options", {}, discordId);
      setResourceCharacters(data.characters || []);
      setResourceCurrencies(data.currencies || []);
      const primaryCurrency = data.primary_currency;
      if (primaryCurrency?.currency_id) {
        setResourceForm((current) => ({
          ...current,
          currency_id: current.currency_id || primaryCurrency.currency_id,
        }));
      }
    } catch (error: any) {
      console.warn("Could not load staff resource grant options", error);
    }
  }

  async function grantStaffResource() {
    setMessage("");
    setStaffConfirmation("");

    if (!resourceForm.character_id) {
      setMessage("Choose an OC before granting resources.");
      return;
    }

    if (!resourceForm.amount || Number(resourceForm.amount) <= 0) {
      setMessage("Enter a positive amount.");
      return;
    }

    if (!resourceForm.reason.trim()) {
      setMessage("Add a staff reason before granting resources.");
      return;
    }

    try {
      const data = await apiFetch(
        "/api/staff/resource-grants/grant",
        {
          method: "POST",
          body: JSON.stringify({
            ...resourceForm,
            amount: Number(resourceForm.amount),
          }),
        },
        discordId
      );

      const successMessage = data.message || "Resource grant complete.";
      setMessage(successMessage);
      setStaffConfirmation(successMessage);
      window.alert(successMessage);
      setResourceForm((current) => ({
        ...current,
        amount: current.grant_type === "xp" ? "600" : "",
        reason: "",
      }));
      await Promise.all([loadQueue(), loadStaffResourceOptions()]);
      setMessage(successMessage);
      setStaffConfirmation(successMessage);
    } catch (error: any) {
      setMessage(error?.message || "Could not grant resources.");
    }
  }

  useEffect(() => {
    loadTraitBenefitOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadTraitBenefitOptions() {
    try {
      const data = await apiFetch("/api/staff/trait-benefits/options", {}, discordId);
      setTraitBenefitCharacters(data.characters || []);
      setTraitBenefitTraits(data.traits || []);
      setTraitBenefitSkills(data.skills || []);
    } catch (error: any) {
      console.warn("Could not load trait benefit options", error);
    }
  }

  const selectedTraitBenefit = traitBenefitTraits.find((trait: any) =>
    String(trait.slug || "") === String(traitBenefitForm.trait_slug || "")
  );

  const traitAllowedSkillKeys = selectedTraitBenefit?.grant_config?.skill_keys || [];
  const traitFilteredSkills = traitAllowedSkillKeys.length > 0
    ? traitBenefitSkills.filter((skill: any) => traitAllowedSkillKeys.includes(skill.skill_key))
    : traitBenefitSkills;

  async function applyTraitBenefit() {
    setMessage("");
    setStaffConfirmation("");

    if (!traitBenefitForm.character_id) {
      setMessage("Choose an OC before applying a trait benefit.");
      return;
    }

    if (!traitBenefitForm.trait_slug) {
      setMessage("Choose a trait or origin first.");
      return;
    }

    if (!traitBenefitForm.skill_key) {
      setMessage("Choose the free skill to grant.");
      return;
    }

    try {
      const traitName = selectedTraitBenefit?.name || traitBenefitForm.trait_slug;
      const selectedSkill = traitBenefitSkills.find((skill: any) => skill.skill_key === traitBenefitForm.skill_key);
      const reason = traitBenefitForm.reason.trim()
        || `Granted ${selectedSkill?.name || traitBenefitForm.skill_key} from ${traitName} trait benefit.`;

      const data = await apiFetch(
        "/api/staff/trait-benefits/apply",
        {
          method: "POST",
          body: JSON.stringify({
            ...traitBenefitForm,
            reason,
          }),
        },
        discordId
      );

      const successMessage = data.message || "Trait benefit applied.";
      setTraitBenefitForm((current) => ({
        ...current,
        skill_key: "",
        reason: "",
      }));

      await Promise.all([loadQueue(), loadTraitBenefitOptions(), loadSkillOverrideOptions()]);
      setMessage(successMessage);
      setStaffConfirmation(successMessage);
    } catch (error: any) {
      setMessage(error?.message || "Could not apply trait benefit.");
    }
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="request-workflow-page">

        <div className="card request-workflow-hero">
          <div>
            <span className="activity-type-label">Staff Operations</span>
            <h2>Staff Center</h2>
            <p className="muted-text">
              Approve requests, look up any player's full profile, or run staff actions like grants, overrides, and corrections.
            </p>
          </div>
        </div>

        {/* Inner tab bar — mirrors GettingStarted style */}
        <div style={{ display:"flex", gap:"6px", borderBottom:"1px solid rgba(255,255,255,0.08)", paddingBottom:"2px", marginBottom:"4px", flexWrap:"wrap" }}>
          {([
            { id: "queue", label: "📋 Request Queue", badge: counts.pending > 0 ? counts.pending : null },
            { id: "lookup", label: "🔍 Player Lookup" },
            { id: "actions", label: "⚙️ Action Center" },
          ] as const).map((t) => (
            <button
              key={t.id}
              onClick={() => setStaffTab(t.id)}
              className={staffTab === t.id ? "" : "ghost"}
              style={{ fontSize:"13px", padding:"5px 14px", display:"flex", alignItems:"center", gap:"6px", borderBottom: staffTab === t.id ? "2px solid #2f6f73" : "2px solid transparent", borderRadius:"4px 4px 0 0" }}
            >
              {t.label}
              {"badge" in t && t.badge ? (
                <span style={{ background:"#c05", color:"#fff", borderRadius:"99px", fontSize:"11px", padding:"1px 7px", fontWeight:700 }}>{t.badge}</span>
              ) : null}
            </button>
          ))}
        </div>

        {/* ── Request Queue tab ── */}
        {staffTab === "queue" && (<>

        <div style={{ display:"flex", justifyContent:"flex-end", marginBottom:"4px" }}>
          <button className="ghost" onClick={loadQueue} disabled={loading}>
            <RefreshCw size={15} /> {loading ? "Loading..." : "Refresh Queue"}
          </button>
        </div>

        <div className="request-summary-grid">
          <div className="card request-summary-card">
            <span>Total</span>
            <strong>{counts.total}</strong>
          </div>
          <div className="card request-summary-card pending">
            <span>Pending</span>
            <strong>{counts.pending}</strong>
          </div>
          <div className="card request-summary-card approved">
            <span>Approved</span>
            <strong>{counts.approved}</strong>
          </div>
          <div className="card request-summary-card denied">
            <span>Denied</span>
            <strong>{counts.denied}</strong>
          </div>
        </div>

        <div className="card request-filters-card">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search requests..."
          />

          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="all">All Statuses</option>
          </select>

          <select value={requestType} onChange={(event) => setRequestType(event.target.value)}>
            <option value="all">All Types</option>
            <option value="stat">Stat Requests</option>
            <option value="skill">Skill Requests</option>
          </select>
        </div>

        {message ? <p className="message">{message}</p> : null}
        {staffConfirmation ? (
          <div className="card staff-confirmation-card">
            <strong>Done</strong>
            <p>{staffConfirmation}</p>
          </div>
        ) : null}

        <div className="card discord-lore-role-backfill-card" style={{ display: "none" }}>
          <div className="card-title-row">
            <div>
              <span className="activity-type-label">Discord Roles</span>
              <h3>Backfill City Lore Roles</h3>
              <p className="muted-text">
                Sync active lore role mappings for all active OCs. Since religion mappings are inactive, this currently only assigns city-state origin roles.
              </p>
            </div>
          </div>

          <div className="actions">
            <button className="ghost" onClick={() => syncAllDiscordLoreRoles(true)} disabled={discordRoleSyncing}>
              <RefreshCw size={16} /> {discordRoleSyncing ? "Working..." : "Preview Backfill"}
            </button>
            <button onClick={() => syncAllDiscordLoreRoles(false)} disabled={discordRoleSyncing}>
              <ShieldCheck size={16} /> {discordRoleSyncing ? "Working..." : "Backfill Roles"}
            </button>
          </div>

          {discordRoleSyncResult ? (
            <div className="request-note-block">
              <span>Last Sync Result</span>
              <p>
                Checked {discordRoleSyncResult.characters_checked ?? 0} OC(s) - Roles applied: {discordRoleSyncResult.roles_applied ?? 0} - Skipped: {discordRoleSyncResult.characters_skipped ?? 0} - Errors: {discordRoleSyncResult.errors ?? 0}
              </p>
            </div>
          ) : null}
        </div>

        <div className="request-card-list">
          {visibleRequests.length === 0 ? (
            <div className="card request-empty-state">
              <strong>No requests found.</strong>
              <p className="muted-text">Try changing filters or refreshing the queue.</p>
            </div>
          ) : null}

          {visibleRequests.map((request) => {
            const key = requestKey(request);
            const working = workingKey === key;
            const pending = request.status === "pending";

            return (
              <div className="card request-review-card" key={key}>
                <div className="request-review-top">
                  <div>
                    <span className="activity-type-label">{pretty(request.request_type)} Request</span>
                    <h3>{request.title || request.summary || "Request"}</h3>
                    <p className="muted-text">{request.summary}</p>
                  </div>

                  <em className={`request-status-pill ${statusClass(request.status)}`}>
                    {pretty(request.status)}
                  </em>
                </div>

                <div className="request-meta-grid">
                  <div>
                    <span>OC</span>
                    <strong>{request.character_name || request.character_id || "—"}</strong>
                  </div>
                  <div>
                    <span>Submitted By</span>
                    <strong>{request.actor_id ? `<@${request.actor_id}>` : "—"}</strong>
                  </div>
                  <div>
                    <span>Amount / Cost</span>
                    <strong>{request.amount ?? "—"}</strong>
                  </div>
                  <div>
                    <span>Created</span>
                    <strong>{formatDate(request.created_at)}</strong>
                  </div>
                </div>

                {request.reason ? (
                  <div className="request-note-block">
                    <span>Player Reason</span>
                    <p>{request.reason}</p>
                  </div>
                ) : null}

                {request.staff_note ? (
                  <div className="request-note-block staff">
                    <span>Staff Note</span>
                    <p>{request.staff_note}</p>
                  </div>
                ) : null}

                {pending ? (
                  <div className="request-actions-panel">
                    {request.request_type === "skill" && isOriginTraitFreeSkillRequest(request) ? (
                      <div className="request-note-block">
                        <span>Free Origin / Trait Skill</span>
                        <p>Keystone will approve this as a 0 XP staff override even if staff clicks plain Approve.</p>
                      </div>
                    ) : null}

                    {request.request_type === "skill" ? (
                      <div className="skill-override-panel">
                        <label className="skill-override-check">
                          <input
                            type="checkbox"
                            checked={Boolean(overrideByRequest[key])}
                            onChange={(event) =>
                              setOverrideByRequest((current) => ({ ...current, [key]: event.target.checked }))
                            }
                          />
                          <span>Staff override skill requirements</span>
                        </label>
                        <small>
                          Use only for Origin traits, special approvals, or staff-approved exceptions. Add the reason below.
                        </small>
                      </div>
                    ) : null}

                    <label>
                      <span>Staff Note / Denial Reason</span>
                      <textarea
                        rows={3}
                        value={notes[key] || ""}
                        onChange={(event) =>
                          setNotes((current) => ({ ...current, [key]: event.target.value }))
                        }
                        placeholder="Optional for approval, required for denial."
                      />
                    </label>

                    <div className="auth-actions">
                      <button onClick={() => approveRequest(request)} disabled={working}>
                        <Check size={16} /> {working ? "Working..." : "Approve"}
                      </button>
                      <button className="danger-button" onClick={() => denyRequest(request)} disabled={working}>
                        <X size={16} /> Deny
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>

        </>)} {/* end queue tab */}

        {/* ── Player Lookup tab ── */}
        {staffTab === "lookup" && (
          <StaffPlayerLookup discordId={discordId} />
        )}

        {/* ── Action Center tab ── */}
        {staffTab === "actions" && (<>

<div className="card staff-resource-grant-card" style={{ display: "none" }}>
          <div className="card-title-row">
            <div>
              <span className="activity-type-label">Staff Resources</span>
              <h3>Grant OC Resources</h3>
              <p className="muted-text">
                Use this for starting XP, event awards, corrections, or staff-approved currency grants. New OCs should start with 600 XP unless staff says otherwise.
              </p>
            </div>
            <button className="ghost" onClick={loadStaffResourceOptions}>
              <RefreshCw size={16} /> Refresh Options
            </button>
          </div>

          <div className="request-actions-panel staff-resource-grant-form">
            <label>
              <span>OC</span>
              <select
                value={resourceForm.character_id}
                onChange={(event) =>
                  setResourceForm((current) => ({ ...current, character_id: event.target.value }))
                }
              >
                <option value="">Select an OC</option>
                {resourceCharacters.map((character: any) => (
                  <option key={character.character_id} value={character.character_id}>
                    {character.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Grant Type</span>
              <select
                value={resourceForm.grant_type}
                onChange={(event) =>
                  setResourceForm((current) => ({
                    ...current,
                    grant_type: event.target.value,
                    amount: event.target.value === "xp" ? "600" : current.amount,
                  }))
                }
              >
                <option value="xp">XP</option>
                <option value="currency">Currency</option>
              </select>
            </label>

            {resourceForm.grant_type === "currency" ? (
              <label>
                <span>Currency</span>
                <select
                  value={resourceForm.currency_id}
                  onChange={(event) =>
                    setResourceForm((current) => ({ ...current, currency_id: event.target.value }))
                  }
                >
                  <option value="">Primary currency</option>
                  {resourceCurrencies.map((currency: any) => (
                    <option key={currency.currency_id} value={currency.currency_id}>
                      {currency.emoji ? `${currency.emoji} ` : ""}{currency.name} ({currency.ticker})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <label>
              <span>Amount</span>
              <input
                type="number"
                min="1"
                value={resourceForm.amount}
                onChange={(event) =>
                  setResourceForm((current) => ({ ...current, amount: event.target.value }))
                }
                placeholder={resourceForm.grant_type === "xp" ? "600" : "Amount"}
              />
            </label>

            <label>
              <span>Staff Reason</span>
              <textarea
                rows={3}
                value={resourceForm.reason}
                onChange={(event) =>
                  setResourceForm((current) => ({ ...current, reason: event.target.value }))
                }
                placeholder="Example: Starting OC setup grant, event reward, correction, or approved staff adjustment."
              />
            </label>

            <div className="actions">
              <button onClick={grantStaffResource}>
                <ShieldCheck size={16} /> Grant Resources
              </button>
            </div>
          </div>
        </div>

        <div className="card staff-maintenance-card">
          <div className="card-title-row">
            <div>
              <span className="activity-type-label">Staff Toolbox</span>
              <h3>Staff Action Center</h3>
              <p className="muted-text">
                Choose one staff workflow from the dropdown. This replaces the separate resource, override, trait benefit, correction, and custom-grant cards.
              </p>
            </div>
            <button className="ghost" onClick={loadMaintenanceOptions}>
              <RefreshCw size={16} /> Refresh Options
            </button>
          </div>

          <div className="request-actions-panel staff-maintenance-form">
            <label>
              <span>OC</span>
              <select value={maintenanceForm.character_id} onChange={(event) => setMaintenanceForm((current) => ({ ...current, character_id: event.target.value }))}>
                <option value="">Select an OC</option>
                {(maintenanceOptions.characters || resourceCharacters).map((character: any) => (
                  <option key={character.character_id} value={character.character_id}>{character.name}</option>
                ))}
              </select>
            </label>

            <label>
              <span>Action</span>
              <select value={maintenanceForm.action} onChange={(event) => setMaintenanceForm((current) => ({ ...current, action: event.target.value }))}>
                <option value="grant_resources">Grant XP / Currency</option>
                <option value="grant_skill_override">Grant Skill Override</option>
                <option value="apply_trait_benefit">Apply Trait Benefit</option>
                <option value="preview_city_lore_roles">Preview City Lore Role Backfill</option>
                <option value="backfill_city_lore_roles">Backfill City Lore Roles</option>
                <option value="remove_xp">Remove XP</option>
                <option value="remove_skill">Remove Skill</option>
                <option value="remove_trait">Remove Trait</option>
                <option value="grant_custom_skill">Grant Hidden Custom Skill</option>
                <option value="grant_custom_trait">Grant Hidden Custom Trait</option>
                                <option value="trait_grant_only">Grant / Remove Trait Only</option>
                </select>
            </label>

        {maintenanceForm.action === "trait_grant_only" ? (
              <StaffTraitGrantCard discordId={discordId} selectedCharacterId={maintenanceForm.character_id} embedded fallbackCharacters={maintenanceOptions.characters || resourceCharacters} fallbackTraits={maintenanceOptions.traits || traitBenefitTraits} />
            ) : null}

            {maintenanceForm.action === "grant_resources" ? (
              <>
                <label>
                  <span>Grant Type</span>
                  <select
                    value={resourceForm.grant_type}
                    onChange={(event) =>
                      setResourceForm((current) => ({
                        ...current,
                        grant_type: event.target.value,
                        amount: event.target.value === "xp" ? "600" : current.amount,
                      }))
                    }
                  >
                    <option value="xp">XP</option>
                    <option value="currency">Currency</option>
                  </select>
                </label>

                {resourceForm.grant_type === "currency" ? (
                  <label>
                    <span>Currency</span>
                    <select
                      value={resourceForm.currency_id}
                      onChange={(event) =>
                        setResourceForm((current) => ({ ...current, currency_id: event.target.value }))
                      }
                    >
                      <option value="">Primary currency</option>
                      {resourceCurrencies.map((currency: any) => (
                        <option key={currency.currency_id} value={currency.currency_id}>
                          {currency.emoji ? `${currency.emoji} ` : ""}{currency.name} ({currency.ticker})
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}

                <label>
                  <span>Amount</span>
                  <input
                    type="number"
                    min="1"
                    value={resourceForm.amount}
                    onChange={(event) =>
                      setResourceForm((current) => ({ ...current, amount: event.target.value }))
                    }
                    placeholder={resourceForm.grant_type === "xp" ? "600" : "Amount"}
                  />
                </label>
              </>
            ) : null}

            {maintenanceForm.action === "grant_skill_override" ? (
              <>
                <label>
                  <span>Skill</span>
                  <select
                    value={overrideForm.skill_key}
                    onChange={(event) =>
                      setOverrideForm((current) => ({ ...current, skill_key: event.target.value }))
                    }
                  >
                    <option value="">Select a skill</option>
                    {overrideSkills.map((skill: any) => (
                      <option key={skill.skill_key} value={skill.skill_key}>
                        {skill.name || skill.skill_key}{skill.tree ? ` / ${skill.tree}` : ""}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Source / Trait</span>
                  <input
                    value={overrideForm.source_trait}
                    onChange={(event) =>
                      setOverrideForm((current) => ({ ...current, source_trait: event.target.value }))
                    }
                    placeholder="Origin Trait, Magic Background, Mana Circuits..."
                  />
                </label>
              </>
            ) : null}

            {maintenanceForm.action === "apply_trait_benefit" ? (
              <>
                <label>
                  <span>Trait / Origin</span>
                  <select
                    value={traitBenefitForm.trait_slug}
                    onChange={(event) =>
                      setTraitBenefitForm((current) => ({
                        ...current,
                        trait_slug: event.target.value,
                        skill_key: "",
                        reason: "",
                      }))
                    }
                  >
                    <option value="">Select a trait</option>
                    {traitBenefitTraits.map((trait: any) => (
                      <option key={trait.slug || trait.trait_id} value={trait.slug}>
                        {trait.name}{trait.tier ? ` / ${trait.tier}` : ""}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Free Skill</span>
                  <select
                    value={traitBenefitForm.skill_key}
                    onChange={(event) =>
                      setTraitBenefitForm((current) => ({ ...current, skill_key: event.target.value }))
                    }
                  >
                    <option value="">Select a skill</option>
                    {traitFilteredSkills.map((skill: any) => (
                      <option key={skill.skill_key} value={skill.skill_key}>
                        {skill.name || skill.skill_key}{skill.tree ? ` / ${skill.tree}` : ""}{skill.cost !== undefined ? ` / ${skill.cost} XP normally` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            ) : null}

            {maintenanceForm.action === "preview_city_lore_roles" || maintenanceForm.action === "backfill_city_lore_roles" ? (
              <div className="request-note-block">
                <span>City Lore Role Sync</span>
                <p>
                  Preview checks active OCs and mapped origin traits without assigning roles. Backfill assigns active city-state lore roles through Discord.
                </p>
                {discordRoleSyncResult ? (
                  <p>
                    Last result: checked {discordRoleSyncResult.characters_checked ?? 0} OC(s), roles applied {discordRoleSyncResult.roles_applied ?? 0}, skipped {discordRoleSyncResult.characters_skipped ?? 0}, errors {discordRoleSyncResult.errors ?? 0}.
                  </p>
                ) : null}
              </div>
            ) : null}

            {maintenanceForm.action === "remove_xp" ? (
              <label>
                <span>XP to Remove</span>
                <input type="number" min="1" value={maintenanceForm.amount} onChange={(event) => setMaintenanceForm((current) => ({ ...current, amount: event.target.value }))} placeholder="Example: 67" />
              </label>
            ) : null}

            {maintenanceForm.action === "remove_skill" ? (
              <label>
                <span>Skill to Remove</span>
                <select value={maintenanceForm.skill_key} onChange={(event) => setMaintenanceForm((current) => ({ ...current, skill_key: event.target.value }))}>
                  <option value="">Select a skill</option>
                  {(maintenanceOptions.skills || overrideSkills).map((skill: any) => (
                    <option key={skill.skill_key} value={skill.skill_key}>{skill.name || skill.skill_key}{skill.tree ? ` / ${skill.tree}` : ""}</option>
                  ))}
                </select>
              </label>
            ) : null}

            {maintenanceForm.action === "remove_trait" ? (
              <label>
                <span>Trait to Remove</span>
                <select value={maintenanceForm.trait_slug} onChange={(event) => setMaintenanceForm((current) => ({ ...current, trait_slug: event.target.value }))}>
                  <option value="">Select a trait</option>
                  {(maintenanceOptions.traits || traitBenefitTraits).map((trait: any) => (
                    <option key={trait.slug || trait.trait_id} value={trait.slug}>{trait.name || trait.slug}{trait.tier ? ` / ${trait.tier}` : ""}</option>
                  ))}
                </select>
              </label>
            ) : null}

            {maintenanceForm.action === "grant_custom_skill" || maintenanceForm.action === "grant_custom_trait" ? (
              <>
                <label><span>Custom Name</span><input value={maintenanceForm.custom_name} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_name: event.target.value }))} placeholder="Restricted lore option" /></label>
                <label><span>Optional Key / Slug</span><input value={maintenanceForm.custom_key} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_key: event.target.value }))} placeholder="Leave blank to auto-create" /></label>

                {maintenanceForm.action === "grant_custom_skill" ? (
                  <label><span>Skill Tree</span><input value={maintenanceForm.custom_tree} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_tree: event.target.value }))} placeholder="Staff Custom" /></label>
                ) : (
                  <label>
                    <span>Trait Tier</span>
                    <select value={maintenanceForm.custom_tier} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_tier: event.target.value }))}>
                      <option value="minor">Minor</option><option value="reliable">Reliable</option><option value="keystone">Keystone</option><option value="origin">Origin</option><option value="negative">Negative</option>
                    </select>
                  </label>
                )}

                <label><span>{maintenanceForm.action === "grant_custom_skill" ? "Tier" : "Cost"}</span><input value={maintenanceForm.action === "grant_custom_skill" ? maintenanceForm.custom_tier : maintenanceForm.custom_cost} onChange={(event) => setMaintenanceForm((current) => maintenanceForm.action === "grant_custom_skill" ? { ...current, custom_tier: event.target.value } : { ...current, custom_cost: event.target.value })} placeholder="0" /></label>

                {maintenanceForm.action === "grant_custom_skill" ? (
                  <label><span>Normal Cost</span><input type="number" value={maintenanceForm.custom_cost} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_cost: event.target.value }))} placeholder="0" /></label>
                ) : (
                  <label><span>Category</span><input value={maintenanceForm.custom_category} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_category: event.target.value }))} placeholder="custom" /></label>
                )}

                <label><span>Description</span><textarea rows={2} value={maintenanceForm.custom_description} onChange={(event) => setMaintenanceForm((current) => ({ ...current, custom_description: event.target.value }))} placeholder="Optional staff-facing note/description." /></label>
              </>
            ) : null}
            {maintenanceForm.action !== "trait_grant_only" ? (

            <label>
              <span>Staff Reason</span>
              <textarea rows={3} value={maintenanceForm.reason} onChange={(event) => setMaintenanceForm((current) => ({ ...current, reason: event.target.value }))} placeholder="Required. Example: correcting discounted cost, wrong skill assigned, restricted lore approval." />
            </label>
            ) : null}
            {maintenanceForm.action !== "trait_grant_only" ? (

            <div className="actions"><button onClick={runMaintenanceAction}><ShieldCheck size={16} /> Run Selected Action</button></div>
            ) : null}
          </div>
        </div>

        <div className="card staff-trait-benefit-card" style={{ display: "none" }}>
          <div className="card-title-row">
            <div>
              <span className="activity-type-label">Trait / Origin Resolver</span>
              <h3>Apply Trait Benefit</h3>
              <p className="muted-text">
                Use this when an Origin or starting trait grants a free skill choice. Keystone grants it for 0 XP and logs the trait reason.
              </p>
            </div>
            <button className="ghost" onClick={loadTraitBenefitOptions}>
              <RefreshCw size={16} /> Refresh Options
            </button>
          </div>

          <div className="request-actions-panel staff-trait-benefit-form">
            <label>
              <span>OC</span>
              <select
                value={traitBenefitForm.character_id}
                onChange={(event) =>
                  setTraitBenefitForm((current) => ({ ...current, character_id: event.target.value }))
                }
              >
                <option value="">Select an OC</option>
                {traitBenefitCharacters.map((character: any) => (
                  <option key={character.character_id} value={character.character_id}>
                    {character.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Trait / Origin</span>
              <select
                value={traitBenefitForm.trait_slug}
                onChange={(event) =>
                  setTraitBenefitForm((current) => ({
                    ...current,
                    trait_slug: event.target.value,
                    skill_key: "",
                    reason: "",
                  }))
                }
              >
                <option value="">Select a trait</option>
                {traitBenefitTraits.map((trait: any) => (
                  <option key={trait.slug || trait.trait_id} value={trait.slug}>
                    {trait.name}{trait.tier ? ` / ${trait.tier}` : ""}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Free Skill</span>
              <select
                value={traitBenefitForm.skill_key}
                onChange={(event) =>
                  setTraitBenefitForm((current) => ({ ...current, skill_key: event.target.value }))
                }
              >
                <option value="">Select a skill</option>
                {traitFilteredSkills.map((skill: any) => (
                  <option key={skill.skill_key} value={skill.skill_key}>
                    {skill.name || skill.skill_key}{skill.tree ? ` / ${skill.tree}` : ""}{skill.cost !== undefined ? ` / ${skill.cost} XP normally` : ""}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Staff Note</span>
              <textarea
                rows={3}
                value={traitBenefitForm.reason}
                onChange={(event) =>
                  setTraitBenefitForm((current) => ({ ...current, reason: event.target.value }))
                }
                placeholder="Optional. If blank, Keystone uses the trait + skill as the reason."
              />
            </label>

            {selectedTraitBenefit ? (
              <div className="request-note-block">
                <span>Detected Benefit Rules</span>
                <p>
                  {traitAllowedSkillKeys.length > 0
                    ? `${traitAllowedSkillKeys.length} encoded eligible skill option(s).`
                    : "No encoded skill list yet, so staff may manually choose the valid beta benefit."}
                </p>
              </div>
            ) : null}

            <div className="actions">
              <button onClick={applyTraitBenefit}>
                <ShieldCheck size={16} /> Apply Trait Benefit
              </button>
            </div>
          </div>
        </div>

<div className="card staff-skill-override-card" style={{ display: "none" }}>
          <div className="card-title-row">
            <div>
              <span className="activity-type-label">Staff Override</span>
              <h3>Grant Skill Override</h3>
              <p className="muted-text">
                Use this for Origin traits, Magic Background, Mana Circuits, or other staff-approved exceptions that bypass normal skill requirements.
              </p>
            </div>
            <button className="ghost" onClick={loadSkillOverrideOptions}>
              <RefreshCw size={16} /> Refresh Options
            </button>
          </div>

          <div className="request-actions-panel staff-skill-override-form">
            <label>
              <span>OC</span>
              <select
                value={overrideForm.character_id}
                onChange={(event) =>
                  setOverrideForm((current) => ({ ...current, character_id: event.target.value }))
                }
              >
                <option value="">Select an OC</option>
                {overrideCharacters.map((character: any) => (
                  <option key={character.character_id} value={character.character_id}>
                    {character.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Skill</span>
              <select
                value={overrideForm.skill_key}
                onChange={(event) =>
                  setOverrideForm((current) => ({ ...current, skill_key: event.target.value }))
                }
              >
                <option value="">Select a skill</option>
                {overrideSkills.map((skill: any) => (
                  <option key={skill.skill_key} value={skill.skill_key}>
                    {skill.name || skill.skill_key}{skill.tree ? ` / ${skill.tree}` : ""}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Source / Trait</span>
              <input
                value={overrideForm.source_trait}
                onChange={(event) =>
                  setOverrideForm((current) => ({ ...current, source_trait: event.target.value }))
                }
                placeholder="Origin Trait, Magic Background, Mana Circuits..."
              />
            </label>

            <label>
              <span>Staff Reason</span>
              <textarea
                rows={3}
                value={overrideForm.reason}
                onChange={(event) =>
                  setOverrideForm((current) => ({ ...current, reason: event.target.value }))
                }
                placeholder="Example: Origin Trait grants one free Knowledge skill and bypasses normal purchase requirements."
              />
            </label>

            <div className="actions">
              <button onClick={grantSkillOverride}>
                <ShieldCheck size={16} /> Grant Skill Override
              </button>
            </div>
          </div>
        </div>
        
        </>)} {/* end actions tab */}

      </section>
    </RequireDiscord>
  );
}

function DerivedStatsCalculator() {
  const [stats, setStats] = useState<CoreStats>({ strength: 50, dexterity: 50, stamina: 50, magic_affinity: 50, mana: 50 });
  const [result, setResult] = useState<any>(null);
  const derived = result?.derived;

  async function calculate() {
    const data = await apiFetch("/api/combat/derived", { method: "POST", body: JSON.stringify(stats) });
    setResult(data);
  }

  return (
    <section className="grid">
      <div className="card">
        <h2>Derived Stats Calculator</h2>
        <div className="stats-grid">
          {(Object.keys(STAT_LABELS) as Array<keyof CoreStats>).map((key) => (
            <label key={key}>{STAT_LABELS[key]}<input type="number" min={0} value={stats[key]} onChange={(event) => setStats((prev) => ({ ...prev, [key]: Number(event.target.value) }))} /></label>
          ))}
        </div>
        <button onClick={calculate}><Calculator size={16} /> Calculate</button>
      </div>

      <div className="card">
        <h2>Results</h2>
        {!derived ? <p>Run the calculator to see derived stats.</p> : (
          <div className="summary vertical">
            {Object.entries(derived).map(([key, value]) => (
              <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

function StaffTraitGrantCard({
  discordId,
  selectedCharacterId,
  embedded = false,
  fallbackCharacters = [],
  fallbackTraits = [],
}: {
  discordId: string;
  selectedCharacterId?: string;
  embedded?: boolean;
  fallbackCharacters?: any[];
  fallbackTraits?: any[];
}) {
  const [characters, setCharacters] = useState<any[]>(fallbackCharacters || []);
  const [traits, setTraits] = useState<any[]>(fallbackTraits || []);
  const [characterId, setCharacterId] = useState(selectedCharacterId || "");
  const [traitId, setTraitId] = useState("");
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState<"grant" | "remove">("grant");
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);

  async function loadOptions() {
    setMessage("");

    try {
      const data = await apiFetch("/api/staff/trait-grants/options", {}, discordId);
      const loadedCharacters = Array.isArray(data.characters) && data.characters.length > 0 ? data.characters : fallbackCharacters;
      const loadedTraits = Array.isArray(data.traits) && data.traits.length > 0 ? data.traits : fallbackTraits;

      setCharacters(loadedCharacters || []);
      setTraits(loadedTraits || []);
    } catch (error: any) {
      setCharacters(fallbackCharacters || []);
      setTraits(fallbackTraits || []);
      setMessage(
        (fallbackTraits || []).length > 0
          ? "Using Staff Action Center trait options."
          : error.message || "Could not load trait grant options."
      );
    }
  }

  useEffect(() => {
    if (discordId) {
      loadOptions().catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  useEffect(() => {
    setCharacterId(selectedCharacterId || "");
  }, [selectedCharacterId]);

  useEffect(() => {
    if (fallbackCharacters?.length) {
      setCharacters(fallbackCharacters);
    }

    if (fallbackTraits?.length) {
      setTraits(fallbackTraits);
    }
  }, [fallbackCharacters, fallbackTraits]);

  async function submitTraitAction() {
    setMessage("");

    const targetCharacterId = selectedCharacterId || characterId;

    if (!targetCharacterId || !traitId) {
      setMessage("Choose an OC and a trait.");
      return;
    }

    if (!reason.trim()) {
      setMessage("Staff reason is required.");
      return;
    }

    setWorking(true);

    try {
      const endpoint = mode === "grant" ? "/api/staff/trait-grants/grant" : "/api/staff/trait-grants/remove";
      const data = await apiFetch(
        endpoint,
        {
          method: "POST",
          body: JSON.stringify({
            character_id: targetCharacterId,
            trait_id: traitId,
            reason,
          }),
        },
        discordId
      );

      setMessage(data.message || (mode === "grant" ? "Trait granted." : "Trait removed."));
      setReason("");
    } catch (error: any) {
      setMessage(error.message || "Could not update trait.");
    } finally {
      setWorking(false);
    }
  }

  function traitLabel(trait: any) {
    const bits = [
      trait.name || trait.slug || "Trait",
      trait.category,
      trait.tier !== undefined && trait.tier !== null ? `Tier ${trait.tier}` : "",
    ].filter(Boolean);

    return bits.join(" / ");
  }

  const selectedCharacterName =
    characters.find((character: any) => character.character_id === (selectedCharacterId || characterId))?.name ||
    "Selected Staff Action Center OC";

  const filteredTraits = traits.filter((trait) => {
    const q = search.trim().toLowerCase();

    if (!q) return true;

    return [trait.name, trait.slug, trait.category, trait.tier]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(q);
  });

  return (
    <div className={embedded ? "staff-trait-grant-inline" : "card"}>
      <div className="card-title-row">
        <div>
          <span className="activity-type-label">Staff Trait Tools</span>
          <h3>Grant / Remove Trait Only</h3>
          <p className="muted-text">
            Use this when staff needs to grant a trait by itself without granting a skill or running the trait-benefit workflow.
          </p>
        </div>

        <button className="ghost" onClick={loadOptions} disabled={working}>
          Refresh Options
        </button>
      </div>

      {message ? <p className="message">{message}</p> : null}

      <div className="request-actions-panel">
        <label>
          <span>Action</span>
          <select value={mode} onChange={(event) => setMode(event.target.value as "grant" | "remove")}>
            <option value="grant">Grant Trait</option>
            <option value="remove">Remove Trait</option>
          </select>
        </label>

        {selectedCharacterId ? (
          <div>
            <span>OC</span>
            <strong>{selectedCharacterName}</strong>
          </div>
        ) : (
          <label>
            <span>OC</span>
            <select value={characterId} onChange={(event) => setCharacterId(event.target.value)}>
              <option value="">Select an OC</option>
              {characters.map((character: any) => (
                <option key={character.character_id} value={character.character_id}>
                  {character.name || character.character_id}
                </option>
              ))}
            </select>
          </label>
        )}

        <label>
          <span>Search Traits</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search trait name, slug, category..."
          />
        </label>

        <label>
          <span>Trait</span>
          <select
            value={traitId}
            onChange={(event) => {
              const nextTraitId = event.target.value;
              const selectedTrait = traits.find((trait: any) => String(trait.trait_id) === String(nextTraitId));

              setTraitId(nextTraitId);

              if (selectedTrait) {
                setSearch(traitLabel(selectedTrait));
              }
            }}
          >
            <option value="">Select a trait</option>
            {filteredTraits.map((trait: any) => (
              <option key={trait.trait_id} value={trait.trait_id}>
                {traitLabel(trait)}
              </option>
            ))}
          </select>
        </label>

        {traits.length === 0 ? (
          <p className="muted-text">No traits loaded yet. Click Refresh Options or clear the search field.</p>
        ) : null}

        <label>
          <span>Staff Reason</span>
          <textarea
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Required. Example: staff-approved reward, correction, hidden trait approval, sheet cleanup."
          />
        </label>
      </div>

      <div className="actions">
        <button
          onClick={submitTraitAction}
          disabled={working || !(selectedCharacterId || characterId) || !traitId || !reason.trim()}
        >
          {working ? "Working..." : mode === "grant" ? "Grant Trait" : "Remove Trait"}
        </button>
      </div>
    </div>
  );
}

