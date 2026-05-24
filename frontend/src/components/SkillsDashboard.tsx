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
