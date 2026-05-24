from __future__ import annotations

from pathlib import Path


MAIN_PATH = Path("frontend/src/main.tsx")
CSS_PATH = Path("frontend/src/styles.css")

NEW_OC_DASHBOARD = 'function OCDashboard({ discordId, selectedCharacterId, setSelectedCharacterId }: { discordId: string; selectedCharacterId: string; setSelectedCharacterId: (id: string) => void }) {\n  const [summary, setSummary] = useState<any>(null);\n  const [ownedSkills, setOwnedSkills] = useState<any[]>([]);\n  const [skillRequests, setSkillRequests] = useState<any[]>([]);\n  const [message, setMessage] = useState("");\n\n  async function load() {\n    if (!selectedCharacterId) return;\n\n    setMessage("");\n\n    const [summaryData, catalogData, characterSkillData] = await Promise.all([\n      apiFetch(`/api/characters/${selectedCharacterId}/summary`, {}, discordId),\n      apiFetch("/api/skills", {}, discordId),\n      apiFetch(`/api/characters/${selectedCharacterId}/skills`, {}, discordId),\n    ]);\n\n    setSummary(summaryData);\n\n    const catalog = catalogData.skills || [];\n    const ownedKeys = characterSkillData.owned_keys || [];\n\n    const owned = ownedKeys\n      .map((skillKey: string) => {\n        const skill = catalog.find((entry: any) => entry.skill_key === skillKey);\n\n        return {\n          skill_key: skillKey,\n          ...(skill || {}),\n        };\n      })\n      .sort((a: any, b: any) => {\n        const treeCompare = String(a.tree || "").localeCompare(String(b.tree || ""));\n        if (treeCompare !== 0) return treeCompare;\n\n        const tierCompare = Number(a.tier ?? 0) - Number(b.tier ?? 0);\n        if (tierCompare !== 0) return tierCompare;\n\n        return String(a.name || a.skill_key).localeCompare(String(b.name || b.skill_key));\n      });\n\n    setOwnedSkills(owned);\n    setSkillRequests(characterSkillData.requests || []);\n  }\n\n  useEffect(() => {\n    if (selectedCharacterId && discordId) load().catch((error) => setMessage(error.message));\n    // eslint-disable-next-line react-hooks/exhaustive-deps\n  }, [selectedCharacterId, discordId]);\n\n  const groupedOwnedSkills = ownedSkills.reduce<Record<string, any[]>>((groups, skill) => {\n    const tree = String(skill.tree || "Other");\n    if (!groups[tree]) groups[tree] = [];\n    groups[tree].push(skill);\n    return groups;\n  }, {});\n\n  const pendingRequests = skillRequests.filter((request) => String(request.status || "").toLowerCase() === "pending");\n\n  return (\n    <RequireDiscord discordId={discordId}>\n      <section className="grid oc-dashboard-grid">\n        <div className="card">\n          <div className="card-title-row">\n            <h2>OC Dashboard</h2>\n            <button className="ghost" onClick={load}><RefreshCw size={16} /> Refresh</button>\n          </div>\n          <CharacterSelect discordId={discordId} selectedCharacterId={selectedCharacterId} setSelectedCharacterId={setSelectedCharacterId} />\n          {message && <p className="message">{message}</p>}\n          {summary && (\n            <>\n              <h3>{summary.character?.name}</h3>\n              <div className="stat-strip">\n                <span>Available XP</span>\n                <strong>{summary.wallet?.available_xp ?? 0}</strong>\n              </div>\n              <h3>Core Stats</h3>\n              <div className="mini-stat-grid">\n                {(Object.keys(STAT_LABELS) as Array<keyof CoreStats>).map((key) => (\n                  <div key={key} className="mini-stat"><span>{STAT_LABELS[key]}</span><strong>{summary.stats?.[key] ?? 0}</strong></div>\n                ))}\n              </div>\n            </>\n          )}\n        </div>\n\n        <div className="card oc-skills-card">\n          <div className="card-title-row">\n            <div>\n              <h2>Owned Skills</h2>\n              <p className="muted-text">A clean list of skills this OC already has.</p>\n            </div>\n            <span className="pill good">{ownedSkills.length} owned</span>\n          </div>\n\n          {!selectedCharacterId ? <p>Select an OC to view owned skills.</p> : null}\n\n          {selectedCharacterId && ownedSkills.length === 0 ? (\n            <p>No owned skills found yet. Requested skills will appear here after staff approval.</p>\n          ) : null}\n\n          {Object.entries(groupedOwnedSkills).map(([tree, skills]) => (\n            <div className="owned-skill-group" key={tree}>\n              <div className="owned-skill-group-heading">\n                <h3>{tree}</h3>\n                <span>{skills.length}</span>\n              </div>\n\n              <div className="owned-skill-list">\n                {skills.map((skill) => (\n                  <div className="owned-skill-row" key={skill.skill_key}>\n                    <div>\n                      <strong>{skill.name || skill.skill_key}</strong>\n                      <small>{skill.skill_key}</small>\n                    </div>\n                    <div className="owned-skill-meta">\n                      <span>Tier {skill.tier ?? "—"}</span>\n                      <span>{skill.cost ?? 0} XP</span>\n                    </div>\n                  </div>\n                ))}\n              </div>\n            </div>\n          ))}\n\n          {pendingRequests.length > 0 ? (\n            <div className="oc-pending-skills">\n              <h3>Pending Skill Requests</h3>\n              <div className="owned-skill-list">\n                {pendingRequests.slice(0, 6).map((request) => (\n                  <div className="owned-skill-row pending" key={request.request_id}>\n                    <div>\n                      <strong>{request.skill_key}</strong>\n                      <small>{request.request_id}</small>\n                    </div>\n                    <div className="owned-skill-meta">\n                      <span>Pending</span>\n                      <span>{request.cost ?? 0} XP</span>\n                    </div>\n                  </div>\n                ))}\n              </div>\n            </div>\n          ) : null}\n        </div>\n\n        <div className="card">\n          <h2>Derived Stats</h2>\n          {!summary ? <p>Select an OC to load derived stats.</p> : (\n            <div className="summary vertical">\n              {Object.entries(summary.derived || {}).map(([key, value]) => (\n                <div key={key}>\n                  <span>{key.replaceAll("_", " ")}</span>\n                  <strong>{String(value)}</strong>\n                </div>\n              ))}\n            </div>\n          )}\n        </div>\n      </section>\n    </RequireDiscord>\n  );\n}'
CSS_APPEND = '/* OC owned skills panel */\n\n.oc-dashboard-grid {\n  grid-template-columns: minmax(320px, 0.95fr) minmax(360px, 1.15fr);\n}\n\n.oc-skills-card {\n  min-height: 420px;\n}\n\n.owned-skill-group {\n  margin-top: 1rem;\n  border-top: 1px solid rgba(61, 51, 43, 0.1);\n  padding-top: 0.85rem;\n}\n\n.owned-skill-group-heading {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  gap: 1rem;\n  margin-bottom: 0.65rem;\n}\n\n.owned-skill-group-heading h3 {\n  margin: 0;\n}\n\n.owned-skill-group-heading span {\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  min-width: 2rem;\n  min-height: 2rem;\n  border-radius: 999px;\n  background: rgba(47, 111, 115, 0.12);\n  font-weight: 900;\n  color: #2f6f73;\n}\n\n.owned-skill-list {\n  display: grid;\n  gap: 0.55rem;\n}\n\n.owned-skill-row {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) auto;\n  gap: 1rem;\n  align-items: center;\n  border-radius: 18px;\n  padding: 0.8rem 0.9rem;\n  background: rgba(255, 255, 255, 0.58);\n  border: 1px solid rgba(61, 51, 43, 0.08);\n}\n\n.owned-skill-row.pending {\n  background: rgba(245, 198, 93, 0.14);\n}\n\n.owned-skill-row strong,\n.owned-skill-row small {\n  display: block;\n}\n\n.owned-skill-row small {\n  margin-top: 0.2rem;\n  color: rgba(44, 31, 22, 0.58);\n  overflow-wrap: anywhere;\n}\n\n.owned-skill-meta {\n  display: flex;\n  flex-direction: column;\n  align-items: flex-end;\n  gap: 0.2rem;\n  font-size: 0.82rem;\n  color: rgba(44, 31, 22, 0.66);\n  font-weight: 800;\n  white-space: nowrap;\n}\n\n.oc-pending-skills {\n  margin-top: 1.25rem;\n}\n\n@media (max-width: 980px) {\n  .oc-dashboard-grid {\n    grid-template-columns: 1fr;\n  }\n\n  .owned-skill-row {\n    grid-template-columns: 1fr;\n  }\n\n  .owned-skill-meta {\n    align-items: flex-start;\n  }\n}\n'
OLD_TABS = '    ["oc", UserRound, "OC"],\n    ["inventory", Package, "Inventory"],\n    ["shops", Store, "Shops"],\n    ["skills", Sparkles, "Skills"],'
NEW_TABS = '    ["oc", UserRound, "OC"],\n    ["skills", Sparkles, "Skills"],\n    ["inventory", Package, "Inventory"],\n    ["shops", Store, "Shops"],'


