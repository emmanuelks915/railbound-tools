function ActivityDashboard({ discordId }: { discordId: string }) {
  const [events, setEvents] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(80);

  async function load(currentLimit = limit) {
    setMessage("");
    setLoading(true);
    try {
      const data = await apiFetch(`/api/activity/recent?limit=${currentLimit}`, {}, discordId);
      setEvents(data.events || []);
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (discordId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  useEffect(() => {
    if (discordId && limit > 80) load(limit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  const visibleEvents = events.filter((e) => typeFilter === "all" || e.type === typeFilter);

  function typeLabel(type: string) {
    const labels: Record<string, string> = {
      stats: "Stat Request",
      skills: "Skill Request",
      shops: "Shop Listing",
      xp: "XP Transaction",
    };
    return labels[type] || String(type || "Activity").replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  }

  function formatTime(value: string | undefined) {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  const GOOD = new Set(["approved", "paid", "active", "published", "complete", "completed"]);
  const BAD  = new Set(["denied", "rejected", "error", "failed", "cancelled", "canceled"]);

  function statusClass(status: string | undefined) {
    const s = String(status || "").toLowerCase();
    if (GOOD.has(s)) return "approved";
    if (BAD.has(s))  return "denied";
    return "pending";
  }

  function statusLabel(status: string | undefined) {
    return String(status || "unknown").replaceAll("_", " ").toUpperCase();
  }

  // Build actor display: prefer Discord username lookup, fall back to "Discord #ID"
  function actorLabel(event: any) {
    const id = event.actor_id || event.staff_id;
    if (!id) return null;
    return `Discord #${id}`;
  }

  function ocLabel(event: any) {
    const char = event.character;
    if (char?.name) return char.name;
    if (event.details?.character_name) return event.details.character_name;
    return null;
  }

  function detailPills(event: any) {
    const pills: { label: string; value: string }[] = [];
    const d = event.details || {};
    if (d.cost != null)   pills.push({ label: "Cost", value: `${d.cost} XP` });
    if (d.amount != null) pills.push({ label: "Amount", value: String(d.amount) });
    if (d.price != null)  pills.push({ label: "Price", value: String(d.price) });
    if (d.skill?.tree)    pills.push({ label: "Tree", value: d.skill.tree });
    if (d.reason)         pills.push({ label: "Reason", value: d.reason });
    if (d.note)           pills.push({ label: "Note", value: d.note });
    if (d.staff_note)     pills.push({ label: "Staff note", value: d.staff_note });
    return pills;
  }

  const typeCounts = events.reduce<Record<string, number>>((acc, e) => {
    acc[e.type] = (acc[e.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid activity-grid">
        <div className="card">
          <div className="card-title-row">
            <div>
              <h2>Recent Activity</h2>
              <p className="muted-text">Staff-facing timeline of stat requests, skill purchases, shop listings, and XP transactions.</p>
            </div>
            <button className="ghost" onClick={() => load()} disabled={loading}>
              <RefreshCw size={16} /> {loading ? "Loading..." : "Refresh"}
            </button>
          </div>

          {message && <p className="message">{message}</p>}

          <div className="summary">
            <div><span>Showing</span><strong>{visibleEvents.length}</strong></div>
            <div><span>Stats</span><strong>{typeCounts.stats ?? 0}</strong></div>
            <div><span>Skills</span><strong>{typeCounts.skills ?? 0}</strong></div>
          </div>
          <div className="summary">
            <div><span>Shop Listings</span><strong>{typeCounts.shops ?? 0}</strong></div>
            <div><span>XP</span><strong>{typeCounts.xp ?? 0}</strong></div>
          </div>

          <label>
            Filter
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="all">All activity</option>
              <option value="stats">Stat requests</option>
              <option value="skills">Skill requests</option>
              <option value="shops">Shop listings</option>
              <option value="xp">XP transactions</option>
            </select>
          </label>
        </div>

        <div className="card activity-timeline-card">
          <h2>Timeline</h2>
          {loading && events.length === 0 && <p className="muted-text">Loading activity...</p>}

          <div className="item-list activity-list">
            {!loading && visibleEvents.length === 0 && <p>No recent activity found.</p>}

            {visibleEvents.map((event, i) => {
              const oc   = ocLabel(event);
              const actor = actorLabel(event);
              const pills = detailPills(event);

              return (
                <div className="request-card activity-card" key={event.details?.request_id || `${event.type}-${i}`}>
                  <div className="activity-card-header">
                    <span className="pill">{typeLabel(event.type)}</span>
                    {event.status && (
                      <span className={`activity-status ${statusClass(event.status)}`}>
                        {statusLabel(event.status)}
                      </span>
                    )}
                  </div>

                  <h3 style={{ margin: "6px 0 2px" }}>{event.title}</h3>

                  {/* OC name + actor — human readable */}
                  <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", margin: "4px 0 6px", fontSize: "13px" }}>
                    {oc && (
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <UserRound size={12} style={{ opacity: 0.6 }} />
                        <strong>{oc}</strong>
                      </span>
                    )}
                    {actor && (
                      <span style={{ display: "flex", alignItems: "center", gap: "4px", opacity: 0.7 }}>
                        <ShieldCheck size={12} style={{ opacity: 0.6 }} />
                        {actor}
                      </span>
                    )}
                  </div>

                  {/* Detail pills */}
                  {pills.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "6px" }}>
                      {pills.map((p, j) => (
                        <span key={j} style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "99px", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                          <span style={{ opacity: 0.6 }}>{p.label}: </span>{p.value}
                        </span>
                      ))}
                    </div>
                  )}

                  <small style={{ opacity: 0.55 }}>{formatTime(event.timestamp)}</small>
                </div>
              );
            })}
          </div>

          {events.length > 0 && limit < 250 && (
            <div style={{ textAlign: "center", marginTop: "1rem" }}>
              <button className="ghost" onClick={() => setLimit(Math.min(limit + 80, 250))} disabled={loading}>
                {loading ? "Loading..." : `Load More (showing ${limit})`}
              </button>
            </div>
          )}
        </div>
      </section>
    </RequireDiscord>
  );
}
