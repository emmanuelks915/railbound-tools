from __future__ import annotations

from pathlib import Path


BACKEND_ROUTE = Path("backend/app/routes/activity.py")
FRONTEND_MAIN = Path("frontend/src/main.tsx")
FRONTEND_CSS = Path("frontend/src/styles.css")

ACTIVITY_ROUTE_V2 = 'from __future__ import annotations\n\nfrom datetime import datetime, time, timezone\nfrom typing import Any\n\nfrom fastapi import APIRouter, Depends, Query\n\nfrom app.security import actor_from_header, require_staff\nfrom app.services import get_guild_id, sb_data\nfrom app.supabase_client import get_supabase\n\nrouter = APIRouter(prefix="/api/activity", tags=["activity"])\n\n\ndef _as_list(value: Any) -> list[dict[str, Any]]:\n    rows = sb_data(value) or []\n    return rows if isinstance(rows, list) else []\n\n\ndef _timestamp(row: dict[str, Any]) -> str:\n    for key in ("created_at", "reviewed_at", "approved_at", "updated_at", "timestamp"):\n        value = row.get(key)\n        if value:\n            return str(value)\n\n    return datetime.now(timezone.utc).isoformat()\n\n\ndef _parse_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:\n    if not value:\n        return None\n\n    raw = value.strip()\n    if not raw:\n        return None\n\n    try:\n        if "T" not in raw and len(raw) == 10:\n            parsed_date = datetime.strptime(raw, "%Y-%m-%d").date()\n            parsed = datetime.combine(parsed_date, time.max if end_of_day else time.min)\n        else:\n            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))\n\n        if parsed.tzinfo is None:\n            parsed = parsed.replace(tzinfo=timezone.utc)\n\n        return parsed.astimezone(timezone.utc)\n    except Exception:\n        return None\n\n\ndef _event_datetime(event: dict[str, Any]) -> datetime | None:\n    timestamp = event.get("timestamp")\n\n    if not timestamp:\n        return None\n\n    try:\n        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))\n\n        if parsed.tzinfo is None:\n            parsed = parsed.replace(tzinfo=timezone.utc)\n\n        return parsed.astimezone(timezone.utc)\n    except Exception:\n        return None\n\n\ndef _in_date_window(event: dict[str, Any], start_dt: datetime | None, end_dt: datetime | None) -> bool:\n    event_dt = _event_datetime(event)\n\n    if event_dt is None:\n        return not start_dt and not end_dt\n\n    if start_dt and event_dt < start_dt:\n        return False\n\n    if end_dt and event_dt > end_dt:\n        return False\n\n    return True\n\n\ndef _safe_rows(sb, table: str, *, limit: int, order_by: str = "created_at") -> list[dict[str, Any]]:\n    try:\n        return _as_list(\n            sb.table(table)\n            .select("*")\n            .eq("guild_id", get_guild_id())\n            .order(order_by, desc=True)\n            .limit(limit)\n            .execute()\n        )\n    except Exception:\n        try:\n            return _as_list(\n                sb.table(table)\n                .select("*")\n                .eq("guild_id", get_guild_id())\n                .limit(limit)\n                .execute()\n            )\n        except Exception:\n            return []\n\n\ndef _character_lookup(sb, character_ids: set[str]) -> dict[str, dict[str, Any]]:\n    if not character_ids:\n        return {}\n\n    try:\n        rows = _as_list(\n            sb.table("characters")\n            .select("character_id,name,user_id")\n            .eq("guild_id", get_guild_id())\n            .in_("character_id", list(character_ids))\n            .execute()\n        )\n    except Exception:\n        return {}\n\n    return {str(row.get("character_id")): row for row in rows if row.get("character_id")}\n\n\ndef _skill_lookup(sb, skill_keys: set[str]) -> dict[str, dict[str, Any]]:\n    if not skill_keys:\n        return {}\n\n    try:\n        rows = _as_list(\n            sb.table("skill_definitions")\n            .select("skill_key,name,tree,tier,cost")\n            .eq("guild_id", get_guild_id())\n            .in_("skill_key", list(skill_keys))\n            .execute()\n        )\n    except Exception:\n        return {}\n\n    return {str(row.get("skill_key")): row for row in rows if row.get("skill_key")}\n\n\ndef _event(\n    *,\n    event_type: str,\n    title: str,\n    status: str | None,\n    timestamp: str,\n    actor_id: Any = None,\n    staff_id: Any = None,\n    character: dict[str, Any] | None = None,\n    details: dict[str, Any] | None = None,\n    raw: dict[str, Any] | None = None,\n) -> dict[str, Any]:\n    return {\n        "type": event_type,\n        "title": title,\n        "status": status,\n        "timestamp": timestamp,\n        "actor_id": actor_id,\n        "staff_id": staff_id,\n        "character": character,\n        "details": details or {},\n        "raw": raw or {},\n    }\n\n\n@router.get("/recent")\ndef recent_activity(\n    activity_type: str = Query(default="all", alias="type"),\n    limit: int = Query(default=100, ge=1, le=250),\n    start_date: str | None = Query(default=None),\n    end_date: str | None = Query(default=None),\n    actor_discord_id: int | None = Depends(actor_from_header),\n):\n    require_staff(actor_discord_id)\n\n    sb = get_supabase()\n\n    want_all = activity_type == "all"\n    events: list[dict[str, Any]] = []\n\n    fetch_limit = min(max(limit * 3, 100), 250)\n\n    stat_rows = _safe_rows(sb, "stat_upgrade_requests", limit=fetch_limit) if want_all or activity_type == "stats" else []\n    skill_rows = _safe_rows(sb, "skill_purchase_requests", limit=fetch_limit) if want_all or activity_type == "skills" else []\n    shop_rows = _safe_rows(sb, "shop_items", limit=fetch_limit) if want_all or activity_type == "shops" else []\n\n    xp_rows: list[dict[str, Any]] = []\n    if want_all or activity_type == "xp":\n        xp_rows = _safe_rows(sb, "oc_xp_transactions", limit=fetch_limit)\n        if not xp_rows:\n            xp_rows = _safe_rows(sb, "character_xp_transactions", limit=fetch_limit)\n        if not xp_rows:\n            xp_rows = _safe_rows(sb, "xp_transactions", limit=fetch_limit)\n\n    character_ids: set[str] = set()\n\n    for row in stat_rows + skill_rows:\n        if row.get("character_id"):\n            character_ids.add(str(row.get("character_id")))\n\n    for row in xp_rows:\n        if row.get("character_id"):\n            character_ids.add(str(row.get("character_id")))\n\n    character_map = _character_lookup(sb, character_ids)\n    skill_map = _skill_lookup(sb, {str(row.get("skill_key")) for row in skill_rows if row.get("skill_key")})\n\n    for row in stat_rows:\n        character = character_map.get(str(row.get("character_id")))\n        total_cost = row.get("total_cost") or row.get("cost") or 0\n        status = str(row.get("status") or "unknown")\n\n        events.append(\n            _event(\n                event_type="stats",\n                title=f"Stat request • {character.get(\'name\') if character else \'Unknown OC\'}",\n                status=status,\n                timestamp=_timestamp(row),\n                actor_id=row.get("requested_by_discord_id"),\n                staff_id=row.get("staff_discord_id") or row.get("reviewed_by_discord_id"),\n                character=character,\n                details={\n                    "cost": total_cost,\n                    "note": row.get("submitter_note"),\n                    "staff_note": row.get("staff_note") or row.get("denial_reason"),\n                    "request_id": row.get("request_id"),\n                },\n                raw=row,\n            )\n        )\n\n    for row in skill_rows:\n        character = character_map.get(str(row.get("character_id")))\n        skill = skill_map.get(str(row.get("skill_key")))\n        skill_name = skill.get("name") if skill else row.get("skill_key")\n        status = str(row.get("status") or "unknown")\n\n        events.append(\n            _event(\n                event_type="skills",\n                title=f"Skill request • {skill_name}",\n                status=status,\n                timestamp=_timestamp(row),\n                actor_id=row.get("requested_by_discord_id"),\n                staff_id=row.get("staff_discord_id") or row.get("reviewed_by_discord_id"),\n                character=character,\n                details={\n                    "skill_key": row.get("skill_key"),\n                    "skill": skill,\n                    "cost": row.get("cost") or (skill or {}).get("cost"),\n                    "note": row.get("submitter_note"),\n                    "staff_note": row.get("staff_note") or row.get("denial_reason"),\n                    "request_id": row.get("request_id"),\n                },\n                raw=row,\n            )\n        )\n\n    for row in shop_rows:\n        status = str(row.get("review_status") or row.get("status") or ("active" if row.get("is_active") else "unknown"))\n        events.append(\n            _event(\n                event_type="shops",\n                title=f"Shop listing • {row.get(\'name\') or \'Unnamed item\'}",\n                status=status,\n                timestamp=_timestamp(row),\n                actor_id=row.get("created_by_discord_id") or row.get("submitted_by_discord_id"),\n                staff_id=row.get("reviewed_by_discord_id") or row.get("approved_by"),\n                details={\n                    "item_id": row.get("item_id"),\n                    "price": row.get("price"),\n                    "stock": row.get("stock"),\n                    "item_type": row.get("item_type"),\n                    "item_class": row.get("item_class"),\n                    "note": row.get("submitter_note"),\n                    "staff_note": row.get("staff_note") or row.get("denial_reason"),\n                },\n                raw=row,\n            )\n        )\n\n    for row in xp_rows:\n        character = character_map.get(str(row.get("character_id")))\n        amount = row.get("amount") or row.get("xp_delta") or row.get("delta") or 0\n        tx_type = row.get("tx_type") or row.get("transaction_type") or row.get("kind") or "XP"\n\n        events.append(\n            _event(\n                event_type="xp",\n                title=f"XP {tx_type} • {character.get(\'name\') if character else \'Unknown OC\'}",\n                status=str(tx_type),\n                timestamp=_timestamp(row),\n                actor_id=row.get("actor_discord_id") or row.get("created_by_discord_id"),\n                character=character,\n                details={\n                    "amount": amount,\n                    "reason": row.get("reason") or row.get("note"),\n                    "reference_type": row.get("reference_type"),\n                    "reference_id": row.get("reference_id"),\n                },\n                raw=row,\n            )\n        )\n\n    start_dt = _parse_datetime(start_date, end_of_day=False)\n    end_dt = _parse_datetime(end_date, end_of_day=True)\n\n    events = [\n        event\n        for event in events\n        if _in_date_window(event, start_dt, end_dt)\n    ]\n\n    def sort_key(event: dict[str, Any]) -> str:\n        return str(event.get("timestamp") or "")\n\n    events.sort(key=sort_key, reverse=True)\n\n    return {\n        "events": events[:limit],\n        "count": len(events[:limit]),\n        "date_filter": {\n            "start_date": start_date,\n            "end_date": end_date,\n        },\n        "sources": {\n            "stats": len(stat_rows),\n            "skills": len(skill_rows),\n            "shops": len(shop_rows),\n            "xp": len(xp_rows),\n        },\n    }\n'
ACTIVITY_DASHBOARD_V2 = 'function ActivityDashboard({ discordId }: { discordId: string }) {\n  const [events, setEvents] = useState<any[]>([]);\n  const [sources, setSources] = useState<Record<string, number>>({});\n  const [activityType, setActivityType] = useState("all");\n  const [startDate, setStartDate] = useState("");\n  const [endDate, setEndDate] = useState("");\n  const [message, setMessage] = useState("");\n\n  async function loadActivity(type = activityType) {\n    setMessage("");\n\n    const params = new URLSearchParams({\n      type,\n      limit: "100",\n    });\n\n    if (startDate) params.set("start_date", startDate);\n    if (endDate) params.set("end_date", endDate);\n\n    const data = await apiFetch(`/api/activity/recent?${params.toString()}`, {}, discordId);\n\n    setEvents(data.events || []);\n    setSources(data.sources || {});\n  }\n\n  useEffect(() => {\n    if (discordId) loadActivity().catch((error) => setMessage(error.message));\n    // eslint-disable-next-line react-hooks/exhaustive-deps\n  }, [discordId, activityType, startDate, endDate]);\n\n  function setFilter(type: string) {\n    setActivityType(type);\n  }\n\n  function clearDates() {\n    setStartDate("");\n    setEndDate("");\n  }\n\n  function statusLabel(status: string | null | undefined) {\n    return String(status || "unknown").replaceAll("_", " ").toUpperCase();\n  }\n\n  function eventIcon(type: string) {\n    if (type === "skills") return "✨";\n    if (type === "stats") return "📈";\n    if (type === "shops") return "🛒";\n    if (type === "xp") return "⭐";\n    return "📝";\n  }\n\n  function formatDate(value: string | null | undefined) {\n    if (!value) return "Unknown time";\n\n    const parsed = new Date(value);\n    if (Number.isNaN(parsed.getTime())) return String(value);\n\n    return parsed.toLocaleString();\n  }\n\n  function actorText(event: any) {\n    const pieces = [];\n\n    if (event.actor_id) pieces.push(`Actor: ${event.actor_id}`);\n    if (event.staff_id) pieces.push(`Staff: ${event.staff_id}`);\n\n    return pieces.join(" • ");\n  }\n\n  return (\n    <RequireDiscord discordId={discordId}>\n      <section className="activity-page-v1">\n        <div className="card activity-hero-card">\n          <div className="card-title-row">\n            <div>\n              <h2>Recent Activity</h2>\n              <p className="muted-text">\n                A staff paper trail for stat requests, skill purchases, shop listings, and XP changes.\n              </p>\n            </div>\n            <button className="ghost" onClick={() => loadActivity()}>\n              <RefreshCw size={16} /> Refresh\n            </button>\n          </div>\n\n          {message && <p className="message">{message}</p>}\n\n          <div className="activity-filter-tabs">\n            {[\n              ["all", "All"],\n              ["skills", "Skills"],\n              ["stats", "Stats"],\n              ["shops", "Shops"],\n              ["xp", "XP"],\n            ].map(([value, label]) => (\n              <button\n                key={value}\n                className={activityType === value ? "active" : ""}\n                onClick={() => setFilter(value)}\n              >\n                {label}\n                <span>{value === "all" ? events.length : sources[value] ?? 0}</span>\n              </button>\n            ))}\n          </div>\n\n          <div className="activity-date-filters">\n            <label>\n              From\n              <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />\n            </label>\n            <label>\n              To\n              <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />\n            </label>\n            <button className="ghost" onClick={clearDates} disabled={!startDate && !endDate}>\n              Clear Dates\n            </button>\n          </div>\n        </div>\n\n        <div className="activity-timeline">\n          {events.length === 0 ? (\n            <div className="card">\n              <p>No activity found for this filter.</p>\n            </div>\n          ) : null}\n\n          {events.map((event, index) => (\n            <div className={`activity-card ${event.type}`} key={`${event.type}-${event.details?.request_id || event.details?.item_id || index}`}>\n              <div className="activity-marker">{eventIcon(event.type)}</div>\n\n              <div className="activity-content">\n                <div className="activity-card-header">\n                  <div>\n                    <span className="activity-type-label">{String(event.type || "activity").toUpperCase()}</span>\n                    <h3>{event.title}</h3>\n                  </div>\n                  <span className={`pill ${String(event.status || "").includes("approved") ? "good" : ""}`}>\n                    {statusLabel(event.status)}\n                  </span>\n                </div>\n\n                <p className="activity-time">{formatDate(event.timestamp)}</p>\n\n                {event.character?.name ? (\n                  <p>\n                    OC: <strong>{event.character.name}</strong>\n                  </p>\n                ) : null}\n\n                {event.details?.cost !== undefined && event.details?.cost !== null ? (\n                  <p>Cost: <strong>{event.details.cost} XP</strong></p>\n                ) : null}\n\n                {event.details?.amount !== undefined && event.details?.amount !== null ? (\n                  <p>Amount: <strong>{event.details.amount} XP</strong></p>\n                ) : null}\n\n                {event.details?.skill?.tree ? (\n                  <p>\n                    Tree: <strong>{event.details.skill.tree}</strong>\n                    {event.details.skill.tier !== undefined ? <> • Tier: <strong>{event.details.skill.tier}</strong></> : null}\n                  </p>\n                ) : null}\n\n                {event.details?.price !== undefined && event.details?.price !== null ? (\n                  <p>Price: <strong>{event.details.price}</strong></p>\n                ) : null}\n\n                {event.details?.reason ? (\n                  <div className="activity-note">\n                    <strong>Reason</strong>\n                    <p>{event.details.reason}</p>\n                  </div>\n                ) : null}\n\n                {event.details?.note ? (\n                  <div className="activity-note">\n                    <strong>Submitter Note</strong>\n                    <p>{event.details.note}</p>\n                  </div>\n                ) : null}\n\n                {event.details?.staff_note ? (\n                  <div className="activity-note staff">\n                    <strong>Staff Note</strong>\n                    <p>{event.details.staff_note}</p>\n                  </div>\n                ) : null}\n\n                {actorText(event) ? <small>{actorText(event)}</small> : null}\n              </div>\n            </div>\n          ))}\n        </div>\n      </section>\n    </RequireDiscord>\n  );\n}'
CSS_APPEND = '/* Activity date filters */\n\n.activity-date-filters {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 0.8rem;\n  align-items: end;\n  margin-top: 1rem;\n  padding-top: 1rem;\n  border-top: 1px solid rgba(61, 51, 43, 0.1);\n}\n\n.activity-date-filters label {\n  min-width: 180px;\n  flex: 0 1 220px;\n}\n\n.activity-date-filters button {\n  min-height: 2.8rem;\n}\n'


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


