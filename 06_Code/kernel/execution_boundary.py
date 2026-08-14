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
    Effect scope classification:
        local_workspace_effect  ──►  auto-allow (skip ApprovalGate)
        external_effect         ──►  ApprovalGate required
        ↓
    ApprovalGate      ──►  external_effect action and no prior approval  →  DENIED (pending)
        ↓
    ExecutionAuthorization.check()                                       →  approved / pending / denied
        ↓
    allow / deny

Design rules
------------
* Fail-closed: any ambiguous, missing, or unknown guardian status → deny
* Only an explicit "pass" from Guardian allows execution to proceed
* Conversational request_types never enter side-effect execution
* LOCAL WORKSPACE AUTONOMY: file.read/create/update and local build/test/lint/format
  operations inside runtime_workspace are auto-allowed — ApprovalGate is NOT consulted.
* EXTERNAL EFFECT APPROVAL: git push, deploy, external API calls, financial operations
  require ApprovalGate before execution.
* ApprovalGate is consulted ONLY for external_effect operations.
* ExecutionAuthorization is the final gate (capability + permission).
* Audit logging is always written regardless of effect scope.
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
# All local-workspace intents are included so they pass the conversational guard.
KERNEL_ACTIONABLE_INTENTS: Set[str] = {
    "build_homepage",
    "build_generic",
    "file_read",
    "run_test",
    # Local workspace autonomy — building, testing, editing inside runtime_workspace
    "create_website",
    "add_chat_box",
    "local_build",
    "local_test",
    "local_lint",
    "local_format",
    "local_codegen",
    "local_retry",
    "local_fix",
    "file_create",
    "file_update",
    "file_write",
}

# ── Effect-scope classification ────────────────────────────────────────────────

# Intents that are unconditionally local workspace operations (never need approval).
_LOCAL_WORKSPACE_INTENTS: Set[str] = {
    "build_homepage",
    "build_generic",
    "file_read",
    "file_create",
    "file_update",
    "file_write",
    "run_test",
    "create_website",
    "add_chat_box",
    "local_build",
    "local_test",
    "local_lint",
    "local_format",
    "local_codegen",
    "local_retry",
    "local_fix",
}

# Intents that unconditionally require external-effect approval.
_EXTERNAL_EFFECT_INTENTS: Set[str] = {
    "publish_site",
    "deploy",
    "git_push",
    "merge_pr",
    "send_email",
    "financial_operation",
}

# Tool names that operate exclusively inside the local workspace.
_LOCAL_WORKSPACE_TOOLS: Set[str] = {
    "file.read",
    "file.create",
    "file.update",
}


