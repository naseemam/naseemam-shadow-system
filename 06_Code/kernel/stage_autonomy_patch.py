from __future__ import annotations

from functools import wraps
from typing import Any

_INSTALLED = False

# Commands that continue the current stage. They must not be treated as a new
# executive lane merely because old task records are still pending/blocked.
_CONTINUATION_TERMS = (
    "نفذ", "نفّذ", "ابدأ", "ابدا", "ابدئي", "أبدأ", "اكمل", "أكمل", "كمل",
    "تابع", "استمر", "عدل", "عدّل", "اصلح", "أصلح", "اختبر", "جرب", "جرّب",
    "نفّذ الآن", "ابدأ الآن", "كمل الآن", "continue", "proceed", "execute",
    "implement", "test", "fix", "update",
)

# The legacy reasoning guardian used to classify generic execution words such
# as "نفذ" and "push" as high-risk. StageGovernance / FinalStageGate now owns
# final approvals, so this legacy layer only keeps genuinely destructive local
# operations guarded. Production merge/deploy/credential activation remain
# governed by the final-stage gate in ExpandedAgentExecutiveKernel.
_LEGACY_DESTRUCTIVE_ONLY = (
    "delete", "drop", "destroy", "wipe", "reset",
    "احذف", "امسح",
)


def _is_stage_continuation(query: str) -> bool:
    text = (query or "").strip().lower()
    return bool(text) and any(term in text for term in _CONTINUATION_TERMS)


def install_stage_autonomy_patch() -> None:
    """Align legacy conversation/reasoning layers with final-gate-only policy."""
    global _INSTALLED
    if _INSTALLED:
        return

    from reasoning_orchestrator import AmeerOrchestrator
    from executive_conversation import ExecutiveConversationEngine, PersistentConversationMemory

    original_guardian_check = AmeerOrchestrator.guardian_check

    @wraps(original_guardian_check)
    def guardian_check(self: AmeerOrchestrator, query: str, intent: str):
        previous = list(getattr(self, "high_risk_action_terms", []))
        try:
            # Generic execution/build/test/push words are normal work inside a
            # stage. Do not require Founder approval for each micro-action.
            self.high_risk_action_terms = list(_LEGACY_DESTRUCTIVE_ONLY)
            return original_guardian_check(self, query, intent)
        finally:
            self.high_risk_action_terms = previous

    AmeerOrchestrator.guardian_check = guardian_check

    original_plan = PersistentConversationMemory.plan

    @wraps(original_plan)
    def plan(self: PersistentConversationMemory, query: str, *args: Any, **kwargs: Any):
        if _is_stage_continuation(query):
            # Pending/blocked records belonging to the stage must not force the
            # planner to stop and "close a task" before continuing that stage.
            kwargs["running_tasks"] = []
        return original_plan(self, query, *args, **kwargs)

    PersistentConversationMemory.plan = plan

    original_execute = ExecutiveConversationEngine.execute

    @wraps(original_execute)
    def execute(self: ExecutiveConversationEngine, *args: Any, **kwargs: Any):
        query = str(kwargs.get("query") or "")
        if _is_stage_continuation(query):
            # Same-stage continuation should use the actual provider/kernel
            # result instead of being hijacked by stale task-state warnings.
            kwargs["running_tasks"] = []
        return original_execute(self, *args, **kwargs)

    ExecutiveConversationEngine.execute = execute
    _INSTALLED = True
