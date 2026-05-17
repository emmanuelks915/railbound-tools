import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Calculator, Check, ClipboardList, Home, Package, RefreshCw, Save, Send, ShieldCheck, Sparkles, Store, UserRound, X, Users } from "lucide-react";
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

type Tab = "home" | "activity" | "planner" | "oc" | "inventory" | "shops" | "skills" | "rp" | "staff" | "combat" | "registry" | "register" | "manage_oc" | "qa";

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

  useEffect(() => {
    localStorage.setItem("railbound_discord_id", discordId);
  }, [discordId]);

  useEffect(() => {
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
  }

  const tabs = [
    ["home", Home, "Dashboard"],

    ["planner", Calculator, "XP Planner"],
    ["oc", UserRound, "OC"],
    ["manage_oc", UserRound, "Manage OC"],
    ["skills", Sparkles, "Skills"],
    ["inventory", Package, "Inventory"],
    ["shops", Store, "Shops"],
    ["rp", ClipboardList, "RP Hub"],
    ["register", UserRound, "Register OC"],
    ["registry", Users, "OC Registry"],
    ["staff", ShieldCheck, "Staff"],
    ["activity", ClipboardList, "Activity"],
    ["qa", ClipboardList, "QA Checklist"],
    ["combat", ClipboardList, "Derived Stats"],
  ] as const;

    const permissions = usePermissions(discordId);

  if (tab && !canUseTab(permissions, tab)) {
    setTab("dashboard");
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
                    <div className="auth-user">
            {authUser?.avatar_url ? (
              <img
                src={authUser.avatar_url}
                alt="Discord avatar"
                className="auth-avatar"
              />
            ) : null}

            <span>{authUser ? "Logged in with Discord" : "Login"}</span>

            <strong>
              {authUser
                ? authUser.global_name || authUser.username || authUser.discord_id || discordId
                : "Use Discord OAuth"}
            </strong>

            {authUser?.username ? (
              <small>@{authUser.username}</small>
            ) : discordId ? (
              <small>Discord ID: {discordId}</small>
            ) : null}
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
        {tabs.filter(([key]) => canUseTab(permissions, key as Tab))
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
      {tab === "qa" && <StaffOnly discordId={discordId}><ProductionQADashboard discordId={discordId} jump={setTab} /></StaffOnly>}
      {tab === "planner" && <Planner discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "oc" && <OCDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} jump={setTab} />}
      {tab === "manage_oc" && <ManageOCDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "inventory" && <InventoryDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "shops" && <ShopDashboard discordId={discordId} />}
      {tab === "skills" && <SkillsDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "rp" && <RpHubDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "register" && <OCRegistrationDashboard discordId={discordId} jump={setTab} />}
      {tab === "registry" && <OCRegistry discordId={discordId} />}
      {tab === "staff" && <StaffOnly discordId={discordId}><StaffQueue discordId={discordId} /></StaffOnly>}
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
      .then(setPermissions)
      .catch(() =>
        setPermissions({
          is_logged_in: Boolean(discordId),
          is_staff: false,
          is_admin: false,
          allowed_tabs: [],
        })
      );
  }, [discordId]);

  return permissions;
}

