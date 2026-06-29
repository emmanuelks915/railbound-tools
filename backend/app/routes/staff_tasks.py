from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.discord_webhook import notify_staff_webhook, _field
from app.permissions import require_staff
from app.security import actor_from_header
from app.services import get_guild_id
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/staff/tasks", tags=["staff-tasks"])

PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
PRIORITY_EMOJI = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
STATUS_LABELS   = {"todo": "To Do", "in_progress": "In Progress", "done": "Done"}


def _as_list(value: Any) -> list[dict[str, Any]]:
    from app.services import sb_data
    rows = sb_data(value) or []
    return rows if isinstance(rows, list) else []


def _safe_rows(builder) -> list[dict[str, Any]]:
    try:
        return _as_list(builder.execute())
    except Exception:
        return []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id":              str(row.get("task_id") or ""),
        "title":                row.get("title") or "Untitled Task",
        "description":          row.get("description"),
        "status":               row.get("status") or "todo",
        "priority":             row.get("priority") or "medium",
        "assignee_discord_id":  row.get("assignee_discord_id"),
        "assignee_name":        row.get("assignee_name"),
        "created_by_discord_id":row.get("created_by_discord_id"),
        "due_date":             str(row.get("due_date")) if row.get("due_date") else None,
        "completed_at":         str(row.get("completed_at")) if row.get("completed_at") else None,
        "created_at":           str(row.get("created_at") or ""),
        "updated_at":           str(row.get("updated_at") or ""),
        "is_overdue":           _is_overdue(row),
    }


def _is_overdue(row: dict[str, Any]) -> bool:
    if row.get("status") == "done":
        return False
    due = row.get("due_date")
    if not due:
        return False
    try:
        due_date = date.fromisoformat(str(due)[:10])
        return due_date < date.today()
    except Exception:
        return False


# ── List ─────────────────────────────────────────────────────────────────────

