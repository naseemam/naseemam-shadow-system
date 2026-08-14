from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

import ameer_server
from kernel.agent_operations import AgentExecutiveKernel
from kernel.execution_boundary import ExecutionBoundary
from kernel.repository_execution import (
    RepositoryExecutionAuthorization,
    RepositoryFileExecutor,
    RepositoryPlanValidator,
    repository_file_create_permission_scope,
)
from kernel.tool_dispatcher import ToolDispatcher


def _build_kernel() -> AgentExecutiveKernel:
    repo_root = Path(ameer_server.REPO_ROOT).resolve()
    kernel = AgentExecutiveKernel(repo_root)
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
    # AgentExecutiveKernel owns AgentTaskDecomposer; do not replace it with the
    # repository-only decomposer here.
    return kernel


# One runtime kernel owns controlled code changes, business operations,
# communications/calendar tools, GitHub delivery, and Railway deployment.
ameer_server.KERNEL = _build_kernel()
ameer_server.EXECUTION_BOUNDARY = ameer_server.KERNEL.execution_boundary
ameer_server.KERNEL_ACTIONABLE_INTENTS.update({"agent_action", "delivery_action"})
app = ameer_server.app


@app.get("/agent/capabilities")
async def agent_capabilities():
    return ameer_server.utf8_json_response(
        ameer_server.KERNEL.agent_ops.capabilities(),
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
    )


@app.post("/agent/action")
async def agent_action(request: Request):
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
    result = ameer_server.KERNEL.agent_ops.execute_structured(action, params)
    code = 200 if result.get("status") in {"completed", "needs_parameters"} else 409
    return ameer_server.utf8_json_response(
        result,
        headers=ameer_server.runtime_headers(workspace_root=ameer_server.REPO_ROOT),
        status_code=code,
    )


# The legacy /ask endpoint was written when every successful Kernel execution
# meant "build homepage". Replace only its final rendering layer so agent and
# delivery operations can return their real execution message without changing
# the existing reasoning/orchestration pipeline.
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
            if stage in {"agent_action", "delivery_action"} and message:
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