function canUseTab(permissions: any, tab: Tab) {
  const allowedTabs = permissions?.allowed_tabs || [];

  if (!allowedTabs.length) {
    return !["staff", "qa", "activity"].includes(String(tab));
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
    return (
      <section className="card muted-card">
        <h2>Login required</h2>
        <p>Please use Login with Discord to access Railbound Tools. Your account is used to load your characters, requests, staff access, and activity history.</p>
      </section>
    );
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
    const suffix = discordId ? `?discord_id=${encodeURIComponent(discordId)}` : "";
    const data = await apiFetch(`/api/characters${suffix}`, {}, discordId);
    setCharacters(data.characters || []);
    if (!selectedCharacterId && data.characters?.[0]?.character_id) {
      setSelectedCharacterId(data.characters[0].character_id);
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
    setData(d);
    if (!selectedCharacterId && d.characters?.[0]?.character_id) {
      setSelectedCharacterId(d.characters[0].character_id);
    }
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
            <button onClick={() => jump("shops")}><Store size={16} /> Manage Shops</button>
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
      const data = await apiFetch(`/api/characters?discord_id=${discordId}`, {}, discordId);
      const rows = Array.isArray(data) ? data : data.characters || data.data || [];
      setCharacters(rows);

      if (!selectedCharacterId && rows.length > 0) {
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
      const result = await apiFetch(`/api/characters?discord_id=${discordId}`, {}, discordId);
      const rows = Array.isArray(result) ? result : result.characters || result.data || [];
      setCharacters(rows);

      if (!selectedCharacterId && rows.length > 0) {
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
                <div>
                  <span className="activity-type-label">{itemBadge(item)}</span>
                  <h3>{item.name || "Unnamed Item"}</h3>
                </div>
                <strong className="inventory-quantity">×{item.quantity ?? 1}</strong>
              </div>

              {item.description ? <p className="muted-text">{item.description}</p> : null}

              <div className="inventory-item-meta">
                <span>Type: {item.type || "Item"}</span>
                {item.source ? <span>Source: {item.source}</span> : null}
                {item.is_locked ? <span>Locked</span> : null}
                {item.is_equipped ? <span>Equipped</span> : null}
              </div>
            </div>
          ))}
        </div>
      </section>
    </RequireDiscord>
  );
}



