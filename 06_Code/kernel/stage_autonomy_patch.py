from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any

_INSTALLED = False

# Commands that continue the current stage. They must not be treated as a new
# executive lane merely because old task records are still pending/blocked.
_CONTINUATION_TERMS = (
    "نفذ", "نفّذ", "ابدأ", "ابدا", "ابدئي", "أبدأ", "اكمل", "أكمل", "كمل",
    "تابع", "استمر", "عدل", "عدّل", "اصلح", "أصلح", "اختبر", "جرب", "جرّب",
    "سوها", "سويها", "شيك", "راجع", "م ضبط", "ما ضبط", "خلص", "أنجز", "انجز",
    "نفّذ الآن", "ابدأ الآن", "كمل الآن", "continue", "proceed", "execute",
    "implement", "test", "fix", "update",
)

# Explicit delegation phrases mean: keep working autonomously inside the current
# reversible stage and return to the Founder only at the real final gate.
_DELEGATION_TERMS = (
    "لا ترجع لموافقتي", "لا ترجع لي", "لا تسألني", "بدون ما تسألني",
    "انجز كلشي", "أنجز كلشي", "انجز كل شيء", "أنجز كل شيء", "كمل كلشي",
    "إلا وقت النشر", "الا وقت النشر", "إلا عند النشر", "الا عند النشر",
    "until publish", "until deployment", "without asking me", "do it all",
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


def _normalized(query: str) -> str:
    return (query or "").strip().lower()


def _is_destructive(query: str) -> bool:
    text = _normalized(query)
    return any(term in text for term in _LEGACY_DESTRUCTIVE_ONLY)


def _is_stage_continuation(query: str) -> bool:
    text = _normalized(query)
    return bool(text) and any(term in text for term in _CONTINUATION_TERMS + _DELEGATION_TERMS)


def _clear_legacy_guardian(reasoning_output: Any) -> Any:
    """Remove only the obsolete per-turn guardian approval signal.

    The real final-stage gate remains authoritative for merge, production deploy,
    credentials, destructive operations, and other irreversible effects.
    """
    if not isinstance(reasoning_output, dict):
        return reasoning_output
    result = deepcopy(reasoning_output)
    reasoning = result.get("reasoning")
    if isinstance(reasoning, dict) and reasoning.get("guardian_status") == "needs_approval":
        reasoning["guardian_status"] = "pass"
        reasoning["guardian_reason"] = "delegated_stage_execution"
        reasoning["guardian_mode"] = "execution_ready"
    return result


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
        if _is_stage_continuation(query) and not _is_destructive(query):
            # Pending/blocked records belonging to the stage must not force the
            # planner to stop and "close a task" before continuing that stage.
            kwargs["running_tasks"] = []
        return original_plan(self, query, *args, **kwargs)

    PersistentConversationMemory.plan = plan

    original_execute = ExecutiveConversationEngine.execute

    @wraps(original_execute)
    def execute(self: ExecutiveConversationEngine, *args: Any, **kwargs: Any):
        query = str(kwargs.get("query") or "")
        if _is_stage_continuation(query) and not _is_destructive(query):
            # Same-stage continuation should use the actual provider/kernel
            # result instead of being hijacked by stale task-state warnings or
            # the obsolete per-turn guardian approval prompt.
            kwargs["running_tasks"] = []
            kwargs["pending_approvals"] = []
            kwargs["reasoning_output"] = _clear_legacy_guardian(kwargs.get("reasoning_output"))
        return original_execute(self, *args, **kwargs)

    ExecutiveConversationEngine.execute = execute
    _INSTALLED = True
