from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from kernel.ameer_authority import ROOT_ASSET_ACTIONS, requires_founder_approval


# Compatibility exports. The central authority policy is the single source of
# truth: a Founder decision is reserved only for a new root asset creation.
FINAL_APPROVAL_ACTIONS = set(ROOT_ASSET_ACTIONS)
_FINAL_APPROVAL_PREFIXES = tuple()

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

    Ameer may execute every scoped capability and integration directly inside
    existing assets. A decision in the Business Chat is required only before
    creating a new root site, program, system, or repository.
    """

    @staticmethod
    def _requires_founder_final_approval(action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        return requires_founder_approval(action, context)

    def evaluate(
        self,
        action: str,
        *,
        irreversible: bool = False,
        external_effect: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> GovernanceDecision:
        if self._requires_founder_final_approval(action, context):
            return GovernanceDecision("REQUIRE_APPROVAL", True, "founder_root_asset_creation_gate", "root_asset_gate")

        # Irreversibility or an external effect alone are not founder gates under
        # the delegated policy. They remain fully audited by the executing layer.
        return GovernanceDecision("ALLOW", False, "founder_delegated_executive_authority", "stage")

    def stage_summary(self, actions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        items = list(actions)
        return {
            "approval_model": "new_root_asset_creation_only",
            "autonomous_actions": sum(1 for item in items if not item.get("approval_required", False)),
            "approval_actions": [item for item in items if item.get("approval_required", False)],
            "founder_decision_required": any(item.get("approval_required", False) for item in items),
        }