function ShopDashboard({ discordId }

) {
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState("");
  const [shop, setShop] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [uploadingImage, setUploadingImage] = useState(false);
  const [createOpen, setCreateOpen] = useState(true);
  const [listingForm, setListingForm] = useState({
    name: "",
    description: "",
    image_url: "",
    price: "0",
    stock: "",
    item_type: "item",
    item_class: "",
    recipe_link: "",
    special_effects: "",
    usage_information: "",
    stat_limits: "",
  });

  function updateListingForm(key: string, value: string) {
    setListingForm((current) => ({ ...current, [key]: value }));
  }

  function resetListingForm() {
    setListingForm({
      name: "",
      description: "",
      image_url: "",
      price: "0",
      stock: "",
      item_type: "item",
      item_class: "",
      recipe_link: "",
      special_effects: "",
      usage_information: "",
      stat_limits: "",
    });
  }

  async function loadShops() {
    setMessage("");
    const data = await apiFetch("/api/shops/mine", {}, discordId);
    setShops(data.shops || []);
    if (!shopId && data.shops?.[0]?.company_id) setShopId(data.shops[0].company_id);
  }

  async function loadShop(id = shopId) {
    if (!id) return;
    setMessage("");
    const detail = await apiFetch(`/api/shops/${id}`, {}, discordId);
    setShop(detail.shop);
    const itemData = await apiFetch(`/api/shops/${id}/items`, {}, discordId);
    setItems(itemData.items || []);
  }

  useEffect(() => { if (discordId) loadShops().catch((error) => setMessage(error.message)); /* eslint-disable-next-line */ }, [discordId]);
  useEffect(() => { if (discordId && shopId) loadShop(shopId).catch((error) => setMessage(error.message)); /* eslint-disable-next-line */ }, [shopId, discordId]);

  async function saveShop() {
    if (!shop) return;
    await apiFetch(`/api/shops/${shop.company_id}`, {
      method: "PATCH",
      body: JSON.stringify({
        name: shop.name,
        description: shop.shop_description,
        banner_url: shop.shop_banner_url,
        logo_url: shop.shop_logo_url,
      }),
    }, discordId);
    setMessage("Shop storefront saved.");
    await loadShop(shop.company_id);
  }

  async function uploadListingImage(file: File | null) {
    if (!file) return;

    if (!shopId) {
      setMessage("Select a shop before uploading an image.");
      return;
    }

    setUploadingImage(true);
    setMessage("Uploading image...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const headers = new Headers();
      if (ALLOW_DEV_LOGIN && discordId) headers.set("X-Discord-Id", discordId);

      const response = await fetch(`${API_BASE}/api/shops/${shopId}/images`, {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Image upload failed.");
      }

      updateListingForm("image_url", data.url || "");
      setMessage("Image uploaded and attached to the listing.");
    } catch (error: any) {
      setMessage(error.message || "Image upload failed.");
    } finally {
      setUploadingImage(false);
    }
  }

  async function createListing() {
    if (!shopId) {
      setMessage("Select a shop first.");
      return;
    }

    if (!listingForm.name.trim()) {
      setMessage("Listing name is required.");
      return;
    }

    const price = Number(listingForm.price || 0);
    if (Number.isNaN(price) || price < 0) {
      setMessage("Price must be 0 or higher.");
      return;
    }

    const stockText = listingForm.stock.trim();
    const stock = stockText === "" ? null : Number(stockText);
    if (stock !== null && (Number.isNaN(stock) || stock < 0)) {
      setMessage("Stock must be blank, 0, or higher.");
      return;
    }

    await apiFetch(`/api/shops/${shopId}/items`, {
      method: "POST",
      body: JSON.stringify({
        name: listingForm.name.trim(),
        description: listingForm.description.trim(),
        image_url: listingForm.image_url.trim() || null,
        price,
        stock,
        item_type: listingForm.item_type.trim() || "item",
        item_class: listingForm.item_class.trim() || null,
        recipe_link: listingForm.recipe_link.trim() || null,
        special_effects: listingForm.special_effects.trim() || null,
        usage_information: listingForm.usage_information.trim() || null,
        stat_limits: listingForm.stat_limits.trim() || null,
      }),
    }, discordId);

    setMessage("Listing submitted for staff review.");
    resetListingForm();
    await loadShop(shopId);
  }

  async function patchItem(itemId: string, patch: Record<string, unknown>) {
    await apiFetch(`/api/shops/items/${itemId}`, { method: "PATCH", body: JSON.stringify(patch) }, discordId);
    setMessage("Listing updated.");
    await loadShop();
  }

  function listingStatus(item: any) {
    const raw = String(item.review_status || (item.is_active ? "active" : "draft"));
    return raw.replaceAll("_", " ").toUpperCase();
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid shop-grid">
        <div className="card">
          <div className="card-title-row">
            <h2>Shop Dashboard</h2>
            <button className="ghost" onClick={loadShops}><RefreshCw size={16} /> Refresh</button>
          </div>
          {message && <p className="message">{message}</p>}
          <label>
            Shop
            <select value={shopId} onChange={(e) => setShopId(e.target.value)}>
              <option value="">Select a shop</option>
              {shops.map((s) => <option key={s.company_id} value={s.company_id}>{s.name} {s.member_role ? `• ${s.member_role}` : ""}</option>)}
            </select>
          </label>

          {shop ? (
            <>
              <label>Storefront Name<input value={shop.name || ""} onChange={(e) => setShop({ ...shop, name: e.target.value })} /></label>
              <label>Description<textarea value={shop.shop_description || ""} onChange={(e) => setShop({ ...shop, shop_description: e.target.value })} /></label>
              <label>Banner URL<input value={shop.shop_banner_url || ""} onChange={(e) => setShop({ ...shop, shop_banner_url: e.target.value })} /></label>
              <label>Logo URL<input value={shop.shop_logo_url || ""} onChange={(e) => setShop({ ...shop, shop_logo_url: e.target.value })} /></label>
              <button onClick={saveShop}><Save size={16} /> Save Storefront</button>
            </>
          ) : <p>Select a shop to manage.</p>}
        </div>

        <div className="card shop-create-card">
          <div className="card-title-row">
            <div>
              <h2>Create Listing</h2>
              <p className="muted-text">Submit a shop item for staff review. Approved listings can be published to Discord later.</p>
            </div>
            <button className="ghost" onClick={() => setCreateOpen((value) => !value)}>
              {createOpen ? "Collapse" : "Open"}
            </button>
          </div>

          {createOpen ? (
            <>
              <div className="shop-create-grid">
                <label>
                  Item Name
                  <input value={listingForm.name} onChange={(e) => updateListingForm("name", e.target.value)} placeholder="Clockwork Grapple" />
                </label>
                <label>
                  Price
                  <input type="number" min={0} value={listingForm.price} onChange={(e) => updateListingForm("price", e.target.value)} />
                </label>
                <label>
                  Stock
                  <input type="number" min={0} value={listingForm.stock} onChange={(e) => updateListingForm("stock", e.target.value)} placeholder="Blank = unlimited" />
                </label>
                <label>
                  Item Type
                  <input value={listingForm.item_type} onChange={(e) => updateListingForm("item_type", e.target.value)} placeholder="item, service, recipe..." />
                </label>
                <label>
                  Item Class
                  <input value={listingForm.item_class} onChange={(e) => updateListingForm("item_class", e.target.value)} placeholder="Weapon, Armor, Consumable..." />
                </label>
                <label>
                  Image URL
                  <input value={listingForm.image_url} onChange={(e) => updateListingForm("image_url", e.target.value)} placeholder="https://..." />
                </label>
                <label>
                  Upload Image
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    disabled={uploadingImage}
                    onChange={(e) => uploadListingImage(e.target.files?.[0] || null)}
                  />
                  <small>{uploadingImage ? "Uploading..." : "PNG, JPG, WEBP, or GIF. Max 8 MB."}</small>
                </label>
                <label className="full-span">
                  Description
                  <textarea value={listingForm.description} onChange={(e) => updateListingForm("description", e.target.value)} placeholder="What is this listing?" />
                </label>
                <label className="full-span">
                  Recipe / Sheet Link
                  <input value={listingForm.recipe_link} onChange={(e) => updateListingForm("recipe_link", e.target.value)} placeholder="Optional doc/sheet link" />
                </label>
                <label className="full-span">
                  Stat Limits
                  <textarea value={listingForm.stat_limits} onChange={(e) => updateListingForm("stat_limits", e.target.value)} placeholder="Optional stat requirements or limits..." />
                </label>
                <label className="full-span">
                  Special Effects
                  <textarea value={listingForm.special_effects} onChange={(e) => updateListingForm("special_effects", e.target.value)} placeholder="Optional effects..." />
                </label>
                <label className="full-span">
                  Usage Information
                  <textarea value={listingForm.usage_information} onChange={(e) => updateListingForm("usage_information", e.target.value)} placeholder="How should players use this?" />
                </label>
              </div>

              {listingForm.image_url.trim() ? (
                <div className="shop-image-preview">
                  <span>Image Preview</span>
                  <img src={listingForm.image_url.trim()} alt="Listing preview" />
                </div>
              ) : null}

              <div className="actions">
                <button className="primary-action" onClick={createListing}><Send size={16} /> Submit Listing</button>
                <button className="ghost secondary-action" onClick={resetListingForm}>Clear Form</button>
              </div>
            </>
          ) : null}
        </div>

        <div className="card shop-listings-card">
          <h2>Listings</h2>
          <div className="item-list">
            {items.length === 0 ? <p>No listings found.</p> : null}
            {items.map((item) => (
              <div className="request-card shop-listing-card" key={item.item_id}>
                {item.image_url ? <img src={item.image_url} alt="" /> : null}
                <div>
                  <h3>{item.name}</h3>
                  <p>Price: {item.price} • Stock: {item.stock ?? "∞"} • Status: {listingStatus(item)}</p>
                  {item.description ? <small>{item.description}</small> : null}
                </div>
                <div className="inline-form compact-inline">
                  <input type="number" defaultValue={item.stock ?? 0} onBlur={(e) => patchItem(item.item_id, { stock: Number(e.target.value) })} />
                  <button className="ghost" onClick={() => patchItem(item.item_id, { is_active: false })}>Unpublish</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </RequireDiscord>
  );
}

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
  const [form, setForm] = useState({
    name: "",
    sheet_url: "",
    occupation: "",
    affiliation: "",
    blurb: "",
    origin_trait_id: "",
    trait_ids: [] as string[],
  });

  async function loadOptions() {
    const data = await apiFetch("/api/oc-registration/options", {}, discordId);
    setOptions(data);
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

      const data = await apiFetch(
        "/api/oc-registration/characters",
        {
          method: "POST",
          body: JSON.stringify(form),
        },
        discordId
      );

      setCreatedCharacterId(data.character_id || "");
      setSuccessMessage(data.message || "OC registered.");
      setMessage("");

      setForm({
        name: "",
        sheet_url: "",
        occupation: "",
        affiliation: "",
        blurb: "",
        origin_trait_id: "",
        trait_ids: [],
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
                onChange={(event) => updateForm({ origin_trait_id: event.target.value })}
              >
                <option value="">No Origin selected</option>
                {originTraits.map((trait: any) => (
                  <option value={trait.trait_id} key={trait.trait_id}>
                    {traitLabel(trait)}
                  </option>
                ))}
              </select>
            </label>

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
            <button onClick={() => loadRegistry()}>Search</button>
          </div>

          {message && <p className="message">{message}</p>}
        </div>

        <div className="registry-layout registry-layout-v2 registry-polish-layout">
          <div className="registry-list card">
            <div className="card-title-row">
              <h3>Roster</h3>
              <span className="pill">{characters.length} citizens</span>
            </div>

            <div className="registry-card-scroll">
              {characters.length === 0 ? <p className="muted-text">No citizens found yet.</p> : null}

              {characters.map((character) => (
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
      title: "Access & Login",
      items: [
        "Open Railway frontend on desktop",
        "Open Railway frontend on mobile",
        "Login with Discord",
        "Confirm Dev Login is not visible publicly",
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


function StaffQueue({ discordId }: { discordId: string }) {
  const [statRequests, setStatRequests] = useState<any[]>([]);
  const [skillRequests, setSkillRequests] = useState<any[]>([]);
  const [shopRequests, setShopRequests] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [activeQueue, setActiveQueue] = useState<"stats" | "skills" | "shops">("skills");

  async function loadRequests() {
    setMessage("");

    const stats = await apiFetch("/api/staff/stat-requests?status=pending", {}, discordId);
    setStatRequests(stats.requests || []);

    const skills = await apiFetch("/api/staff/skill-requests?status=pending", {}, discordId);
    setSkillRequests(skills.requests || []);

    const shops = await apiFetch("/api/staff/shop-items?status=pending_staff_review", {}, discordId);
    setShopRequests(shops.items || []);
  }

  useEffect(() => {
    if (discordId) loadRequests().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  async function actStat(requestId: string, action: "approve" | "deny") {
    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";

    await apiFetch(
      `/api/staff/stat-requests/${requestId}/${action}`,
      {
        method: "POST",
        body: JSON.stringify({ staff_note: note }),
      },
      discordId
    );

    setMessage(`Stat request ${action}d.`);
    await loadRequests();
  }

  async function actSkill(requestId: string, action: "approve" | "deny") {
    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";

    await apiFetch(
      `/api/staff/skill-requests/${requestId}/${action}`,
      {
        method: "POST",
        body: JSON.stringify({ staff_note: note }),
      },
      discordId
    );

    setMessage(`Skill request ${action}d.`);
    await loadRequests();
  }

  async function actShopItem(itemId: string, action: "approve" | "deny") {
    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";

    await apiFetch(
      `/api/staff/shop-items/${itemId}/${action}`,
      {
        method: "POST",
        body: JSON.stringify({ staff_note: note }),
      },
      discordId
    );

    setMessage(`Shop listing ${action}d.`);
    await loadRequests();
  }

  function checkPill(ok: boolean, label: string, badLabel?: string) {
    return (
      <span className={`review-check-pill ${ok ? "good" : "bad"}`}>
        {ok ? "✓" : "!"} {ok ? label : badLabel || label}
      </span>
    );
  }

  function skillRequestTitle(request: any) {
    return request.skill?.name || request.skill_key || "Unknown Skill";
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="staff-dashboard-v2">
        <div className="card staff-overview-card">
          <div className="card-title-row">
            <div>
              <h2>Staff Review Center</h2>
              <p className="muted-text">
                Review pending stat requests, skill purchases, and shop listings.
              </p>
            </div>
            <button className="ghost" onClick={loadRequests}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>

          {message && <p className="message">{message}</p>}

          <div className="staff-queue-tabs">
            <button className={activeQueue === "skills" ? "active" : ""} onClick={() => setActiveQueue("skills")}>
              Skill Requests <span>{skillRequests.length}</span>
            </button>
            <button className={activeQueue === "stats" ? "active" : ""} onClick={() => setActiveQueue("stats")}>
              Stat Requests <span>{statRequests.length}</span>
            </button>
            <button className={activeQueue === "shops" ? "active" : ""} onClick={() => setActiveQueue("shops")}>
              Shop Listings <span>{shopRequests.length}</span>
            </button>
          </div>
        </div>

        {activeQueue === "skills" ? (
          <div className="card staff-section-card">
            <div className="card-title-row">
              <div>
                <h2>Skill Request Queue</h2>
                <p className="muted-text">
                  Review skill prerequisites, XP, and ownership before approving.
                </p>
              </div>
              <span className="pill">{skillRequests.length} pending</span>
            </div>

            <div className="item-list skill-review-list">
              {skillRequests.length === 0 && <p>No pending skill requests.</p>}

              {skillRequests.map((request) => {
                const checks = request.review_checks || {};
                const safeToApprove = !!checks.safe_to_approve;

                return (
                  <div className={`request-card skill-review-card-v2 ${safeToApprove ? "safe" : "needs-review"}`} key={request.request_id}>
                    <div className="skill-review-header">
                      <div>
                        <div className="skill-review-eyebrow">
                          <span>{request.skill?.tree || "Unknown Tree"}</span>
                          <span>Tier {request.skill?.tier ?? "—"}</span>
                          <span>{checks.cost ?? request.cost ?? request.skill?.cost ?? 0} XP</span>
                        </div>
                        <h3>{skillRequestTitle(request)}</h3>
                        <p>
                          OC: <strong>{request.character?.name || "Unknown OC"}</strong>
                          {request.character?.user_id ? <> • Player: <strong>{request.character.user_id}</strong></> : null}
                        </p>
                      </div>
                      <span className={`pill ${safeToApprove ? "good" : "bad"}`}>
                        {safeToApprove ? "Safe to Approve" : "Needs Review"}
                      </span>
                    </div>

                    <div className="review-check-grid">
                      {checkPill(!!checks.has_enough_xp, `${checks.available_xp ?? 0} XP available`, `Needs ${checks.cost ?? request.cost ?? 0} XP`)}
                      {checkPill(!checks.already_owned, "Not owned", "Already owned")}
                      {checkPill(!!checks.skill_active, "Skill active", "Inactive / unreleased")}
                      {checkPill(!!checks.prerequisites_met, "Prereqs met", "Missing prereqs")}
                    </div>

                    {checks.prereq_names?.length ? (
                      <div className="skill-review-detail-box">
                        <strong>Prerequisites</strong>
                        <p>{checks.prereq_names.join(", ")}</p>
                      </div>
                    ) : (
                      <div className="skill-review-detail-box">
                        <strong>Prerequisites</strong>
                        <p>None listed.</p>
                      </div>
                    )}

                    {checks.missing_prereq_keys?.length ? (
                      <div className="skill-review-warning">
                        Missing: {checks.missing_prereq_keys.join(", ")}
                      </div>
                    ) : null}

                    {request.submitter_note ? (
                      <div className="skill-review-detail-box">
                        <strong>Player Note</strong>
                        <p>{request.submitter_note}</p>
                      </div>
                    ) : null}

                    <div className="actions">
                      <button disabled={!safeToApprove} onClick={() => actSkill(request.request_id, "approve")}>
                        <Check size={16} /> Approve
                      </button>
                      <button className="danger" onClick={() => actSkill(request.request_id, "deny")}>
                        <X size={16} /> Deny
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {activeQueue === "stats" ? (
          <div className="card staff-section-card">
            <h2>Stat Review Queue</h2>

            <div className="item-list">
              {statRequests.length === 0 && <p>No pending stat requests.</p>}

              {statRequests.map((request) => (
                <div className="request-card" key={request.request_id}>
                  <div>
                    <h3>{request.character?.name || "Unknown OC"}</h3>
                    <p>Total: {request.total_cost} XP</p>
                    {request.submitter_note && <p>Note: {request.submitter_note}</p>}
                  </div>

                  <ul>
                    {request.items.map((item: any) => (
                      <li key={item.item_id}>
                        {STAT_LABELS[item.stat_key as keyof CoreStats]}: {item.current_value} →{" "}
                        {item.target_value} ({item.cost} XP)
                      </li>
                    ))}
                  </ul>

                  <div className="actions">
                    <button onClick={() => actStat(request.request_id, "approve")}>
                      <Check size={16} /> Approve
                    </button>
                    <button className="danger" onClick={() => actStat(request.request_id, "deny")}>
                      <X size={16} /> Deny
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {activeQueue === "shops" ? (
          <div className="card staff-section-card staff-shop-review-card">
            <h2>Shop Listing Review Queue</h2>
            <p className="muted-text">
              Review submitted player shop listings before they go live.
            </p>

            <div className="item-list">
              {shopRequests.length === 0 && <p>No pending shop listings.</p>}

              {shopRequests.map((item) => (
                <div className="request-card shop-review-card" key={item.item_id}>
                  {item.image_url ? (
                    <img
                      className="shop-review-image"
                      src={item.image_url}
                      alt={item.name || "Shop item"}
                    />
                  ) : null}

                  <div>
                    <h3>{item.name}</h3>
                    <p>
                      Shop: {item.company?.name || "Unknown Shop"} • Price: {item.price} • Stock:{" "}
                      {item.stock ?? "∞"}
                    </p>

                    {item.item_type || item.item_class ? (
                      <p>
                        Type: {item.item_type || "—"} • Class: {item.item_class || "—"}
                      </p>
                    ) : null}

                    {item.description ? <p>{item.description}</p> : null}
                    {item.special_effects ? <p><strong>Effects:</strong> {item.special_effects}</p> : null}
                    {item.usage_information ? <p><strong>Usage:</strong> {item.usage_information}</p> : null}

                    {item.recipe_link ? (
                      <a href={item.recipe_link} target="_blank" rel="noreferrer">
                        Open recipe / sheet
                      </a>
                    ) : null}
                  </div>

                  <div className="actions">
                    <button onClick={() => actShopItem(item.item_id, "approve")}>
                      <Check size={16} /> Approve
                    </button>
                    <button className="danger" onClick={() => actShopItem(item.item_id, "deny")}>
                      <X size={16} /> Deny
                    </button>
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
