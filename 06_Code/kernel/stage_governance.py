from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


# Founder policy: Ameer is an executive agent with comprehensive authority.
# The only final-chat decisions reserved to the Founder are irreversible deletion
# and publication of an outcome to production/public audiences.
FINAL_APPROVAL_ACTIONS = {
    "delete",
    "destructive.delete",
    "publish",
    "railway.deploy_production",
    "railway.rollback",
}

_FINAL_APPROVAL_PREFIXES = (
    "delete.",
    "destructive.delete",
    "publish.",
    "deployment.publish",
    "railway.deploy",
    "railway.rollback",
)

AUTONOMOUS_STAGE_ACTION_PREFIXES = (
    "design.",
    "engineering.",
    "code.",
    "test.",
    "lint.",
    "debug.",
    "refactor.",
    "repository.",
    "business.",
    "school.",
    "trading.",
    "capability.",
    "credential.",
    "connector.",
    "external.",
    "git.",
    "github.",
    "email.",
    "calendar.",
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
    """Founder-governed executive autonomy.

    Ameer may execute every non-destructive capability and integration directly.
    A decision in the Business Chat is required only to delete material or to
    publish/deploy/rollback an outcome.
    """

    @staticmethod
    def _requires_founder_final_approval(action: str) -> bool:
        name = str(action or "").strip().lower()
        return name in FINAL_APPROVAL_ACTIONS or any(
            name.startswith(prefix) for prefix in _FINAL_APPROVAL_PREFIXES
        )

    def evaluate(self, action: str, *, irreversible: bool = False, external_effect: bool = False) -> GovernanceDecision:
        name = str(action or "").strip().lower()

        if self._requires_founder_final_approval(name):
            return GovernanceDecision("REQUIRE_APPROVAL", True, "founder_delete_or_publish_gate", "final_gate")

        # Irreversibility or an external effect alone are not founder gates under
        # the delegated policy. They remain fully audited by the executing layer.
        return GovernanceDecision("ALLOW", False, "founder_delegated_executive_authority", "stage")

    def stage_summary(self, actions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        items = list(actions)
        return {
            "approval_model": "delete_and_publish_only",
            "autonomous_actions": sum(1 for item in items if not item.get("approval_required", False)),
            "approval_actions": [item for item in items if item.get("approval_required", False)],
            "founder_decision_required": any(item.get("approval_required", False) for item in items),
        }
