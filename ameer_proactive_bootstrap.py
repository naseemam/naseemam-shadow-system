from __future__ import annotations

import asyncio
import json

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

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


class ProactiveExecutionMiddleware(BaseHTTPMiddleware):
    """Turn real runtime outcomes into persistent Founder-facing events."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
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
            PROACTIVE.emit(
                "execution_failed",
                "واجهت مشكلة أثناء التنفيذ",
                "فشل طلب تنفيذي أو تعذر إكماله. راجعي سجل التنفيذ لمعرفة المرحلة المتوقفة.",
                severity="error",
                source="kernel",
            )
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
        elif body.get("execution_claim_checked"):
            PROACTIVE.emit(
                "execution_unverified",
                "أوقفت ادعاء إنجاز غير موثّق",
                "لم يظهر أثر تنفيذي حقيقي لهذا الطلب، لذلك لم أسجله كإنجاز.",
                severity="warning",
                source="truth_guard",
            )

        headers = {
            k: v for k, v in dict(response.headers).items()
            if k.lower() not in {"content-length", "content-type"}
        }
        return JSONResponse(content=body, status_code=response.status_code, headers=headers)


app.add_middleware(ProactiveExecutionMiddleware)


@app.get("/ui/proactive")
async def ui_proactive_events():
    return ameer_server.utf8_json_response(
        {
            "events": PROACTIVE.recent(60),
            "unread_count": PROACTIVE.unread_count(),
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
    """Watch meaningful runtime state without spamming the Founder.

    The monitor emits only when approval state changes. Execution outcomes are
    emitted by middleware immediately after a real request completes.
    """
    previous_pending: int | None = None
    while True:
        try:
            pending = ameer_server.KERNEL.final_gate.pending()
            count = len(pending)
            if previous_pending is None:
                previous_pending = count
            elif count != previous_pending:
                if count > previous_pending:
                    PROACTIVE.emit(
                        "state_approval_pending",
                        "أحتاج قرارك النهائي",
                        f"يوجد الآن {count} طلب موافقة نهائية محفوظ. العمل الداخلي لا يتوقف بسببه إلا عند بوابته.",
                        severity="attention",
                        source="final_gate",
                        dedupe_key="approval_pending_count",
                    )
                else:
                    PROACTIVE.emit(
                        "state_approval_resolved",
                        "تغيّرت حالة الموافقات",
                        f"الموافقات النهائية المعلقة الآن: {count}.",
                        severity="info",
                        source="final_gate",
                        dedupe_key="approval_pending_count",
                    )
                previous_pending = count
        except Exception:
            # Monitoring must never take Ameer down.
            pass
        await asyncio.sleep(20)


@app.on_event("startup")
async def start_proactive_monitor():
    PROACTIVE.emit(
        "state_runtime_online",
        "أمير متصل ويعمل بالمراقبة",
        "بدأت مراقبة الأحداث التنفيذية والموافقات. سأعرض المستجدات المهمة بدون انتظار سؤال.",
        severity="success",
        source="runtime",
        dedupe_key="runtime_online",
    )
    app.state.ameer_proactive_task = asyncio.create_task(_state_monitor())


@app.on_event("shutdown")
async def stop_proactive_monitor():
    task = getattr(app.state, "ameer_proactive_task", None)
    if task:
        task.cancel()
