from __future__ import annotations

from pathlib import Path


MAIN_PATH = Path("frontend/src/main.tsx")
CSS_PATH = Path("frontend/src/styles.css")
SKILLS_PATH = Path("backend/app/routes/skills.py")

NEW_STAFF_QUEUE = 'function StaffQueue({ discordId }: { discordId: string }) {\n  const [statRequests, setStatRequests] = useState<any[]>([]);\n  const [skillRequests, setSkillRequests] = useState<any[]>([]);\n  const [shopRequests, setShopRequests] = useState<any[]>([]);\n  const [message, setMessage] = useState("");\n  const [activeQueue, setActiveQueue] = useState<"stats" | "skills" | "shops">("skills");\n\n  async function loadRequests() {\n    setMessage("");\n\n    const stats = await apiFetch("/api/staff/stat-requests?status=pending", {}, discordId);\n    setStatRequests(stats.requests || []);\n\n    const skills = await apiFetch("/api/staff/skill-requests?status=pending", {}, discordId);\n    setSkillRequests(skills.requests || []);\n\n    const shops = await apiFetch("/api/staff/shop-items?status=pending_staff_review", {}, discordId);\n    setShopRequests(shops.items || []);\n  }\n\n  useEffect(() => {\n    if (discordId) loadRequests().catch((error) => setMessage(error.message));\n    // eslint-disable-next-line react-hooks/exhaustive-deps\n  }, [discordId]);\n\n  async function actStat(requestId: string, action: "approve" | "deny") {\n    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";\n\n    await apiFetch(\n      `/api/staff/stat-requests/${requestId}/${action}`,\n      {\n        method: "POST",\n        body: JSON.stringify({ staff_note: note }),\n      },\n      discordId\n    );\n\n    setMessage(`Stat request ${action}d.`);\n    await loadRequests();\n  }\n\n  async function actSkill(requestId: string, action: "approve" | "deny") {\n    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";\n\n    await apiFetch(\n      `/api/staff/skill-requests/${requestId}/${action}`,\n      {\n        method: "POST",\n        body: JSON.stringify({ staff_note: note }),\n      },\n      discordId\n    );\n\n    setMessage(`Skill request ${action}d.`);\n    await loadRequests();\n  }\n\n  async function actShopItem(itemId: string, action: "approve" | "deny") {\n    const note = window.prompt(action === "approve" ? "Approval note?" : "Denial reason?") || "";\n\n    await apiFetch(\n      `/api/staff/shop-items/${itemId}/${action}`,\n      {\n        method: "POST",\n        body: JSON.stringify({ staff_note: note }),\n      },\n      discordId\n    );\n\n    setMessage(`Shop listing ${action}d.`);\n    await loadRequests();\n  }\n\n  function checkPill(ok: boolean, label: string, badLabel?: string) {\n    return (\n      <span className={`review-check-pill ${ok ? "good" : "bad"}`}>\n        {ok ? "✓" : "!"} {ok ? label : badLabel || label}\n      </span>\n    );\n  }\n\n  function skillRequestTitle(request: any) {\n    return request.skill?.name || request.skill_key || "Unknown Skill";\n  }\n\n  return (\n    <RequireDiscord discordId={discordId}>\n      <section className="staff-dashboard-v2">\n        <div className="card staff-overview-card">\n          <div className="card-title-row">\n            <div>\n              <h2>Staff Review Center</h2>\n              <p className="muted-text">\n                Review pending stat requests, skill purchases, and shop listings.\n              </p>\n            </div>\n            <button className="ghost" onClick={loadRequests}>\n              <RefreshCw size={16} /> Refresh\n            </button>\n          </div>\n\n          {message && <p className="message">{message}</p>}\n\n          <div className="staff-queue-tabs">\n            <button className={activeQueue === "skills" ? "active" : ""} onClick={() => setActiveQueue("skills")}>\n              Skill Requests <span>{skillRequests.length}</span>\n            </button>\n            <button className={activeQueue === "stats" ? "active" : ""} onClick={() => setActiveQueue("stats")}>\n              Stat Requests <span>{statRequests.length}</span>\n            </button>\n            <button className={activeQueue === "shops" ? "active" : ""} onClick={() => setActiveQueue("shops")}>\n              Shop Listings <span>{shopRequests.length}</span>\n            </button>\n          </div>\n        </div>\n\n        {activeQueue === "skills" ? (\n          <div className="card staff-section-card">\n            <div className="card-title-row">\n              <div>\n                <h2>Skill Request Queue</h2>\n                <p className="muted-text">\n                  Review skill prerequisites, XP, and ownership before approving.\n                </p>\n              </div>\n              <span className="pill">{skillRequests.length} pending</span>\n            </div>\n\n            <div className="item-list skill-review-list">\n              {skillRequests.length === 0 && <p>No pending skill requests.</p>}\n\n              {skillRequests.map((request) => {\n                const checks = request.review_checks || {};\n                const safeToApprove = !!checks.safe_to_approve;\n\n                return (\n                  <div className={`request-card skill-review-card-v2 ${safeToApprove ? "safe" : "needs-review"}`} key={request.request_id}>\n                    <div className="skill-review-header">\n                      <div>\n                        <div className="skill-review-eyebrow">\n                          <span>{request.skill?.tree || "Unknown Tree"}</span>\n                          <span>Tier {request.skill?.tier ?? "—"}</span>\n                          <span>{checks.cost ?? request.cost ?? request.skill?.cost ?? 0} XP</span>\n                        </div>\n                        <h3>{skillRequestTitle(request)}</h3>\n                        <p>\n                          OC: <strong>{request.character?.name || "Unknown OC"}</strong>\n                          {request.character?.user_id ? <> • Player: <strong>{request.character.user_id}</strong></> : null}\n                        </p>\n                      </div>\n                      <span className={`pill ${safeToApprove ? "good" : "bad"}`}>\n                        {safeToApprove ? "Safe to Approve" : "Needs Review"}\n                      </span>\n                    </div>\n\n                    <div className="review-check-grid">\n                      {checkPill(!!checks.has_enough_xp, `${checks.available_xp ?? 0} XP available`, `Needs ${checks.cost ?? request.cost ?? 0} XP`)}\n                      {checkPill(!checks.already_owned, "Not owned", "Already owned")}\n                      {checkPill(!!checks.skill_active, "Skill active", "Inactive / unreleased")}\n                      {checkPill(!!checks.prerequisites_met, "Prereqs met", "Missing prereqs")}\n                    </div>\n\n                    {checks.prereq_names?.length ? (\n                      <div className="skill-review-detail-box">\n                        <strong>Prerequisites</strong>\n                        <p>{checks.prereq_names.join(", ")}</p>\n                      </div>\n                    ) : (\n                      <div className="skill-review-detail-box">\n                        <strong>Prerequisites</strong>\n                        <p>None listed.</p>\n                      </div>\n                    )}\n\n                    {checks.missing_prereq_keys?.length ? (\n                      <div className="skill-review-warning">\n                        Missing: {checks.missing_prereq_keys.join(", ")}\n                      </div>\n                    ) : null}\n\n                    {request.submitter_note ? (\n                      <div className="skill-review-detail-box">\n                        <strong>Player Note</strong>\n                        <p>{request.submitter_note}</p>\n                      </div>\n                    ) : null}\n\n                    <div className="actions">\n                      <button disabled={!safeToApprove} onClick={() => actSkill(request.request_id, "approve")}>\n                        <Check size={16} /> Approve\n                      </button>\n                      <button className="danger" onClick={() => actSkill(request.request_id, "deny")}>\n                        <X size={16} /> Deny\n                      </button>\n                    </div>\n                  </div>\n                );\n              })}\n            </div>\n          </div>\n        ) : null}\n\n        {activeQueue === "stats" ? (\n          <div className="card staff-section-card">\n            <h2>Stat Review Queue</h2>\n\n            <div className="item-list">\n              {statRequests.length === 0 && <p>No pending stat requests.</p>}\n\n              {statRequests.map((request) => (\n                <div className="request-card" key={request.request_id}>\n                  <div>\n                    <h3>{request.character?.name || "Unknown OC"}</h3>\n                    <p>Total: {request.total_cost} XP</p>\n                    {request.submitter_note && <p>Note: {request.submitter_note}</p>}\n                  </div>\n\n                  <ul>\n                    {request.items.map((item: any) => (\n                      <li key={item.item_id}>\n                        {STAT_LABELS[item.stat_key as keyof CoreStats]}: {item.current_value} →{" "}\n                        {item.target_value} ({item.cost} XP)\n                      </li>\n                    ))}\n                  </ul>\n\n                  <div className="actions">\n                    <button onClick={() => actStat(request.request_id, "approve")}>\n                      <Check size={16} /> Approve\n                    </button>\n                    <button className="danger" onClick={() => actStat(request.request_id, "deny")}>\n                      <X size={16} /> Deny\n                    </button>\n                  </div>\n                </div>\n              ))}\n            </div>\n          </div>\n        ) : null}\n\n        {activeQueue === "shops" ? (\n          <div className="card staff-section-card staff-shop-review-card">\n            <h2>Shop Listing Review Queue</h2>\n            <p className="muted-text">\n              Review submitted player shop listings before they go live.\n            </p>\n\n            <div className="item-list">\n              {shopRequests.length === 0 && <p>No pending shop listings.</p>}\n\n              {shopRequests.map((item) => (\n                <div className="request-card shop-review-card" key={item.item_id}>\n                  {item.image_url ? (\n                    <img\n                      className="shop-review-image"\n                      src={item.image_url}\n                      alt={item.name || "Shop item"}\n                    />\n                  ) : null}\n\n                  <div>\n                    <h3>{item.name}</h3>\n                    <p>\n                      Shop: {item.company?.name || "Unknown Shop"} • Price: {item.price} • Stock:{" "}\n                      {item.stock ?? "∞"}\n                    </p>\n\n                    {item.item_type || item.item_class ? (\n                      <p>\n                        Type: {item.item_type || "—"} • Class: {item.item_class || "—"}\n                      </p>\n                    ) : null}\n\n                    {item.description ? <p>{item.description}</p> : null}\n                    {item.special_effects ? <p><strong>Effects:</strong> {item.special_effects}</p> : null}\n                    {item.usage_information ? <p><strong>Usage:</strong> {item.usage_information}</p> : null}\n\n                    {item.recipe_link ? (\n                      <a href={item.recipe_link} target="_blank" rel="noreferrer">\n                        Open recipe / sheet\n                      </a>\n                    ) : null}\n                  </div>\n\n                  <div className="actions">\n                    <button onClick={() => actShopItem(item.item_id, "approve")}>\n                      <Check size={16} /> Approve\n                    </button>\n                    <button className="danger" onClick={() => actShopItem(item.item_id, "deny")}>\n                      <X size={16} /> Deny\n                    </button>\n                  </div>\n                </div>\n              ))}\n            </div>\n          </div>\n        ) : null}\n      </section>\n    </RequireDiscord>\n  );\n}'
CSS_APPEND = '/* Staff skill review cards v2 */\n\n.staff-dashboard-v2 {\n  display: grid;\n  gap: 1.1rem;\n}\n\n.staff-overview-card,\n.staff-section-card {\n  grid-column: 1 / -1;\n}\n\n.staff-queue-tabs {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 0.65rem;\n  margin-top: 1rem;\n}\n\n.staff-queue-tabs button {\n  display: inline-flex;\n  align-items: center;\n  gap: 0.55rem;\n  border: 0;\n  border-radius: 16px;\n  padding: 0.8rem 1rem;\n  font-weight: 900;\n  background: rgba(255, 255, 255, 0.62);\n  color: #2c1f16;\n  cursor: pointer;\n}\n\n.staff-queue-tabs button.active {\n  background: #2f6f73;\n  color: white;\n}\n\n.staff-queue-tabs button span {\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  min-width: 1.6rem;\n  min-height: 1.6rem;\n  border-radius: 999px;\n  background: rgba(0, 0, 0, 0.1);\n}\n\n.skill-review-list {\n  margin-top: 1rem;\n}\n\n.skill-review-card-v2 {\n  border-left: 5px solid rgba(156, 61, 61, 0.5);\n}\n\n.skill-review-card-v2.safe {\n  border-left-color: rgba(47, 143, 91, 0.65);\n}\n\n.skill-review-header {\n  display: flex;\n  justify-content: space-between;\n  gap: 1rem;\n  align-items: flex-start;\n}\n\n.skill-review-eyebrow {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 0.45rem;\n  margin-bottom: 0.45rem;\n}\n\n.skill-review-eyebrow span {\n  border-radius: 999px;\n  padding: 0.35rem 0.55rem;\n  background: rgba(47, 111, 115, 0.11);\n  color: rgba(44, 31, 22, 0.72);\n  font-size: 0.75rem;\n  font-weight: 900;\n}\n\n.review-check-grid {\n  display: grid;\n  grid-template-columns: repeat(4, minmax(0, 1fr));\n  gap: 0.55rem;\n  margin: 0.85rem 0;\n}\n\n.review-check-pill {\n  border-radius: 14px;\n  padding: 0.65rem 0.7rem;\n  font-size: 0.78rem;\n  font-weight: 900;\n  background: rgba(255, 255, 255, 0.6);\n  border: 1px solid rgba(61, 51, 43, 0.08);\n}\n\n.review-check-pill.good {\n  color: #2f6f5b;\n}\n\n.review-check-pill.bad {\n  color: #9c3d3d;\n}\n\n.skill-review-detail-box {\n  border-radius: 16px;\n  padding: 0.75rem 0.85rem;\n  background: rgba(255, 255, 255, 0.52);\n  border: 1px solid rgba(61, 51, 43, 0.08);\n  margin-top: 0.65rem;\n}\n\n.skill-review-detail-box strong {\n  display: block;\n  margin-bottom: 0.25rem;\n}\n\n.skill-review-detail-box p {\n  margin: 0;\n}\n\n.skill-review-warning {\n  margin-top: 0.65rem;\n  border-radius: 16px;\n  padding: 0.75rem 0.85rem;\n  background: rgba(156, 61, 61, 0.12);\n  color: #7e2d2d;\n  font-weight: 900;\n}\n\n@media (max-width: 900px) {\n  .skill-review-header {\n    flex-direction: column;\n  }\n\n  .review-check-grid {\n    grid-template-columns: 1fr;\n  }\n}\n'
BACKEND_LIST_SKILL_REQUESTS = 'def _skill_prereq_keys(prerequisites: Any) -> list[str]:\n    if not prerequisites:\n        return []\n\n    if isinstance(prerequisites, list):\n        out: list[str] = []\n\n        for item in prerequisites:\n            if isinstance(item, str):\n                out.append(item)\n            elif isinstance(item, dict):\n                value = (\n                    item.get("skill_key")\n                    or item.get("skill")\n                    or item.get("key")\n                    or item.get("prereq_key")\n                )\n                if value:\n                    out.append(str(value))\n\n        return out\n\n    if isinstance(prerequisites, dict):\n        raw = (\n            prerequisites.get("skills")\n            or prerequisites.get("skill_keys")\n            or prerequisites.get("requires")\n            or prerequisites.get("prerequisites")\n            or prerequisites.get("required_skills")\n            or []\n        )\n\n        if isinstance(raw, str):\n            return [raw]\n\n        if isinstance(raw, list):\n            out: list[str] = []\n\n            for item in raw:\n                if isinstance(item, str):\n                    out.append(item)\n                elif isinstance(item, dict):\n                    value = (\n                        item.get("skill_key")\n                        or item.get("skill")\n                        or item.get("key")\n                        or item.get("prereq_key")\n                    )\n                    if value:\n                        out.append(str(value))\n\n            return out\n\n    if isinstance(prerequisites, str):\n        cleaned = prerequisites.strip()\n\n        if not cleaned or cleaned.lower() in {"none", "n/a", "na"}:\n            return []\n\n        # Keep loose prose prereqs visible as text, but do not treat them as a skill_key.\n        return []\n\n    return []\n\n\n@router.get("/staff/skill-requests")\ndef list_skill_requests(\n    status: str = Query(default="pending"),\n    actor_discord_id: int | None = Depends(actor_from_header),\n):\n    require_staff(actor_discord_id)\n\n    sb = get_supabase()\n    gid = get_guild_id()\n\n    req_res = (\n        sb.table("skill_purchase_requests")\n        .select("*")\n        .eq("guild_id", gid)\n        .eq("status", status)\n        .order("created_at", desc=True)\n        .limit(100)\n        .execute()\n    )\n\n    reqs = sb_data(req_res) or []\n    out = []\n\n    for req in reqs:\n        character_id = req.get("character_id")\n        skill_key = req.get("skill_key")\n\n        char_res = (\n            sb.table("characters")\n            .select("character_id,name,user_id")\n            .eq("guild_id", gid)\n            .eq("character_id", character_id)\n            .limit(1)\n            .execute()\n        )\n\n        skill_res = (\n            sb.table("skill_definitions")\n            .select("*")\n            .eq("guild_id", gid)\n            .eq("skill_key", skill_key)\n            .limit(1)\n            .execute()\n        )\n\n        character = (sb_data(char_res) or [None])[0]\n        skill = (sb_data(skill_res) or [None])[0]\n\n        wallet = None\n        owned_keys: list[str] = []\n        missing_prereqs: list[str] = []\n        prereq_keys: list[str] = []\n        prereq_names: list[str] = []\n\n        if character_id:\n            try:\n                wallet = get_wallet(sb, UUID(str(character_id)), gid)\n            except Exception:\n                wallet = None\n\n            owned_res = (\n                sb.table("oc_skills")\n                .select("skill_key")\n                .eq("guild_id", gid)\n                .eq("character_id", character_id)\n                .execute()\n            )\n            owned_rows = sb_data(owned_res) or []\n            owned_keys = [\n                str(row.get("skill_key"))\n                for row in owned_rows\n                if row.get("skill_key")\n            ]\n\n        if skill:\n            prereq_keys = _skill_prereq_keys(skill.get("prerequisites"))\n            missing_prereqs = [\n                key\n                for key in prereq_keys\n                if key not in owned_keys\n            ]\n\n            if prereq_keys:\n                prereq_res = (\n                    sb.table("skill_definitions")\n                    .select("skill_key,name")\n                    .eq("guild_id", gid)\n                    .in_("skill_key", prereq_keys)\n                    .execute()\n                )\n                prereq_rows = sb_data(prereq_res) or []\n                prereq_name_lookup = {\n                    row.get("skill_key"): row.get("name")\n                    for row in prereq_rows\n                }\n                prereq_names = [\n                    prereq_name_lookup.get(key) or key\n                    for key in prereq_keys\n                ]\n\n        available_xp = int((wallet or {}).get("available_xp") or 0)\n        cost = int(req.get("cost") or (skill or {}).get("cost") or 0)\n        already_owned = skill_key in owned_keys\n        skill_active = bool((skill or {}).get("is_active", True))\n        has_enough_xp = available_xp >= cost\n        prerequisites_met = len(missing_prereqs) == 0\n\n        review_checks = {\n            "skill_active": skill_active,\n            "already_owned": already_owned,\n            "has_enough_xp": has_enough_xp,\n            "available_xp": available_xp,\n            "cost": cost,\n            "prerequisites_met": prerequisites_met,\n            "prereq_keys": prereq_keys,\n            "prereq_names": prereq_names,\n            "missing_prereq_keys": missing_prereqs,\n            "owned_skill_count": len(owned_keys),\n            "safe_to_approve": skill_active and not already_owned and has_enough_xp and prerequisites_met,\n        }\n\n        out.append(\n            {\n                **req,\n                "character": character,\n                "skill": skill,\n                "wallet": wallet,\n                "review_checks": review_checks,\n            }\n        )\n\n    return {"requests": out}'


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


