from __future__ import annotations

import asyncio
import json

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse

from ameer_identity_bootstrap import app
import ameer_server
from kernel.proactive_events import ProactiveEventStore


PROACTIVE = ProactiveEventStore(ameer_server.REPO_ROOT)


def _execution_summary(evidence: dict) -> str:
    completed = int(evidence.get("completed_units") or evidence.get("final_completed") or 0)
    file_count = int(evidence.get("file_count") or 0)
    if file_count:
        return f"أنجزت {completed} خطوة فعلية وغيّرت {file_count} ملف. التفاصيل محفوظة في سجل التنفيذ."
    return f"أنجزت {completed} خطوة فعلية. التفاصيل محفوظة في سجل التنفيذ."


def _task_snapshot() -> dict:
    tasks = list(getattr(getattr(ameer_server.KERNEL, "state", None), "running_tasks", []) or [])
    counts = {"total": len(tasks), "pending": 0, "running": 0, "blocked": 0, "completed": 0, "failed": 0}
    for task in tasks:
        status = str((task or {}).get("status") or "pending").strip().lower()
        if status in counts:
            counts[status] += 1
        elif status in {"done", "finished"}:
            counts["completed"] += 1
        else:
            counts["pending"] += 1
    return counts


class ProactiveExecutionMiddleware(BaseHTTPMiddleware):
    """Turn real runtime outcomes into persistent Founder-facing events."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        if request.method == "GET" and request.url.path in {"/", "/index.html"} and response.status_code < 400:
            try:
                raw = b""
                async for chunk in response.body_iterator:
                    raw += chunk
                html = raw.decode("utf-8")
                tag = '<script src="/modules/proactive.js" defer></script>'
                if tag not in html:
                    html = html.replace("</body>", tag + "\n</body>")
                headers = {k: v for k, v in dict(response.headers).items() if k.lower() not in {"content-length", "content-type"}}
                return HTMLResponse(html, status_code=response.status_code, headers=headers)
            except Exception:
                return response

        if request.url.path != "/ask":
            return response

        try:
            raw = b""
            async for chunk in response.body_iterator:
                raw += chunk
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            return response

        evidence = body.get("execution_evidence") or {}
        if response.status_code >= 400:
            PROACTIVE.emit("execution_failed", "واجهت مشكلة أثناء التنفيذ", "فشل طلب تنفيذي أو تعذر إكماله. راجعي سجل التنفيذ لمعرفة المرحلة المتوقفة.", severity="error", source="kernel")
        elif evidence.get("verified"):
            PROACTIVE.emit(
                "execution_completed",
                "أنجزت مهمة فعلية",
                _execution_summary(evidence),
                severity="success",
                source="kernel",
                evidence={
                    "kind": evidence.get("kind"),
                    "completed_units": evidence.get("completed_units"),
                    "file_count": evidence.get("file_count"),
                    "files": list(evidence.get("files") or [])[:12],
                },
            )

        headers = {k: v for k, v in dict(response.headers).items() if k.lower() not in {"content-length", "content-type"}}
        return JSONResponse(content=body, status_code=response.status_code, headers=headers)


app.add_middleware(ProactiveExecutionMiddleware)


@app.get("/ui/proactive")
async def ui_proactive_events():
    return ameer_server.utf8_json_response(
        {
            "events": PROACTIVE.recent(60),
            "unread_count": PROACTIVE.unread_count(),
            "task_state": _task_snapshot(),
        },
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
    )


@app.post("/ui/proactive/seen")
async def ui_proactive_seen(request: Request):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    PROACTIVE.mark_seen(str(payload.get("at") or "") or None)
    return ameer_server.utf8_json_response({"ok": True, "unread_count": PROACTIVE.unread_count()})


async def _state_monitor() -> None:
    """Continuously watch approvals and task lifecycle; announce only changes."""
    previous_pending: int | None = None
    previous_tasks: dict | None = None
    while True:
        try:
            pending = ameer_server.KERNEL.final_gate.pending()
            count = len(pending)
            if previous_pending is None:
                previous_pending = count
                if count:
                    PROACTIVE.emit("state_approval_pending", "أحتاج قرارك النهائي", f"يوجد {count} طلب موافقة نهائية محفوظ.", severity="attention", source="final_gate", dedupe_key="approval_pending_count")
            elif count != previous_pending:
                if count > previous_pending:
                    PROACTIVE.emit("state_approval_pending", "أحتاج قرارك النهائي", f"يوجد الآن {count} طلب موافقة نهائية محفوظ. العمل الداخلي يستمر حتى بوابته.", severity="attention", source="final_gate", dedupe_key="approval_pending_count")
                else:
                    PROACTIVE.emit("state_approval_resolved", "تغيّرت حالة الموافقات", f"الموافقات النهائية المعلقة الآن: {count}.", severity="info", source="final_gate", dedupe_key="approval_pending_count")
                previous_pending = count

            tasks = _task_snapshot()
            if previous_tasks is None:
                previous_tasks = tasks
                if tasks["blocked"]:
                    PROACTIVE.emit("state_tasks_blocked", "هناك مهام متوقفة", f"وجدت {tasks['blocked']} مهمة متوقفة وسأبقيها ظاهرة بدل إخفائها داخل المحادثة.", severity="warning", source="task_lifecycle", dedupe_key="task_state")
            elif tasks != previous_tasks:
                if tasks["failed"] > previous_tasks.get("failed", 0):
                    PROACTIVE.emit("state_tasks_failed", "ظهرت مهمة فاشلة", f"المهام الفاشلة الآن: {tasks['failed']}. سأعرضها في المستجدات بدل انتظار سؤالك.", severity="error", source="task_lifecycle", dedupe_key="task_state")
                elif tasks["blocked"] > previous_tasks.get("blocked", 0):
                    PROACTIVE.emit("state_tasks_blocked", "توقفت مهمة وتحتاج انتباه", f"المهام المتوقفة الآن: {tasks['blocked']}.", severity="warning", source="task_lifecycle", dedupe_key="task_state")
                elif tasks["completed"] > previous_tasks.get("completed", 0):
                    PROACTIVE.emit("state_tasks_progress", "تقدم في المهام", f"المهام المكتملة المسجلة الآن: {tasks['completed']} من {tasks['total']}.", severity="success", source="task_lifecycle", dedupe_key="task_state")
                else:
                    PROACTIVE.emit("state_tasks_changed", "تغيّرت حالة العمل", f"قيد التنفيذ: {tasks['running']}، معلقة: {tasks['pending']}، متوقفة: {tasks['blocked']}.", severity="info", source="task_lifecycle", dedupe_key="task_state")
                previous_tasks = tasks
        except Exception:
            pass
        await asyncio.sleep(20)


@app.on_event("startup")
async def start_proactive_monitor():
    PROACTIVE.emit(
        "runtime_online",
        "أمير متصل ويعمل بالمراقبة",
        "بدأت مراقبة التنفيذ والمهام والموافقات. سأعرض المستجدات المهمة بدون انتظار سؤال.",
        severity="success",
        source="runtime",
    )
    app.state.ameer_proactive_task = asyncio.create_task(_state_monitor())


@app.on_event("shutdown")
async def stop_proactive_monitor():
    task = getattr(app.state, "ameer_proactive_task", None)
    if task:
        task.cancel()
