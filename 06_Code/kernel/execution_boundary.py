"""
execution_boundary.py
=====================
Central Execution Boundary — the single gate every side-effecting execution
request must pass before reaching ExecutionAuthorization or FileExecutor.

Pipeline
--------
    Execution request
        ↓
    ExecutionBoundary.evaluate(guardian, request_type, intent)
        ↓
    Guardian verdict  ──►  blocked / needs_approval / unknown / missing  →  DENIED
        ↓
    conversational?   ──►  not in KERNEL_ACTIONABLE_INTENTS             →  DENIED
        ↓
    ApprovalGate      ──►  action HIGH_RISK and no prior approval        →  DENIED (pending)
        ↓
    ExecutionAuthorization.check()                                       →  approved / pending / denied
        ↓
    allow / deny

Design rules
------------
* Fail-closed: any ambiguous, missing, or unknown guardian status → deny
* Only an explicit "pass" from Guardian allows execution to proceed
* Conversational request_types never enter side-effect execution
* ApprovalGate is consulted for high-risk actions
* ExecutionAuthorization is the final gate (capability + permission)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set

# Statuses that Guardian must explicitly produce for execution to be allowed.
_GUARDIAN_PASS_VALUES: Set[str] = {"pass"}

# High-risk actions that require an ApprovalGate to be available.
# Mirrors ApprovalGate.HIGH_RISK_ACTIONS.
_HIGH_RISK_ACTIONS_REQUIRING_APPROVAL: Set[str] = {
    "delete",
    "publish",
    "external",
    "financial",
    "merge",
    "deploy",
}

# Request types that are purely conversational — they must never trigger side effects.
_CONVERSATIONAL_TYPES: Set[str] = {
    "question",
    "greeting",
    "analysis",
    "memory",
    "creative",
}

# Intents that the kernel is allowed to act on even when request_type is conversational.
# This mirrors KERNEL_ACTIONABLE_INTENTS in ameer_server.py.
KERNEL_ACTIONABLE_INTENTS: Set[str] = {
    "build_homepage", "build_generic", "file_read", "run_test",
    "repository_review", "code_edit", "build_website", "build_store",
    "open_branch", "open_pull_request", "deploy_railway",
}

# AEX-1 permission matrix. Read/analyze and workspace writes are eligible for
# the normal audited path; merge/publish/deploy require explicit approval.
AEX1_PERMISSION_MATRIX: Dict[str, Dict[str, Any]] = {
    "read_only": {"allow": True, "tracked": True, "approval": False},
    "tracked_write": {"allow": True, "tracked": True, "approval": False},
    "external_approval": {"allow": False, "tracked": True, "approval": True},
}


class BoundaryVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    PENDING = "pending"   # waiting for Founder approval


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
    """
    Central gate that every side-effecting execution request must pass.

    Parameters
    ----------
    approval_gate : ApprovalGate | None
        Optional; consulted for HIGH_RISK_ACTIONS.
    execution_auth : ExecutionAuthorization | None
        Optional; the final authorization layer.
    """

    def __init__(
        self,
        approval_gate=None,
        execution_auth=None,
    ) -> None:
        self._approval_gate = approval_gate
        self._execution_auth = execution_auth

    # ── Public API ────────────────────────────────────────────────────────────

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
        """
        Evaluate whether a side-effecting execution may proceed.

        Returns a :class:`BoundaryResult` with ``verdict`` ∈
        {ALLOW, DENY, PENDING}.

        Guardian check (fail-closed)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        * ``guardian`` is None or empty dict → DENY
        * ``guardian["status"]`` is None, ``""`` or anything other than
          ``"pass"`` → DENY
        * ``"pass"`` → continue to next check

        Conversational-type check
        ~~~~~~~~~~~~~~~~~~~~~~~~~
        * If request_type is in _CONVERSATIONAL_TYPES AND intent is not in
          KERNEL_ACTIONABLE_INTENTS → DENY (conversational requests cannot
          trigger side effects).

        ApprovalGate check
        ~~~~~~~~~~~~~~~~~~
        * If an approval_gate is wired and the action is HIGH_RISK → PENDING
          (unless a prior approval exists).

        ExecutionAuthorization check
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        * ``execution_auth.check(...)`` → approved / pending / denied
        * Only ``approved`` maps to ALLOW.
        """
        # ── Step 1: Guardian fail-closed ──────────────────────────────────────
        guardian_status = self._extract_guardian_status(guardian)
        if guardian_status not in _GUARDIAN_PASS_VALUES:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="guardian_not_pass",
                detail={
                    "guardian_status": guardian_status,
                    "guardian_raw": guardian,
                },
            )

        # ── Step 2: Conversational guard ──────────────────────────────────────
        rt = (request_type or "").strip().lower()
        it = (intent or "").strip().lower()
        if rt in _CONVERSATIONAL_TYPES and it not in KERNEL_ACTIONABLE_INTENTS:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="conversational_request_blocked",
                detail={"request_type": rt, "intent": it},
            )

        # ── Step 3: ApprovalGate (high-risk) ─────────────────────────────────
        is_high_risk = action in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
        if is_high_risk and self._approval_gate is None:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="approval_gate_required_missing",
                detail={"action": action},
            )

        if self._approval_gate is not None and is_high_risk:
            recent_fn = getattr(self._approval_gate, "recent", None)
            pending_fn = getattr(self._approval_gate, "pending", None)
            request_fn = getattr(self._approval_gate, "request", None)
            if not callable(recent_fn) or not callable(pending_fn) or not callable(request_fn):
                return BoundaryResult(
                    verdict=BoundaryVerdict.DENY,
                    reason="approval_gate_unavailable",
                    detail={"action": action},
                )

            # Check if there is already an *approved* entry for this action type.
            # If so, the Founder has already authorized — allow execution.
            recent = recent_fn(20)
            approved_existing = any(
                r.get("status") == "approved" and r.get("action") == action
                for r in recent
            )
            if not approved_existing:
                # Check whether there is a pending request
                pending = pending_fn()
                if pending:
                    # Pending request exists — block until resolved
                    return BoundaryResult(
                        verdict=BoundaryVerdict.PENDING,
                        reason="approval_gate_pending",
                        detail={"pending_count": len(pending)},
                    )
                # No pending and no approved — open a new request
                valid_actions = getattr(self._approval_gate, "VALID_ACTIONS", {action})
                approval_id = request_fn(
                    action=action if action in valid_actions else "other",
                    description=f"Execution boundary gate: {capability_name}/{action}",
                    requested_by=requested_by,
                    context=context or {},
                )
                return BoundaryResult(
                    verdict=BoundaryVerdict.PENDING,
                    reason="approval_gate_created",
                    detail={"approval_id": approval_id},
                )

        # ── Step 4: ExecutionAuthorization ───────────────────────────────────
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
                context=context or {},
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

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_guardian_status(guardian: Optional[Dict[str, Any]]) -> str:
        """
        Extract the guardian status string.

        Fail-closed: anything that is not an explicit "pass" becomes "unknown".
        """
        if not guardian:
            return "missing"
        raw_status = guardian.get("status")
        if not raw_status:
            return "missing"
        normalized = str(raw_status).strip().lower()
        return normalized if normalized else "missing"