def find_matching(text: str, open_index: int, open_char: str, close_char: str) -> int:
    depth = 0
    in_string = None
    escaped = False
    in_line_comment = False
    in_block_comment = False

    for i in range(open_index, len(text)):
        handled, in_string, escaped, in_line_comment, in_block_comment = _skip_string_or_comment(
            text, i, in_string, escaped, in_line_comment, in_block_comment
        )
        if handled:
            continue

        ch = text[i]

        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return i

    raise RuntimeError("Could not find matching closing character.")


def find_ts_function_block(text: str, function_name: str) -> tuple[int, int]:
    start = text.find(f"function {function_name}(")
    if start == -1:
        raise RuntimeError(f"Could not find function {function_name}.")

    open_paren = text.find("(", start)
    close_paren = find_matching(text, open_paren, "(", ")")
    body_start = text.find("{", close_paren)

    if body_start == -1:
        raise RuntimeError(f"Could not find body for function {function_name}.")

    body_end = find_matching(text, body_start, "{", "}") + 1
    return start, body_end


def find_py_function_block(text: str, function_name: str) -> tuple[int, int]:
    marker = f"def {function_name}("
    start = text.find(marker)
    if start == -1:
        raise RuntimeError(f"Could not find Python function {function_name}.")

    next_decorator = text.find("\n@router.", start + 1)
    next_def = text.find("\ndef ", start + 1)

    candidates = [idx for idx in [next_decorator, next_def] if idx != -1]
    end = min(candidates) + 1 if candidates else len(text)

    return start, end


