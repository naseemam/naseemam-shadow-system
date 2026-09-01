"""
execution_boundary.py
=====================
Central Execution Boundary for side-effecting work.

The boundary validates request clarity, separates chat from executable intent,
and routes ONLY centrally-defined sovereign actions to Founder approval. It may
reject malformed or technically unavailable execution, but no subsystem here may
invent an additional Founder approval requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set

from kernel.ameer_authority import SOVEREIGN_ACTIONS, canonical_sovereign_action

_GUARDIAN_PASS_VALUES: Set[str] = {"pass"}
_HIGH_RISK_ACTIONS_REQUIRING_APPROVAL: Set[str] = set(SOVEREIGN_ACTIONS)

_CONVERSATIONAL_TYPES: Set[str] = {
    "question",
    "greeting",
    "analysis",
    "memory",
    "creative",
}

KERNEL_ACTIONABLE_INTENTS: Set[str] = {
    "build_homepage", "build_generic", "file_read", "run_test",
    "repository_review", "code_edit", "build_website", "build_store",
    "open_branch", "open_pull_request", "deploy_railway",
}

AEX1_PERMISSION_MATRIX: Dict[str, Dict[str, Any]] = {
    "read_only": {"allow": True, "tracked": True, "approval": False},
    "tracked_write": {"allow": True, "tracked": True, "approval": False},
    "sovereign_gate": {"allow": False, "tracked": True, "approval": True},
    # compatibility key retained for callers/tests from the earlier policy
    "root_asset_creation": {"allow": False, "tracked": True, "approval": True},
}


class BoundaryVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    PENDING = "pending"


@dataclass
class BoundaryResult:
    verdict: BoundaryVerdict
    reason: str
    request_id: Optional[str] = None
    authorization_request_id: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.verdict == BoundaryVerdict.ALLOW


class ExecutionBoundary:
    """Technical boundary plus the single routing point to sovereign approval."""

    def __init__(self, approval_gate=None, execution_auth=None) -> None:
        self._approval_gate = approval_gate
        self._execution_auth = execution_auth

    def evaluate(
        self,
        *,
        guardian: Optional[Dict[str, Any]],
        request_type: str = "",
        intent: str = "",
        capability_name: str = "file_operations",
        action: str = "write",
        context: Optional[Dict[str, Any]] = None,
        requested_by: str = "executive_kernel",
    ) -> BoundaryResult:
        safe_context = context or {}

        # 1. Guardian checks request validity/clarity only. It is not an approval
        # authority. Anything other than explicit pass is a technical/input deny.
        guardian_status = self._extract_guardian_status(guardian)
        if guardian_status not in _GUARDIAN_PASS_VALUES:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="guardian_not_pass",
                detail={"guardian_status": guardian_status, "guardian_raw": guardian},
            )

        # 2. Ordinary conversation must not accidentally trigger side effects.
        rt = (request_type or "").strip().lower()
        it = (intent or "").strip().lower()
        if rt in _CONVERSATIONAL_TYPES and it not in KERNEL_ACTIONABLE_INTENTS:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="conversational_request_blocked",
                detail={"request_type": rt, "intent": it},
            )

        # 3. Central sovereign policy is the ONLY source of Founder gates.
        sovereign_action = canonical_sovereign_action(action, safe_context)
        if sovereign_action is not None:
            if self._approval_gate is None:
                return BoundaryResult(
                    verdict=BoundaryVerdict.DENY,
                    reason="sovereign_approval_gate_missing",
                    detail={"action": sovereign_action},
                )

            recent_fn = getattr(self._approval_gate, "recent", None)
            pending_fn = getattr(self._approval_gate, "pending", None)
            request_fn = getattr(self._approval_gate, "request", None)
            if not callable(recent_fn) or not callable(pending_fn) or not callable(request_fn):
                return BoundaryResult(
                    verdict=BoundaryVerdict.DENY,
                    reason="approval_gate_unavailable",
                    detail={"action": sovereign_action},
                )

            # Approval matching includes context identity when supplied, preventing
            # one approval for one asset/payment from silently authorizing another.
            identity_keys = ("asset_id", "root_asset_id", "repository", "payment_id", "transaction_id")
            requested_identity = tuple(
                (key, safe_context.get(key)) for key in identity_keys if safe_context.get(key) not in (None, "")
            )

            def _same_identity(record: Dict[str, Any]) -> bool:
                if record.get("action") != sovereign_action:
                    return False
                if not requested_identity:
                    return True
                recorded_context = record.get("context") or {}
                return all(recorded_context.get(key) == value for key, value in requested_identity)

            recent = recent_fn(50)
            approved_existing = any(
                record.get("status") == "approved" and _same_identity(record)
                for record in recent
            )
            if not approved_existing:
                pending = [record for record in pending_fn() if _same_identity(record)]
                if pending:
                    return BoundaryResult(
                        verdict=BoundaryVerdict.PENDING,
                        reason="approval_gate_pending",
                        detail={
                            "sovereign_action": sovereign_action,
                            "pending_count": len(pending),
                            "approval_id": pending[-1].get("id"),
                        },
                    )

                approval_id = request_fn(
                    action=sovereign_action,
                    description=f"Sovereign gate: {capability_name}/{sovereign_action}",
                    requested_by=requested_by,
                    context=safe_context,
                )
                return BoundaryResult(
                    verdict=BoundaryVerdict.PENDING,
                    reason="approval_gate_created",
                    detail={"approval_id": approval_id, "sovereign_action": sovereign_action},
                )

        # 4. Technical execution authorization. For non-sovereign actions it must
        # never return pending due to a permission card; that invariant is enforced
        # again in ExecutionAuthorization itself.
        if self._execution_auth is None:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_missing",
            )

        check_fn = getattr(self._execution_auth, "check", None)
        if not callable(check_fn):
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_unavailable",
            )

        try:
            auth_result = check_fn(
                capability_name=capability_name,
                action=action,
                context=safe_context,
                requested_by=requested_by,
            )
        except Exception as exc:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_unavailable",
                detail={"error": str(exc)},
            )

        if not isinstance(auth_result, dict):
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_unavailable",
                detail={"error": "invalid_check_result_type"},
            )

        auth_status = auth_result.get("status", "denied")
        if auth_status == "approved":
            return BoundaryResult(
                verdict=BoundaryVerdict.ALLOW,
                reason="execution_authorized",
                authorization_request_id=auth_result.get("request_id"),
                detail=auth_result,
            )
        if auth_status == "pending":
            # This path should only be reachable for a sovereign gate that was
            # invoked without the ApprovalGate wiring. Preserve pending instead
            # of silently converting it to approval.
            return BoundaryResult(
                verdict=BoundaryVerdict.PENDING,
                reason="execution_authorization_pending",
                authorization_request_id=auth_result.get("request_id"),
                detail=auth_result,
            )
        return BoundaryResult(
            verdict=BoundaryVerdict.DENY,
            reason="execution_authorization_denied",
            detail=auth_result,
        )

    @staticmethod
    def _extract_guardian_status(guardian: Optional[Dict[str, Any]]) -> str:
        if not guardian:
            return "missing"
        raw_status = guardian.get("status")
        if not raw_status:
            return "missing"
        normalized = str(raw_status).strip().lower()
        return normalized if normalized else "missing"
