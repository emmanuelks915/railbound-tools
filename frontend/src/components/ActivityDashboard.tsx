function ActivityDashboard({ discordId }: { discordId: string }) {
  const [activities, setActivities] = useState<any[]>([]);
  const [totals, setTotals] = useState<any>({});
  const [message, setMessage] = useState("");
  const [kindFilter, setKindFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(80);

  async function load(currentLimit = limit) {
    setMessage("");
    setLoading(true);
    try {
      const data = await apiFetch(`/api/activity/recent?limit=${currentLimit}`, {}, discordId);
      setActivities(data.activities || []);
      setTotals(data.totals || {});
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (discordId) {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

  // Re-fetch when limit changes (triggered by Load More)
  useEffect(() => {
    if (discordId && limit > 80) {
      load(limit);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  const visibleActivities = activities.filter((activity) => {
    if (kindFilter === "all") return true;
    return activity.kind === kindFilter;
  });

  function kindLabel(kind: string) {
    return String(kind || "unknown").replaceAll("_", " ").toUpperCase();
  }

  function formatTime(value: string | undefined) {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  const GOOD_STATUSES = new Set(["approved", "paid", "active", "published", "complete", "completed"]);
  const BAD_STATUSES = new Set(["denied", "rejected", "error", "failed", "cancelled", "canceled"]);

  function statusClass(status: string | undefined) {
    const normalized = String(status || "").toLowerCase();
    if (GOOD_STATUSES.has(normalized)) return "good";
    if (BAD_STATUSES.has(normalized)) return "bad";
    return "";
  }

  function handleLoadMore() {
    const next = Math.min(limit + 80, 250);
    setLimit(next);
  }

  return (
    <RequireDiscord discordId={discordId}>
      <section className="grid activity-grid">
        <div className="card">
          <div className="card-title-row">
            <div>
              <h2>Recent Activity</h2>
              <p className="muted-text">
                Staff-facing timeline of approvals, shop listings, RP XP claims, and tool activity.
              </p>
            </div>
            <button className="ghost" onClick={() => load()} disabled={loading}>
              <RefreshCw size={16} className={loading ? "spin" : ""} />
              {loading ? "Loading..." : "Refresh"}
            </button>
          </div>

          {message && <p className="message">{message}</p>}

          <div className="summary">
            <div>
              <span>Total</span>
              <strong>{totals.count ?? 0}</strong>
            </div>
            <div>
              <span>Stats</span>
              <strong>{totals.stat_requests ?? 0}</strong>
            </div>
            <div>
              <span>Shops</span>
              <strong>{totals.shop_listings ?? 0}</strong>
            </div>
          </div>
          <div className="summary">
            <div>
              <span>RP Claims</span>
              <strong>{totals.rp_xp_claims ?? 0}</strong>
            </div>
            <div>
              <span>Skills</span>
              <strong>{totals.skill_requests ?? 0}</strong>
            </div>
            <div>
              <span>Showing</span>
              <strong>{visibleActivities.length}</strong>
            </div>
          </div>

          <label>
            Filter Activity
            <select value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}>
              <option value="all">All activity</option>
              <option value="stat_request">Stat requests</option>
              <option value="shop_listing">Shop listings</option>
              <option value="rp_xp_claim">RP XP claims</option>
              <option value="skill_request">Skill requests</option>
            </select>
          </label>
        </div>

        <div className="card activity-timeline-card">
          <h2>Timeline</h2>
          {loading && activities.length === 0 ? (
            <p className="muted-text">Loading activity...</p>
          ) : null}

          <div className="item-list activity-list">
            {!loading && visibleActivities.length === 0 ? (
              <p>No recent activity found.</p>
            ) : null}

            {visibleActivities.map((activity) => (
              <div className="request-card activity-card" key={activity.id}>
                <div>
                  <div className="activity-card-header">
                    <span className="pill">{kindLabel(activity.kind)}</span>
                    {activity.status ? (
                      <span className={`activity-status ${statusClass(activity.status)}`}>
                        {String(activity.status).replaceAll("_", " ").toUpperCase()}
                      </span>
                    ) : null}
                  </div>
                  <h3>{activity.title}</h3>
                  <p>{activity.description}</p>
                  <small>
                    {formatTime(activity.time)}
                    {activity.actor_discord_id
                      ? ` • Actor #${activity.actor_discord_id}`
                      : ""}
                  </small>
                  {activity.payout_status ? (
                    <small>
                      Payout:{" "}
                      <strong className={statusClass(activity.payout_status)}>
                        {String(activity.payout_status).replaceAll("_", " ").toUpperCase()}
                      </strong>
                    </small>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          {activities.length > 0 && limit < 250 ? (
            <div style={{ textAlign: "center", marginTop: "1rem" }}>
              <button className="ghost" onClick={handleLoadMore} disabled={loading}>
                {loading ? "Loading..." : `Load More (showing ${limit})`}
              </button>
            </div>
          ) : null}
        </div>
      </section>
    </RequireDiscord>
  );
}
