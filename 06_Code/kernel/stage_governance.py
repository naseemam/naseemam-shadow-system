from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


FINAL_APPROVAL_ACTIONS = {
    "git.merge_main",
    "railway.deploy_production",
    "railway.rollback",
    "external.send_sensitive",
    "credential.activate",
    "capability.activate_external",
    "destructive.delete",
    "destructive.bulk_update",
    "stage.complete",
}

AUTONOMOUS_STAGE_ACTION_PREFIXES = (
    "design.",
    "engineering.",
    "code.",
    "test.",
    "lint.",
    "debug.",
    "refactor.",
    "repository.write",
    "repository.branch",
    "repository.commit",
    "business.",
    "school.local.",
    "capability.prototype",
    "capability.test",
)


@dataclass(frozen=True)
class GovernanceDecision:
    decision: str
    approval_required: bool
    reason: str
    checkpoint: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "approval_required": self.approval_required,
            "reason": self.reason,
            "checkpoint": self.checkpoint,
        }


class StageGovernancePolicy:
    """Founder-governed autonomy.

    Ameer works autonomously inside an approved stage. Founder approval is requested
    once at a meaningful boundary, not for ordinary implementation details.
    """

    def evaluate(self, action: str, *, irreversible: bool = False, external_effect: bool = False) -> GovernanceDecision:
        name = str(action or "").strip().lower()

        if irreversible:
            return GovernanceDecision("REQUIRE_APPROVAL", True, "irreversible_effect", "final_gate")

        if name in FINAL_APPROVAL_ACTIONS:
            return GovernanceDecision("REQUIRE_APPROVAL", True, "founder_final_gate", "final_gate")

        if name.startswith("email.send"):
            # Ordinary operational mail can be sent autonomously when the stage explicitly
            # includes communications. Sensitive/bulk mail is classified separately.
            return GovernanceDecision("ALLOW", False, "approved_stage_communication", "stage")

        if name.startswith("calendar."):
            return GovernanceDecision("ALLOW", False, "approved_stage_calendar", "stage")

        if any(name.startswith(prefix) for prefix in AUTONOMOUS_STAGE_ACTION_PREFIXES):
            return GovernanceDecision("ALLOW", False, "stage_autonomy", "stage")

        if external_effect:
            return GovernanceDecision("REQUIRE_APPROVAL", True, "unclassified_external_effect", "final_gate")

        return GovernanceDecision("ALLOW", False, "reversible_internal_work", "stage")

    def stage_summary(self, actions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        items = list(actions)
        return {
            "approval_model": "final_gate_only",
            "autonomous_actions": sum(1 for item in items if not item.get("approval_required", False)),
            "approval_actions": [item for item in items if item.get("approval_required", False)],
            "founder_decision_required": any(item.get("approval_required", False) for item in items),
        }