class EffectScope(str, Enum):
    """Effect scope of an execution request."""
    LOCAL_WORKSPACE = "local_workspace_effect"   # auto-allow, no ApprovalGate needed
    EXTERNAL_EFFECT = "external_effect"           # ApprovalGate required


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

        Effect scope classification
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        * local_workspace_effect → skip ApprovalGate, go to ExecutionAuthorization
        * external_effect        → consult ApprovalGate before proceeding

        ApprovalGate check (external effects only)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        * If an approval_gate is wired, the action is HIGH_RISK, and the
          effect scope is EXTERNAL_EFFECT → PENDING (unless a prior approval
          exists).

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

        # ── Step 2.5: Effect scope classification ─────────────────────────────
        # Determines whether this is a local workspace operation (auto-allow for
        # ApprovalGate) or an external-effect operation (requires ApprovalGate).
        effect_scope = self.classify_effect_scope(
            intent=it,
            action=action,
            context=context,
        )

        # ── Step 3: ApprovalGate (external effects only) ──────────────────────
        # LOCAL_WORKSPACE operations bypass ApprovalGate entirely.
        # Only EXTERNAL_EFFECT + HIGH_RISK actions require ApprovalGate.
        is_high_risk = action in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
        needs_approval_gate = is_high_risk and effect_scope == EffectScope.EXTERNAL_EFFECT

        if needs_approval_gate and self._approval_gate is None:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="approval_gate_required_missing",
                detail={"action": action, "effect_scope": effect_scope.value},
            )

        if self._approval_gate is not None and needs_approval_gate:
            recent_fn = getattr(self._approval_gate, "recent", None)
            pending_fn = getattr(self._approval_gate, "pending", None)
            request_fn = getattr(self._approval_gate, "request", None)
            if not callable(recent_fn) or not callable(pending_fn) or not callable(request_fn):
                return BoundaryResult(
                    verdict=BoundaryVerdict.DENY,
                    reason="approval_gate_unavailable",
                    detail={"action": action, "effect_scope": effect_scope.value},
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
                        detail={"pending_count": len(pending), "effect_scope": effect_scope.value},
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
                    detail={"approval_id": approval_id, "effect_scope": effect_scope.value},
                )

        # ── Step 4: ExecutionAuthorization ───────────────────────────────────
        if self._execution_auth is None:
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_missing",
                detail={"effect_scope": effect_scope.value},
            )

        check_fn = getattr(self._execution_auth, "check", None)
        if not callable(check_fn):
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_unavailable",
                detail={"effect_scope": effect_scope.value},
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
                detail={"error": str(exc), "effect_scope": effect_scope.value},
            )

        if not isinstance(auth_result, dict):
            return BoundaryResult(
                verdict=BoundaryVerdict.DENY,
                reason="execution_authorization_unavailable",
                detail={"error": "invalid_check_result_type", "effect_scope": effect_scope.value},
            )
        auth_status = auth_result.get("status", "denied")
        if auth_status == "approved":
            return BoundaryResult(
                verdict=BoundaryVerdict.ALLOW,
                reason="execution_authorized",
                authorization_request_id=auth_result.get("request_id"),
                detail={**auth_result, "effect_scope": effect_scope.value},
            )
        if auth_status == "pending":
            return BoundaryResult(
                verdict=BoundaryVerdict.PENDING,
                reason="execution_authorization_pending",
                authorization_request_id=auth_result.get("request_id"),
                detail={**auth_result, "effect_scope": effect_scope.value},
            )
        return BoundaryResult(
            verdict=BoundaryVerdict.DENY,
            reason="execution_authorization_denied",
            detail={**auth_result, "effect_scope": effect_scope.value},
        )

    # ── Effect scope classification ────────────────────────────────────────────

    @classmethod
    def classify_effect_scope(
        cls,
        *,
        intent: str,
        action: str,
        context: Optional[Dict[str, Any]],
    ) -> "EffectScope":
        """
        Classify an execution request as LOCAL_WORKSPACE or EXTERNAL_EFFECT.

        LOCAL_WORKSPACE operations (auto-allow, no ApprovalGate):
          - file.read, file.create, file.update inside runtime_workspace
          - Local build/test/lint/format/codegen commands (pytest, npm test, etc.)
          - Intents: build_homepage, build_generic, run_test, create_website, etc.

        EXTERNAL_EFFECT operations (ApprovalGate required):
          - git push, merge PR, production deploy, railway config
          - External API writes, email, financial operations
          - Intents: publish_site, deploy, git_push, merge_pr, etc.

        Classification priority:
          1. Shell command classification (for shell.run / action="run") — authoritative
          2. Tool-name-based (file.read/create/update → local)
          3. Intent-based (explicit local / external intent sets)
          4. Action-based (delete/publish/external/financial → external)
          5. Default: LOCAL_WORKSPACE (fail-open for local ops inside workspace)
        """
        ctx = context or {}
        tool_name = str(ctx.get("tool_name") or "").strip().lower()

        # 1. Shell command classification (authoritative — command determines effect)
        if (tool_name == "shell.run" or action == "run") and ctx.get("command"):
            command = ctx.get("command")
            try:
                from kernel.shell_external_effect_classifier import (
                    ShellExternalEffectClassifier,
                )
                classification = ShellExternalEffectClassifier.classify(command)
                if classification["is_external_effect"]:
                    return EffectScope.EXTERNAL_EFFECT
                # Only accept local if the classification reason is definitive.
                # An empty command or unknown reason → fail conservative.
                reason = classification.get("reason", "")
                if not reason or reason == "empty_command":
                    return EffectScope.EXTERNAL_EFFECT
                return EffectScope.LOCAL_WORKSPACE
            except Exception:
                # Classifier unavailable or raised — fail conservative
                return EffectScope.EXTERNAL_EFFECT

        # 2. Tool-name-based (file.read/create/update are always local)
        if tool_name in _LOCAL_WORKSPACE_TOOLS:
            return EffectScope.LOCAL_WORKSPACE

        # 3. Intent-based classification
        if intent in _LOCAL_WORKSPACE_INTENTS:
            return EffectScope.LOCAL_WORKSPACE
        if intent in _EXTERNAL_EFFECT_INTENTS:
            return EffectScope.EXTERNAL_EFFECT

        # 4. Action-based (high-risk actions without a local tool_name → external)
        if action in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL:
            return EffectScope.EXTERNAL_EFFECT

        # 5. Default: unknown context without a proven local tool → fail conservative.
        # Only auto-allow LOCAL_WORKSPACE if the tool is explicitly known-local OR
        # the intent is in _LOCAL_WORKSPACE_INTENTS (already handled above).
        # Anything else is treated as external-effect to avoid silent data exfiltration.
        return EffectScope.EXTERNAL_EFFECT

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