def ensure_any_import(text: str) -> str:
    if "from typing import Any" in text:
        return text

    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("from __future__"):
            insert_at = i + 1
            break

    lines.insert(insert_at, "from typing import Any")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def patch_backend() -> None:
    text = SKILLS_PATH.read_text(encoding="utf-8")
    original = text

    text = ensure_any_import(text)

    # Remove older helper if present to avoid duplicates.
    if "def _skill_prereq_keys(" in text:
        helper_start, helper_end = find_py_function_block(text, "_skill_prereq_keys")
        text = text[:helper_start] + text[helper_end:]

    start, end = find_py_function_block(text, "list_skill_requests")
    text = text[:start] + BACKEND_LIST_SKILL_REQUESTS + text[end:]

    if text != original:
        SKILLS_PATH.with_suffix(".py.staff_skill_cards_v2.bak").write_text(original, encoding="utf-8")
        SKILLS_PATH.write_text(text, encoding="utf-8")
        print("Patched backend/app/routes/skills.py")
    else:
        print("backend/app/routes/skills.py unchanged")


def patch_frontend() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text

    start, end = find_ts_function_block(text, "StaffQueue")
    text = text[:start] + NEW_STAFF_QUEUE + text[end:]

    if text != original:
        MAIN_PATH.with_suffix(".tsx.staff_skill_cards_v2.bak").write_text(original, encoding="utf-8")
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
    else:
        print("frontend/src/main.tsx unchanged")

    css = CSS_PATH.read_text(encoding="utf-8")

    if "Staff skill review cards v2" not in css:
        CSS_PATH.with_suffix(".css.staff_skill_cards_v2.bak").write_text(css, encoding="utf-8")
        CSS_PATH.write_text(css.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n", encoding="utf-8")
        print("Patched frontend/src/styles.css")
    else:
        print("Staff skill review cards CSS already present")


def main() -> None:
    patch_backend()
    patch_frontend()
    print("")
    print("Done. Restart backend/frontend and check Staff tab > Skill Requests.")


if __name__ == "__main__":
    main()
