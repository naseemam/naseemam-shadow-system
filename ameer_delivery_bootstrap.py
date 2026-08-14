from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

import ameer_server
from kernel.expanded_agent import ExpandedAgentExecutiveKernel
from kernel.execution_boundary import ExecutionBoundary
from kernel.multi_client_continuity import MultiClientContinuity
from kernel.repository_execution import (
    RepositoryExecutionAuthorization,
    RepositoryFileExecutor,
    RepositoryPlanValidator,
    repository_file_create_permission_scope,
)
from kernel.stage_autonomy_patch import install_stage_autonomy_patch
from kernel.tool_dispatcher import ToolDispatcher

# Compatibility alignment: legacy reasoning/conversation layers used to require
# approval for generic execution words and interrupt continuation when stale
# tasks existed. The new governance model owns approval at final stage gates.
install_stage_autonomy_patch()


def _build_kernel() -> ExpandedAgentExecutiveKernel:
    repo_root = Path(ameer_server.REPO_ROOT).resolve()
    kernel = ExpandedAgentExecutiveKernel(repo_root)
    kernel.permissions.grant(
        "file.create",
        scope=repository_file_create_permission_scope(),
        granted_by="system:controlled_repository_activation",
    )
    kernel.execution_auth = RepositoryExecutionAuthorization(
        repo_root,
        kernel.capabilities,
        kernel.permissions,
    )
    kernel.execution_boundary = ExecutionBoundary(
        approval_gate=kernel.approvals,
        execution_auth=kernel.execution_auth,
    )
    kernel.plan_validator = RepositoryPlanValidator(
        repo_root,
        capability_registry=kernel.capabilities,
        permission_registry=kernel.permissions,
    )
    kernel.file_executor = RepositoryFileExecutor(repo_root)
    kernel.tool_dispatcher = ToolDispatcher(
        tool_registry=kernel.tool_registry,
        execution_boundary=kernel.execution_boundary,
        execution_authorization=kernel.execution_auth,
        approval_gate=kernel.approvals,
        executor=kernel.file_executor.execute,
        shell_executor=kernel.shell_executor.execute,
        workspace_root=repo_root,
    )
    return kernel


# One runtime kernel owns controlled engineering work, business and school
# operations, communications/calendar, skill expansion, GitHub delivery,
# Railway deployment, and the Founder final-stage approval gate.
ameer_server.KERNEL = _build_kernel()
ameer_server.EXECUTION_BOUNDARY = ameer_server.KERNEL.execution_boundary
ameer_server.KERNEL_ACTIONABLE_INTENTS.update({
    "agent_action",
    "delivery_action",
    "final_approval",
    "final_approval_execute",
})
app = ameer_server.app
CONTINUITY = MultiClientContinuity(ameer_server.REPO_ROOT)


def _is_local_request(request: Request) -> bool:
    host = str(getattr(getattr(request, "client", None), "host", "") or "")
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


def _require_agent_access(request: Request) -> None:
    if CONTINUITY.authorized(
        request.headers.get("authorization", ""),
        local_request=_is_local_request(request),
    ):
        return
    if not CONTINUITY.authentication_enabled:
        raise HTTPException(
            status_code=503,
            detail="Remote agent access requires AMEER_AGENT_API_TOKEN in Railway variables.",
        )
    raise HTTPException(status_code=401, detail="Invalid or missing agent API token")


@app.get("/agent/capabilities")
async def agent_capabilities(request: Request):
    _require_agent_access(request)
    capabilities = ameer_server.KERNEL.expanded_capabilities()
    capabilities["mobility"] = CONTINUITY.snapshot()
    return ameer_server.utf8_json_response(
        capabilities,
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
    )


@app.get("/agent/continuity")
async def agent_continuity(request: Request):
    _require_agent_access(request)
    return ameer_server.utf8_json_response(
        CONTINUITY.snapshot(),
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
    )


@app.post("/agent/client/register")
async def agent_client_register(request: Request):
    _require_agent_access(request)
    payload = await request.json()
    try:
        result = CONTINUITY.register_client(
            client_id=str(payload.get("client_id") or ""),
            client_type=str(payload.get("client_type") or ""),
            channel=str(payload.get("channel") or "text"),
            device_name=str(payload.get("device_name") or ""),
            app_version=str(payload.get("app_version") or ""),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ameer_server.utf8_json_response(result)


@app.post("/agent/session/open")
async def agent_session_open(request: Request):
    _require_agent_access(request)
    payload = await request.json()
    try:
        result = CONTINUITY.open_session(
            client_id=str(payload.get("client_id") or ""),
            channel=str(payload.get("channel") or "") or None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ameer_server.utf8_json_response(result)


@app.post("/agent/session/handoff")
async def agent_session_handoff(request: Request):
    _require_agent_access(request)
    payload = await request.json()
    try:
        result = CONTINUITY.handoff(
            client_id=str(payload.get("client_id") or ""),
            channel=str(payload.get("channel") or "") or None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ameer_server.utf8_json_response(result)


@app.get("/agent/approvals")
async def agent_approvals(request: Request):
    _require_agent_access(request)
    return ameer_server.utf8_json_response(
        {
            "approval_model": "final_gate_only",
            "pending": ameer_server.KERNEL.final_gate.pending(),
        },
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
    )


@app.post("/agent/action")
async def agent_action(request: Request):
    _require_agent_access(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")
    action = str(payload.get("action") or "").strip()
    params = payload.get("payload") or {}
    if not action:
        raise HTTPException(status_code=400, detail="Missing action")
    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail="payload must be an object")
    result = ameer_server.KERNEL.execute_structured_agent_action(action, params)
    code = 200 if result.get("status") in {"completed", "needs_parameters"} else 409
    return ameer_server.utf8_json_response(
        result,
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
        status_code=code,
    )


# The legacy /ask endpoint was written when every successful Kernel execution
# meant "build homepage". Replace only its final rendering layer so agent,
# delivery, and final-approval operations return their real execution message.
_original_ask_route = next(
    (
        route
        for route in list(app.router.routes)
        if getattr(route, "path", None) == "/ask" and "POST" in (getattr(route, "methods", set()) or set())
    ),
    None,
)

if _original_ask_route is not None:
    _original_ask_endpoint = _original_ask_route.endpoint
    app.router.routes.remove(_original_ask_route)

    @app.post("/ask")
    async def agent_aware_ask(request: Request):
        response = await _original_ask_endpoint(request)
        try:
            body = json.loads(bytes(response.body).decode("utf-8"))
            trace = body.get("execution_trace") or {}
            pipeline = trace.get("pipeline") or []
            stage = str((pipeline[0] if pipeline else {}).get("stage") or "")
            message = str((trace.get("final") or {}).get("message") or "").strip()
            if stage in {"agent_action", "delivery_action", "final_approval", "final_approval_execute"} and message:
                body["reply"] = message
                body["message"] = message
                body["agent_action"] = (trace.get("final") or {}).get("results", [{}])[0].get("data")
                headers = {
                    k: v for k, v in dict(response.headers).items()
                    if k.lower() not in {"content-length", "content-type"}
                }
                return JSONResponse(content=body, status_code=response.status_code, headers=headers)
        except Exception:
            pass
        return response