def _skip_string_or_comment(text: str, i: int, in_string, escaped, in_line_comment, in_block_comment):
    ch = text[i]
    nxt = text[i + 1] if i + 1 < len(text) else ""

    if in_line_comment:
        if ch == "\n":
            in_line_comment = False
        return True, in_string, escaped, in_line_comment, in_block_comment

    if in_block_comment:
        if ch == "*" and nxt == "/":
            in_block_comment = False
            return True, in_string, escaped, in_line_comment, in_block_comment
        return True, in_string, escaped, in_line_comment, in_block_comment

    if in_string:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == in_string:
            in_string = None
        return True, in_string, escaped, in_line_comment, in_block_comment

    if ch == "/" and nxt == "/":
        in_line_comment = True
        return True, in_string, escaped, in_line_comment, in_block_comment

    if ch == "/" and nxt == "*":
        in_block_comment = True
        return True, in_string, escaped, in_line_comment, in_block_comment

    if ch in ("'", '"', "`"):
        in_string = ch
        return True, in_string, escaped, in_line_comment, in_block_comment

    return False, in_string, escaped, in_line_comment, in_block_comment


def find_matching_paren(text: str, open_paren: int) -> int:
    depth = 0
    in_string = None
    escaped = False
    in_line_comment = False
    in_block_comment = False

    for i in range(open_paren, len(text)):
        handled, in_string, escaped, in_line_comment, in_block_comment = _skip_string_or_comment(
            text, i, in_string, escaped, in_line_comment, in_block_comment
        )
        if handled:
            continue

        ch = text[i]

        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i

    raise RuntimeError("Could not find closing function parameter parenthesis.")


