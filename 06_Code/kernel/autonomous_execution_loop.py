"""Ameer's autonomous execution loop contract.

The execution model is outcome-driven, not approval-driven:
understand goal -> inspect current state -> choose tools/steps -> execute -> test ->
repair if needed -> retest -> continue until the requested outcome is complete.

ChatGPT, Manus, models, providers, and tools may be used as resources, but none is
an authority that Ameer must consult before each implementation step.
Only the sovereign gates defined in kernel.ameer_authority may pause execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

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


@dataclass(frozen=True)
class ExecutionLoopDecision:
    action: str
    may_execute: bool
    founder_approval_required: bool
    phase: str
    reason: str
    external_assistant_required: bool = False


def decide_execution_step(
    action: str,
    *,
    context: Optional[dict] = None,
    phase: str = "execute_changes",
) -> ExecutionLoopDecision:
    if phase not in EXECUTION_PHASES:
        raise ValueError(f"Unknown execution phase: {phase}")

    sovereign = requires_founder_approval(action, context or {})
    if sovereign:
        return ExecutionLoopDecision(
            action=action,
            may_execute=False,
            founder_approval_required=True,
            phase=phase,
            reason="explicit_sovereign_gate",
            external_assistant_required=False,
        )

    return ExecutionLoopDecision(
        action=action,
        may_execute=True,
        founder_approval_required=False,
        phase=phase,
        reason="delegated_executive_autonomy",
        external_assistant_required=False,
    )


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
