import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Calculator,
  Check,
  ClipboardList,
  Home,
  Package,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
  Sparkles,
  Store,
  UserRound,
  X,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

type Tab = "home" | "planner" | "oc" | "inventory" | "shops" | "skills" | "staff" | "combat";

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
  if (discordId) headers.set("X-Discord-Id", discordId);

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
  const [discordId, setDiscordId] = useState(() => localStorage.getItem("railbound_discord_id") || "");
  const [selectedCharacterId, setSelectedCharacterId] = useState(() => localStorage.getItem("railbound_character_id") || "");

  useEffect(() => {
    localStorage.setItem("railbound_discord_id", discordId);
  }, [discordId]);

  useEffect(() => {
    localStorage.setItem("railbound_character_id", selectedCharacterId);
  }, [selectedCharacterId]);

  const tabs = [
    ["home", Home, "Dashboard"],
    ["planner", Calculator, "XP Planner"],
    ["oc", UserRound, "OC"],
    ["inventory", Package, "Inventory"],
    ["shops", Store, "Shops"],
    ["skills", Sparkles, "Skills"],
    ["staff", ShieldCheck, "Staff"],
    ["combat", ClipboardList, "Derived Stats"],
  ] as const;

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

        <label className="discord-id-box">
          <span>Testing Login</span>
          <input
            value={discordId}
            onChange={(event) => setDiscordId(event.target.value)}
            placeholder="Paste Discord ID for local testing"
          />
        </label>
      </section>

      <nav className="tabs">
        {tabs.map(([key, Icon, label]) => (
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
      {tab === "planner" && <Planner discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "oc" && <OCDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "inventory" && <InventoryDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "shops" && <ShopDashboard discordId={discordId} />}
      {tab === "skills" && <SkillsDashboard discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />}
      {tab === "staff" && <StaffQueue discordId={discordId} />}
      {tab === "combat" && <DerivedStatsCalculator />}
    </main>
  );
}

function RequireDiscord({ discordId, children }: { discordId: string; children: React.ReactNode }) {
  if (!discordId) {
    return (
      <section className="card muted-card">
        <h2>Testing login needed</h2>
        <p>Paste your Discord ID in the top-right box for local testing. This will become Discord OAuth before public launch.</p>
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
            <button onClick={() => jump("shops")}><Store size={16} /> Manage Shops</button>
            <button onClick={() => jump("staff")}><ShieldCheck size={16} /> Staff Queue</button>
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

function OCDashboard({ discordId, selectedCharacterId, setSelectedCharacterId }: { discordId: string; selectedCharacterId: string; setSelectedCharacterId: (id: string) => void }) {
  const [summary, setSummary] = useState<any>(null);
  const [message, setMessage] = useState("");

  async function load() {
    if (!selectedCharacterId) return;
    setMessage("");
    const data = await apiFetch(`/api/characters/${selectedCharacterId}/summary`, {}, discordId);
    setSummary(data);
  }

  useEffect(() => {
    if (selectedCharacterId && discordId) load().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCharacterId, discordId]);

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid">
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

function InventoryDashboard({ discordId, selectedCharacterId, setSelectedCharacterId }: { discordId: string; selectedCharacterId: string; setSelectedCharacterId: (id: string) => void }) {
  const [entries, setEntries] = useState<any[]>([]);
  const [loadouts, setLoadouts] = useState<any[]>([]);
  const [activeLoadout, setActiveLoadout] = useState<string | null>(null);
  const [newLoadoutName, setNewLoadoutName] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    if (!selectedCharacterId) return;
    setMessage("");
    const inv = await apiFetch(`/api/characters/${selectedCharacterId}/inventory`, {}, discordId);
    setEntries(inv.entries || []);
    const lo = await apiFetch(`/api/characters/${selectedCharacterId}/loadouts`, {}, discordId);
    setLoadouts(lo.loadouts || []);
    setActiveLoadout(lo.active_loadout_name || null);
  }

  useEffect(() => {
    if (selectedCharacterId && discordId) load().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCharacterId, discordId]);

  async function saveSnapshot() {
    if (!selectedCharacterId) return;
    if (!newLoadoutName.trim()) {
      setMessage("Name your loadout first.");
      return;
    }
    await apiFetch(`/api/characters/${selectedCharacterId}/loadouts`, {
      method: "POST",
      body: JSON.stringify({ name: newLoadoutName.trim() }),
    }, discordId);
    setNewLoadoutName("");
    setMessage("Loadout saved from current inventory.");
    await load();
  }

  async function setActive(name: string | null) {
    await apiFetch(`/api/characters/${selectedCharacterId}/active-loadout`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }, discordId);
    setMessage(name ? `Active loadout set to ${name}.` : "Active loadout cleared.");
    await load();
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid">
        <div className="card">
          <div className="card-title-row">
            <h2>Inventory</h2>
            <button className="ghost" onClick={load}><RefreshCw size={16} /> Refresh</button>
          </div>
          <CharacterSelect discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />
          {message && <p className="message">{message}</p>}
          <div className="item-list">
            {entries.length === 0 ? <p>Inventory is empty or no OC selected.</p> : null}
            {entries.map((entry) => (
              <div className="item-card" key={entry.item_id}>
                <h3>{entry.item?.name || "Unknown Item"} x{entry.qty}</h3>
                <p>Class: {entry.item?.item_class || "—"} • WU: {entry.item?.wu ?? "—"}</p>
                {entry.item?.sheet_url ? <a href={entry.item.sheet_url} target="_blank" rel="noreferrer">Open sheet</a> : null}
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Loadouts</h2>
          <p className="muted-text">Save the OC's current inventory as a named loadout, then mark one active for missions.</p>
          <div className="inline-form">
            <input value={newLoadoutName} onChange={(e) => setNewLoadoutName(e.target.value)} placeholder="Forest Run" />
            <button onClick={saveSnapshot}><Save size={16} /> Save</button>
          </div>
          <div className="item-list">
            {loadouts.length === 0 ? <p>No saved loadouts.</p> : null}
            {loadouts.map((lo) => (
              <div className="request-card" key={lo.loadout_name}>
                <div>
                  <h3>{activeLoadout === lo.loadout_name ? "⭐ " : ""}{lo.loadout_name}</h3>
                  <p>{Object.keys(lo.items || {}).length} item types</p>
                </div>
                <div className="actions">
                  <button className="ghost" onClick={() => setActive(lo.loadout_name)}>Set Active</button>
                  {activeLoadout === lo.loadout_name ? <button className="danger" onClick={() => setActive(null)}>Clear</button> : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </RequireDiscord>
  );
}

function ShopDashboard({ discordId }: { discordId: string }) {
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState("");
  const [shop, setShop] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [message, setMessage] = useState("");

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

  async function patchItem(itemId: string, patch: Record<string, unknown>) {
    await apiFetch(`/api/shops/items/${itemId}`, { method: "PATCH", body: JSON.stringify(patch) }, discordId);
    setMessage("Listing updated.");
    await loadShop();
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid">
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

        <div className="card">
          <h2>Listings</h2>
          <div className="item-list">
            {items.length === 0 ? <p>No listings found.</p> : null}
            {items.map((item) => (
              <div className="request-card" key={item.item_id}>
                <div>
                  <h3>{item.name}</h3>
                  <p>Price: {item.price} • Stock: {item.stock ?? "∞"} • Status: {item.review_status || (item.is_active ? "ACTIVE" : "DRAFT")}</p>
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
  const [wallet, setWallet] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [treeFilter, setTreeFilter] = useState("all");

  async function load() {
    setMessage("");
    const catalog = await apiFetch("/api/skills", {}, discordId);
    setSkills(catalog.skills || []);
    if (selectedCharacterId) {
      const mine = await apiFetch(`/api/characters/${selectedCharacterId}/skills`, {}, discordId);
      setOwnedKeys(mine.owned_keys || []);
      setWallet(mine.wallet);
    }
  }

  useEffect(() => { if (discordId) load().catch((error) => setMessage(error.message)); /* eslint-disable-next-line */ }, [discordId, selectedCharacterId]);

  const trees = useMemo(() => ["all", ...Array.from(new Set(skills.map((s) => String(s.tree || "General"))))], [skills]);
  const visibleSkills = skills.filter((s) => treeFilter === "all" || s.tree === treeFilter);

  async function requestSkill(skillKey: string) {
    if (!selectedCharacterId) { setMessage("Select an OC first."); return; }
    await apiFetch("/api/skill-requests", {
      method: "POST",
      body: JSON.stringify({
        character_id: selectedCharacterId,
        skill_key: skillKey,
        requested_by_discord_id: Number(discordId),
        submitter_note: "Requested from Railbound Tools dashboard.",
      }),
    }, discordId);
    setMessage("Skill request submitted for staff review.");
    await load();
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="card">
        <div className="card-title-row">
          <h2>Skill Manager</h2>
          <button className="ghost" onClick={load}><RefreshCw size={16} /> Refresh</button>
        </div>
        <CharacterSelect discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />
        {wallet ? <div className="stat-strip"><span>Available XP</span><strong>{wallet.available_xp}</strong></div> : null}
        {message && <p className="message">{message}</p>}
        <label>Skill Tree<select value={treeFilter} onChange={(e) => setTreeFilter(e.target.value)}>{trees.map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
        <div className="item-list skill-grid">
          {visibleSkills.map((skill) => {
            const owned = ownedKeys.includes(skill.skill_key);
            return (
              <div className="item-card" key={skill.skill_key}>
                <div className="card-title-row">
                  <h3>{owned ? "✅ " : ""}{skill.name}</h3>
                  <span className="pill">{skill.cost} XP</span>
                </div>
                <p>{skill.description || "No description yet."}</p>
                {skill.chain ? <p><strong>Chain:</strong> {skill.chain}</p> : null}
                {skill.effects ? <p><strong>Effects:</strong> {skill.effects}</p> : null}
                <button disabled={owned} onClick={() => requestSkill(skill.skill_key)}><Send size={16} /> {owned ? "Owned" : "Request"}</button>
              </div>
            );
          })}
        </div>
      </section>
    </RequireDiscord>
  );
}

function StaffQueue({ discordId }: { discordId: string }) {
  const [statRequests, setStatRequests] = useState<any[]>([]);
  const [skillRequests, setSkillRequests] = useState<any[]>([]);
  const [message, setMessage] = useState("");

  async function loadRequests() {
    setMessage("");
    const stats = await apiFetch("/api/staff/stat-requests?status=pending", {}, discordId);
    setStatRequests(stats.requests || []);
    const skills = await apiFetch("/api/staff/skill-requests?status=pending", {}, discordId);
    setSkillRequests(skills.requests || []);
  }

  useEffect(() => {
    if (discordId) loadRequests().catch((error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  async function actStat(requestId: string, action: "approve" | "deny") {
    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";
    await apiFetch(`/api/staff/stat-requests/${requestId}/${action}`, { method: "POST", body: JSON.stringify({ staff_note: note }) }, discordId);
    setMessage(`Stat request ${action}d.`);
    await loadRequests();
  }

  async function actSkill(requestId: string, action: "approve" | "deny") {
    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";
    await apiFetch(`/api/staff/skill-requests/${requestId}/${action}`, { method: "POST", body: JSON.stringify({ staff_note: note }) }, discordId);
    setMessage(`Skill request ${action}d.`);
    await loadRequests();
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid">
        <div className="card">
          <div className="card-title-row">
            <h2>Stat Review Queue</h2>
            <button className="ghost" onClick={loadRequests}><RefreshCw size={16} /> Refresh</button>
          </div>
          {message && <p className="message">{message}</p>}
          <div className="item-list">
            {statRequests.length === 0 && <p>No pending stat requests.</p>}
            {statRequests.map((request) => (
              <div className="request-card" key={request.request_id}>
                <div>
                  <h3>{request.character?.name || "Unknown OC"}</h3>
                  <p>Requested by: {request.requested_by_discord_id}</p>
                  <p>Total: {request.total_cost} XP</p>
                  {request.submitter_note && <p>Note: {request.submitter_note}</p>}
                </div>
                <ul>
                  {request.items.map((item: any) => (
                    <li key={item.item_id}>{STAT_LABELS[item.stat_key as keyof CoreStats]}: {item.current_value} → {item.target_value} ({item.cost} XP)</li>
                  ))}
                </ul>
                <div className="actions">
                  <button onClick={() => actStat(request.request_id, "approve")}><Check size={16} /> Approve</button>
                  <button className="danger" onClick={() => actStat(request.request_id, "deny")}><X size={16} /> Deny</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Skill Review Queue</h2>
          <div className="item-list">
            {skillRequests.length === 0 && <p>No pending skill requests.</p>}
            {skillRequests.map((request) => (
              <div className="request-card" key={request.request_id}>
                <div>
                  <h3>{request.skill?.name || request.skill_key}</h3>
                  <p>OC: {request.character?.name || "Unknown OC"}</p>
                  <p>Cost: {request.cost} XP</p>
                </div>
                <div className="actions">
                  <button onClick={() => actSkill(request.request_id, "approve")}><Check size={16} /> Approve</button>
                  <button className="danger" onClick={() => actSkill(request.request_id, "deny")}><X size={16} /> Deny</button>
                </div>
              </div>
            ))}
          </div>
        </div>
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