def find_function_block(text: str, function_name: str) -> tuple[int, int]:
    start = text.find(f"function {function_name}(")
    if start == -1:
        raise RuntimeError(f"Could not find function {function_name}.")

    open_paren = text.find("(", start)
    close_paren = find_matching_paren(text, open_paren)

    body_start = text.find("{", close_paren)
    if body_start == -1:
        raise RuntimeError(f"Could not find body opening brace for {function_name}.")

    depth = 0
    in_string = None
    escaped = False
    in_line_comment = False
    in_block_comment = False

    for i in range(body_start, len(text)):
        handled, in_string, escaped, in_line_comment, in_block_comment = _skip_string_or_comment(
            text, i, in_string, escaped, in_line_comment, in_block_comment
        )
        if handled:
            continue

        ch = text[i]

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1

    raise RuntimeError(f"Could not find closing brace for {function_name}.")


def main() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text

    start, end = find_function_block(text, "OCDashboard")
    text = text[:start] + NEW_OC_DASHBOARD + text[end:]

    if OLD_TABS in text:
        text = text.replace(OLD_TABS, NEW_TABS, 1)

    if text != original:
        MAIN_PATH.with_suffix(".tsx.oc_skills_v2.bak").write_text(original, encoding="utf-8")
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
        print("Backup saved as frontend/src/main.tsx.oc_skills_v2.bak")
    else:
        print("frontend/src/main.tsx unchanged")

    css = CSS_PATH.read_text(encoding="utf-8")

    if "OC owned skills panel" not in css:
        CSS_PATH.with_suffix(".css.oc_skills_v2.bak").write_text(css, encoding="utf-8")
        CSS_PATH.write_text(css.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n", encoding="utf-8")
        print("Patched frontend/src/styles.css")
    else:
        print("OC owned skills CSS already present")

    print("")
    print("Done. Restart frontend and check OC tab.")


if __name__ == "__main__":
    main()