def main() -> None:
    old_route = BACKEND_ROUTE.read_text(encoding="utf-8") if BACKEND_ROUTE.exists() else ""
    if old_route != ACTIVITY_ROUTE_V2:
        BACKEND_ROUTE.with_suffix(".py.date_filters_v2.bak").write_text(old_route, encoding="utf-8")
        BACKEND_ROUTE.write_text(ACTIVITY_ROUTE_V2, encoding="utf-8")
        print("Patched backend/app/routes/activity.py")
    else:
        print("backend/app/routes/activity.py already patched")

    text = FRONTEND_MAIN.read_text(encoding="utf-8")
    original = text
    start, end = find_ts_function_block(text, "ActivityDashboard")
    text = text[:start] + ACTIVITY_DASHBOARD_V2 + text[end:]

    if text != original:
        FRONTEND_MAIN.with_suffix(".tsx.activity_date_filters_v2.bak").write_text(original, encoding="utf-8")
        FRONTEND_MAIN.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
    else:
        print("frontend/src/main.tsx unchanged")

    css = FRONTEND_CSS.read_text(encoding="utf-8")
    if "Activity date filters" not in css:
        FRONTEND_CSS.with_suffix(".css.activity_date_filters_v2.bak").write_text(css, encoding="utf-8")
        FRONTEND_CSS.write_text(css.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n", encoding="utf-8")
        print("Patched frontend/src/styles.css")
    else:
        print("Activity date filter CSS already present")

    print("")
    print("Done. Restart backend/frontend and test Activity date filters.")


if __name__ == "__main__":
    main()
