"""Ameer's autonomous execution loop contract.

The execution model is outcome-driven, not approval-driven:
understand goal -> inspect current state -> choose tools/steps -> execute -> test ->
repair if needed -> retest -> continue until the requested outcome is complete.

Operational credentials are part of execution, not a human handoff. When a
service needs a key/token, Ameer may inspect the current credential state, create
a scoped operational key, test it, bind it to the service, verify continuity,
and only then retire an obsolete credential when doing so is safe. A potentially
service-breaking revocation remains a sovereign decision unless a replacement is
verified.

ChatGPT, Manus, models, providers, and tools may be used as resources, but none is
an authority that Ameer must consult before each implementation step.
Only the sovereign gates defined in kernel.ameer_authority may pause execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from kernel.ameer_authority import requires_founder_approval

EXECUTION_PHASES = (
    "understand_goal",
    "inspect_current_state",
    "choose_tools_and_steps",
    "execute_changes",
    "test_result",
    "repair_if_needed",
    "retest",
    "continue_until_complete",
)

CREDENTIAL_LIFECYCLE_PHASES = (
    "inspect_credential_state",
    "determine_minimum_scope",
    "create_operational_credential",
    "test_new_credential",
    "bind_credential_to_service",
    "verify_service_continuity",
    "retire_old_credential_if_safe",
    "record_credential_evidence",
)

@dataclass(frozen=True)
class ExecutionLoopDecision:
    action: str
    may_execute: bool
    founder_approval_required: bool
    phase: str
    reason: str
    external_assistant_required: bool = False

@dataclass(frozen=True)
class CredentialLifecycleDecision:
    phase: str
    action: str
    may_execute: bool
    founder_approval_required: bool
    reason: str
    continuity_must_be_verified: bool = True


def decide_execution_step(action: str, *, context: Optional[dict] = None, phase: str = "execute_changes") -> ExecutionLoopDecision:
    if phase not in EXECUTION_PHASES:
        raise ValueError(f"Unknown execution phase: {phase}")
    sovereign = requires_founder_approval(action, context or {})
    if sovereign:
        return ExecutionLoopDecision(action, False, True, phase, "explicit_sovereign_gate", False)
    return ExecutionLoopDecision(action, True, False, phase, "delegated_executive_autonomy", False)


def decide_credential_step(action: str, *, context: Optional[dict] = None, phase: str = "create_operational_credential") -> CredentialLifecycleDecision:
    if phase not in CREDENTIAL_LIFECYCLE_PHASES:
        raise ValueError(f"Unknown credential lifecycle phase: {phase}")
    ctx = dict(context or {})
    sovereign = requires_founder_approval(action, ctx)
    if sovereign:
        return CredentialLifecycleDecision(
            phase=phase,
            action=action,
            may_execute=False,
            founder_approval_required=True,
            reason="credential_action_crosses_preclassified_sovereign_gate",
        )
    return CredentialLifecycleDecision(
        phase=phase,
        action=action,
        may_execute=True,
        founder_approval_required=False,
        reason="credential_management_is_part_of_delegated_operations",
    )


def cloudflare_operational_key_plan(*, purpose: str, replacement_for: str = "") -> list[dict]:
    """Return the execution contract for an operational Cloudflare credential.

    This is deliberately provider-specific enough to prevent a generic policy
    layer from turning key creation into a human task. The actual Cloudflare API
    adapter supplies concrete permissions/account scope at runtime.
    """
    return [
        {"phase": "inspect_credential_state", "purpose": purpose, "replacement_for": replacement_for},
        {"phase": "determine_minimum_scope", "principle": "scoped_operational_access"},
        {"phase": "create_operational_credential", "requires_founder_approval": False},
        {"phase": "test_new_credential", "requires_founder_approval": False},
        {"phase": "bind_credential_to_service", "requires_founder_approval": False},
        {"phase": "verify_service_continuity", "requires_founder_approval": False},
        {"phase": "retire_old_credential_if_safe", "condition": "replacement_verified_and_no_expected_service_interruption"},
        {"phase": "record_credential_evidence", "redact_secret_value": True},
    ]


def next_phase(current_phase: str, *, success: bool, outcome_complete: bool) -> str:
    """Advance the loop without turning failure into an approval request."""
    if outcome_complete:
        return "complete"
    if current_phase in {"execute_changes", "test_result", "retest"} and not success:
        return "repair_if_needed"
    if current_phase == "repair_if_needed":
        return "retest"
    order = list(EXECUTION_PHASES)
    try:
        index = order.index(current_phase)
    except ValueError:
        return "understand_goal"
    return order[min(index + 1, len(order) - 1)]


def external_resources_are_advisory(resources: Optional[Iterable[str]] = None) -> dict:
    names = [str(x) for x in (resources or ())]
    return {
        "resources": names,
        "authority": "advisory_resource_only",
        "required_for_routine_execution": False,
        "may_be_replaced": True,
        "may_be_skipped": True,
        "sovereign_authority": False,
    }
