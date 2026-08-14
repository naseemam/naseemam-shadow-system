from __future__ import annotations

import json
import os
import sys

# ─── 06_Code on sys.path — must be first so kernel imports resolve everywhere ─
_CODE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "06_Code")
if _CODE_ROOT not in sys.path:
    sys.path.insert(0, _CODE_ROOT)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from kernel.execution_evidence import extract_execution_evidence, enforce_evidence_on_reply
from kernel.operator_activity import OperatorActivityStore
from kernel.provider_identity_patch import install_provider_identity_patch

# Install identity ownership before the executive kernel is constructed.
install_provider_identity_patch()

from ameer_delivery_bootstrap import app  # noqa: E402,F401
import ameer_server  # noqa: E402


ACTIVITY = OperatorActivityStore(ameer_server.REPO_ROOT)


class TruthfulExecutionMiddleware(BaseHTTPMiddleware):
    """Never let a conversational/provider reply masquerade as real execution.

    Ameer may only claim completion when the response carries conservative Kernel
    evidence of a real file write or a completed operational side effect. Verified
    executions are persisted into a small Founder-facing evidence ledger.
    """

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

        trace = body.get("execution_trace") or {}
        evidence = extract_execution_evidence(trace)
        reply = str(body.get("reply") or body.get("message") or "")
        truthful = enforce_evidence_on_reply(reply, evidence)
        if truthful != reply:
            body["reply"] = truthful
            body["message"] = truthful
            body["execution_claim_checked"] = True

        body["execution_evidence"] = evidence
        if evidence.get("verified"):
            ACTIVITY.record(evidence)

        headers = {
            k: v for k, v in dict(response.headers).items()
            if k.lower() not in {"content-length", "content-type"}
        }
        return JSONResponse(content=body, status_code=response.status_code, headers=headers)


app.add_middleware(TruthfulExecutionMiddleware)
