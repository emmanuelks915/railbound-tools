function ActivityDashboard({ discordId }: { discordId: string }) {
  const [activities, setActivities] = useState<any[]>([]);
  const [totals, setTotals] = useState<any>({});
  const [message, setMessage] = useState("");
  const [kindFilter, setKindFilter] = useState("all");

  async function load() {
    setMessage("");

    const data = await apiFetch("/api/activity/recent?limit=120", {}, discordId);

    setActivities(data.activities || []);
    setTotals(data.totals || {});
  }

  useEffect(() => {
    if (discordId) {
      load().catch((error) => setMessage(error.message));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discordId]);

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

  function statusClass(status: string | undefined) {
    const normalized = String(status || "").toLowerCase();

    if (
      normalized.includes("approved") ||
      normalized.includes("paid") ||
      normalized.includes("active") ||
      normalized.includes("published")
    ) {
      return "good";
    }

    if (
      normalized.includes("denied") ||
      normalized.includes("rejected") ||
      normalized.includes("error") ||
      normalized.includes("failed")
    ) {
      return "bad";
    }

    return "";
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

            <button className="ghost" onClick={load}>
              <RefreshCw size={16} /> Refresh
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

          <div className="item-list activity-list">
            {visibleActivities.length === 0 ? <p>No recent activity found.</p> : null}

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
                    {activity.actor_discord_id ? ` • Actor: ${activity.actor_discord_id}` : ""}
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
        </div>
      </section>
    </RequireDiscord>
  );
}
