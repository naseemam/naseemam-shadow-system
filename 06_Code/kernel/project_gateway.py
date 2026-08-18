"""Project-aware routing gateway for the Shadow System.

ProjectGateway is a policy boundary, not an execution worker. It validates the
project, actor, role, capability, and context before a request can be routed to
Ameer and then to a subordinate worker.
"""
from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, Optional

from kernel.shadow_foundation import ShadowFoundation


class ProjectGateway:
    def __init__(self, foundation: ShadowFoundation, *, audit=None, orchestrator=None):
        self.foundation = foundation
        self.audit = audit
        self.orchestrator = orchestrator

    @staticmethod
    def _safe_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        context = copy.deepcopy(context or {})
        # Project context must be explicit and cannot smuggle credentials/prompts.
        forbidden = {"api_key", "openai_api_key", "authorization", "prompt", "secret", "token"}
        return {key: value for key, value in context.items() if key.lower() not in forbidden}

    def authorize(
        self,
        *,
        subject_id: str,
        role_id: str,
        project_id: str,
        capability: str,
        action: str = "read",
        context: Optional[Dict[str, Any]] = None,
        worker_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        correlation_id = uuid.uuid4().hex[:16]
        project = self.foundation.get_project(project_id)
        safe_context = self._safe_context(context)
        requested_project = safe_context.get("project_id")
        if requested_project and requested_project != project_id:
            decision = {"allowed": False, "reason": "cross_project_context_denied"}
        else:
            decision = self.foundation.can(subject_id, role_id, project_id, capability, action)

        if worker_id and project_id == "trading" and worker_id not in {"research", "operations"}:
            decision = {"allowed": False, "reason": "worker_not_allowed_for_project"}

        result = {
            "status": "authorized" if decision.get("allowed") else "blocked",
            "allowed": bool(decision.get("allowed")),
            "correlation_id": correlation_id,
            "orchestrator": "ameer",
            "subject_id": subject_id,
            "role_id": role_id,
            "project_id": project_id,
            "project": project,
            "capability": capability,
            "action": action,
            "approval": decision.get("approval", "none"),
            "reason": decision.get("reason"),
            "context": safe_context,
            "route": {"via": "ameer", "worker_id": worker_id, "direct_worker_access": False},
        }
        if self.audit is not None:
            self.audit.record(
                event_type="project_gateway_decision",
                actor=subject_id,
                subject=project_id,
                status=result["status"],
                correlation_id=correlation_id,
                payload={
                    "role_id": role_id,
                    "capability": capability,
                    "action": action,
                    "approval": result["approval"],
                    "reason": result["reason"],
                    "worker_id": worker_id,
                },
            )
        return result

    def route_to_ameer(self, **request: Any) -> Dict[str, Any]:
        """Authorize a request and return a routing envelope; never executes it."""
        result = self.authorize(**request)
        if result["allowed"]:
            result["next"] = "ameer_review_and_route"
        return result

    def snapshot(self) -> Dict[str, Any]:
        return {
            "gateway": "project_gateway",
            "owner": "ameer",
            "direct_worker_access": False,
            "cross_project_context": False,
            "external_execution": "approval_gate_required",
            "projects": len(self.foundation.list_projects()),
        }