@router.get("")
def list_tasks(actor_discord_id: int | None = Depends(actor_from_header)):
    require_staff(actor_discord_id)
    sb = get_supabase()
    rows = _safe_rows(
        sb.table("staff_tasks")
        .select("*")
        .eq("guild_id", get_guild_id())
        .order("created_at", desc=True)
        .limit(200)
    )
    tasks = [_normalize(r) for r in rows]
    # Sort: by priority then due_date within each status bucket
    tasks.sort(key=lambda t: (
        0 if t["status"] == "todo" else 1 if t["status"] == "in_progress" else 2,
        PRIORITY_ORDER.get(t["priority"], 2),
        t["due_date"] or "9999-99-99",
    ))
    return {"tasks": tasks, "count": len(tasks)}


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("")
def create_task(
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required.")

    priority = str(payload.get("priority") or "medium").lower()
    if priority not in PRIORITY_ORDER:
        priority = "medium"

    status = str(payload.get("status") or "todo").lower()
    if status not in STATUS_LABELS:
        status = "todo"

    due_date = str(payload.get("due_date") or "").strip() or None
    assignee_id = payload.get("assignee_discord_id")
    assignee_name = str(payload.get("assignee_name") or "").strip() or None

    insert: dict[str, Any] = {
        "guild_id":              get_guild_id(),
        "title":                 title,
        "description":           str(payload.get("description") or "").strip() or None,
        "status":                status,
        "priority":              priority,
        "assignee_discord_id":   int(assignee_id) if assignee_id else None,
        "assignee_name":         assignee_name,
        "created_by_discord_id": actor_discord_id,
        "due_date":              due_date,
    }

    sb = get_supabase()
    rows = _as_list(sb.table("staff_tasks").insert(insert).execute())
    task = _normalize(rows[0]) if rows else {**insert, "task_id": "?"}

    # Notify Discord
    notify_staff_webhook(
        title=f"📋 New Staff Task: {title}",
        description=task.get("description") or "No description.",
        color=0x2F6F73,
        fields=[
            _field("Priority",  f"{PRIORITY_EMOJI.get(priority, '')} {priority.upper()}"),
            _field("Assignee",  assignee_name or "Unassigned"),
            _field("Due Date",  due_date or "No deadline"),
            _field("Created By", str(actor_discord_id)),
        ],
    )

    return {"task": task, "message": "Task created."}


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{task_id}")
def update_task(
    task_id: str,
    payload: dict[str, Any] = Body(default={}),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)
    sb = get_supabase()

    existing = _safe_rows(
        sb.table("staff_tasks")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("task_id", task_id)
        .limit(1)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found.")

    update: dict[str, Any] = {"updated_at": _now_iso()}

    if "title" in payload:
        title = str(payload["title"]).strip()
        if title:
            update["title"] = title

    if "description" in payload:
        update["description"] = str(payload["description"]).strip() or None

    if "status" in payload:
        s = str(payload["status"]).lower()
        if s in STATUS_LABELS:
            update["status"] = s
            if s == "done":
                update["completed_at"] = _now_iso()
            elif existing[0].get("status") == "done":
                update["completed_at"] = None

    if "priority" in payload:
        p = str(payload["priority"]).lower()
        if p in PRIORITY_ORDER:
            update["priority"] = p

    if "due_date" in payload:
        update["due_date"] = str(payload["due_date"]).strip() or None

    if "assignee_discord_id" in payload:
        aid = payload["assignee_discord_id"]
        update["assignee_discord_id"] = int(aid) if aid else None

    if "assignee_name" in payload:
        update["assignee_name"] = str(payload["assignee_name"]).strip() or None

    rows = _as_list(
        sb.table("staff_tasks")
        .update(update)
        .eq("guild_id", get_guild_id())
        .eq("task_id", task_id)
        .execute()
    )
    task = _normalize(rows[0]) if rows else {**existing[0], **update}
    return {"task": task, "message": "Task updated."}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    require_staff(actor_discord_id)
    sb = get_supabase()
    existing = _safe_rows(
        sb.table("staff_tasks")
        .select("task_id,title")
        .eq("guild_id", get_guild_id())
        .eq("task_id", task_id)
        .limit(1)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found.")
    sb.table("staff_tasks").delete().eq("guild_id", get_guild_id()).eq("task_id", task_id).execute()
    return {"ok": True, "message": f"Task '{existing[0].get('title')}' deleted."}


# ── Overdue check (hit by cron-job.org) ──────────────────────────────────────

@router.post("/check-overdue")
def check_overdue(
    x_cron_secret: str | None = None,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    """
    Called by cron-job.org on a schedule (e.g. daily 9am UTC).
    Sends a single Discord digest of all overdue tasks.
    Set CRON_SECRET in Railway env and pass as ?x_cron_secret=... for security.
    """
    from app.config import get_settings
    settings = get_settings()
    cron_secret = getattr(settings, "cron_secret", None) or ""
    if cron_secret and x_cron_secret != cron_secret:
        # Also allow staff to trigger manually
        if not actor_discord_id or actor_discord_id not in settings.staff_ids:
            raise HTTPException(status_code=403, detail="Unauthorized.")

    sb = get_supabase()
    today = date.today().isoformat()

    overdue = _safe_rows(
        sb.table("staff_tasks")
        .select("*")
        .eq("guild_id", get_guild_id())
        .neq("status", "done")
        .lt("due_date", today)
        .order("due_date", desc=False)
        .limit(50)
    )

    if not overdue:
        return {"ok": True, "overdue_count": 0, "message": "No overdue tasks."}

    fields = []
    for task in overdue:
        due = task.get("due_date") or "?"
        assignee = task.get("assignee_name") or "Unassigned"
        priority = task.get("priority") or "medium"
        emoji = PRIORITY_EMOJI.get(priority, "⚪")
        fields.append(_field(
            f"{emoji} {task.get('title') or 'Task'}",
            f"Due: {due} · Assignee: {assignee} · Status: {STATUS_LABELS.get(task.get('status','todo'), '?')}",
            inline=False,
        ))
        # Mark as pinged
        try:
            sb.table("staff_tasks").update({"overdue_pinged_at": _now_iso()}).eq("task_id", str(task.get("task_id"))).execute()
        except Exception:
            pass

    notify_staff_webhook(
        title=f"⏰ {len(overdue)} Overdue Staff Task{'s' if len(overdue) != 1 else ''}",
        description="The following tasks are past their due date and still open.",
        color=0xC05050,
        fields=fields[:25],
    )

    return {"ok": True, "overdue_count": len(overdue)}


# ── Weekly summary (hit by cron-job.org every Sunday 9am UTC) ────────────────

@router.post("/weekly-summary")
def weekly_summary(
    x_cron_secret: str | None = None,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    """
    Posts a full weekly digest to the staff Discord channel.
    Set up on cron-job.org: POST to this endpoint every Sunday at 9:00 UTC.
    """
    from app.config import get_settings
    settings = get_settings()
    cron_secret = getattr(settings, "cron_secret", None) or ""
    if cron_secret and x_cron_secret != cron_secret:
        if not actor_discord_id or actor_discord_id not in settings.staff_ids:
            raise HTTPException(status_code=403, detail="Unauthorized.")

    sb = get_supabase()

    all_tasks = _safe_rows(
        sb.table("staff_tasks")
        .select("*")
        .eq("guild_id", get_guild_id())
        .neq("status", "done")
        .order("due_date", desc=False)
        .limit(100)
    )

    if not all_tasks:
        notify_staff_webhook(
            title="📋 Weekly Staff Task Summary",
            description="✅ No open tasks this week — you're all caught up!",
            color=0x2F8F5B,
        )
        return {"ok": True, "task_count": 0}

    # Group by assignee
    by_assignee: dict[str, list[dict]] = {}
    unassigned: list[dict] = []

    for task in all_tasks:
        name = task.get("assignee_name") or ""
        if name:
            by_assignee.setdefault(name, []).append(task)
        else:
            unassigned.append(task)

    todo_count        = sum(1 for t in all_tasks if t.get("status") == "todo")
    in_progress_count = sum(1 for t in all_tasks if t.get("status") == "in_progress")
    overdue_count     = sum(1 for t in all_tasks if _is_overdue(t))

    description_lines = [
        f"**{len(all_tasks)} open task{'s' if len(all_tasks) != 1 else ''}** across the team.",
        f"📌 {todo_count} to do · 🔄 {in_progress_count} in progress · ⏰ {overdue_count} overdue",
    ]

    fields = []

    for assignee_name, tasks in sorted(by_assignee.items()):
        lines = []
        for t in sorted(tasks, key=lambda x: (PRIORITY_ORDER.get(x.get("priority","medium"), 2), x.get("due_date") or "9999")):
            emoji  = PRIORITY_EMOJI.get(t.get("priority","medium"), "⚪")
            status = STATUS_LABELS.get(t.get("status","todo"), "?")
            due    = f" · 📅 {t['due_date']}" if t.get("due_date") else ""
            overdue_flag = " ⏰" if _is_overdue(t) else ""
            lines.append(f"{emoji} **{t.get('title','?')}** [{status}]{due}{overdue_flag}")
        fields.append(_field(f"👤 {assignee_name}", "\n".join(lines), inline=False))

    if unassigned:
        lines = []
        for t in unassigned:
            emoji  = PRIORITY_EMOJI.get(t.get("priority","medium"), "⚪")
            status = STATUS_LABELS.get(t.get("status","todo"), "?")
            due    = f" · 📅 {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"{emoji} **{t.get('title','?')}** [{status}]{due}")
        fields.append(_field("❓ Unassigned", "\n".join(lines), inline=False))

    notify_staff_webhook(
        title="📋 Weekly Staff Task Summary",
        description="\n".join(description_lines),
        color=0x2F6F73,
        fields=fields[:25],
    )

    return {"ok": True, "task_count": len(all_tasks)}
