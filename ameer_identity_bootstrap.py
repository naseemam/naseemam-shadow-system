from __future__ import annotations

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from kernel.provider_identity_patch import install_provider_identity_patch

# Install identity ownership before the executive kernel is constructed.
install_provider_identity_patch()

from ameer_delivery_bootstrap import app  # noqa: E402,F401


_COMPLETION_CLAIMS = (
    "تم التنفيذ", "تم تنفيذ", "تم بناء", "تم تعديل", "تم إصلاح", "تم اصلاح",
    "أنهيت", "انتهيت", "اكتمل التنفيذ", "اكتملت المهمة", "تمت المهمة",
    "نفذت", "نفّذت", "أنجزت", "انجزت", "تم الدفع", "تم النشر",
)


def _has_execution_evidence(body: dict) -> bool:
    trace = body.get("execution_trace") or {}
    final = trace.get("final") or {}
    if final.get("accepted") and (int(final.get("completed") or 0) > 0 or final.get("files_created")):
        return True
    pipeline = trace.get("pipeline") or []
    for step in pipeline:
        status = str((step or {}).get("status") or "").lower()
        if status in {"completed", "passed", "accepted", "approved", "allow"}:
            output = (step or {}).get("output") or {}
            if output.get("files") or int(output.get("completed") or 0) > 0:
                return True
    action = body.get("agent_action") or {}
    if str(action.get("status") or "").lower() == "completed":
        return True
    return False


def _claims_completion(text: str) -> bool:
    value = str(text or "")
    return any(marker in value for marker in _COMPLETION_CLAIMS)


class TruthfulExecutionMiddleware(BaseHTTPMiddleware):
    """Never let a conversational/provider reply masquerade as real execution."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path != "/ask" or response.status_code >= 400:
            return response
        try:
            raw = b""
            async for chunk in response.body_iterator:
                raw += chunk
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            return response

        reply = str(body.get("reply") or body.get("message") or "")
        if _claims_completion(reply) and not _has_execution_evidence(body):
            truthful = (
                "لم أسجّل تنفيذًا فعليًا لهذا الطلب بعد. فهمت المطلوب، لكن لا يوجد إيصال تنفيذ "
                "أو ملفات مكتوبة تثبت الإنجاز، لذلك لن أعتبره مكتملًا. سأحوّل الطلب لمسار التنفيذ "
                "المحكوم بدل الاكتفاء بالرد الكلامي."
            )
            body["reply"] = truthful
            body["message"] = truthful
            body["execution_claim_corrected"] = True

        headers = {
            k: v for k, v in dict(response.headers).items()
            if k.lower() not in {"content-length", "content-type"}
        }
        return JSONResponse(content=body, status_code=response.status_code, headers=headers)


app.add_middleware(TruthfulExecutionMiddleware)
