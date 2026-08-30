"""Founder-first interaction mode classification.

This classifier distinguishes conversation, question, suggestion, planning,
decision, execution, continuation, and correction without allowing a derived
classification to narrow or override the Founder's original directive.

Classification is an execution aid, not an authority boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InteractionMode:
    mode: str
    confidence: float
    execution_requested: bool
    continuation: bool = False
    correction: bool = False
    reason: str = ""


_EXECUTION = (
    "نفذ", "نفّذ", "سوي", "سوه", "سوها", "ابدأ", "ابدا", "كمل", "كمّل", "أكمل",
    "عدل", "عدّل", "اصلح", "أصلح", "صلح", "شغل", "شغّل", "اكتب", "أنشئ", "انشئ",
    "ابن", "ابنِ", "ارسل", "أرسل", "احذف", "أضف", "طبق", "طبّق",
    "execute", "run", "start", "continue", "edit", "fix", "build", "create", "write",
)

_CONTINUATION = (
    "كمل", "كمّل", "أكمل", "ابدأ", "ابدا", "خلص", "خلصها", "تابع", "continue", "resume",
)

_CORRECTION = (
    "م ضبط", "ما ضبط", "مو كذا", "غلط", "خطأ", "ناقص", "مو كامل", "اصلح", "أصلح", "صلح",
    "fix it", "not right", "wrong",
)

_PLANNING = (
    "خطة", "خطط", "خطوات", "مراحل", "roadmap", "plan", "كيف نبدأ", "كيف ابدا", "كيف أبدأ",
)

_SUGGESTION = (
    "اقترح", "وش تقترح", "ما اقتراحك", "فكرة", "أفكار", "suggest", "recommend", "brainstorm",
)

_DECISION = (
    "قرر", "اختار", "أختار", "هل أوافق", "أوافق", "أرفض", "قرار", "decide", "choose", "should i",
)

_QUESTION_PREFIXES = (
    "ما ", "من ", "كيف ", "متى ", "وين ", "أين ", "هل ", "ليش ", "لماذا ",
    "what ", "who ", "how ", "when ", "where ", "why ", "is ", "are ",
)


def _norm(text: str) -> str:
    value = " ".join((text or "").strip().lower().split())
    return value.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ى", "ي")


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(_norm(value) in text for value in values)


def classify_interaction_mode(text: str, *, previous_goal: str = "") -> InteractionMode:
    q = _norm(text)
    if not q:
        return InteractionMode("conversation", 0.0, False, reason="empty_turn")

    continuation = _contains_any(q, _CONTINUATION)
    correction = _contains_any(q, _CORRECTION)

    # Explicit requests for a plan or suggestion remain non-executing unless the
    # same turn also explicitly asks Ameer to carry the work out.
    planning = _contains_any(q, _PLANNING)
    suggestion = _contains_any(q, _SUGGESTION)
    decision = _contains_any(q, _DECISION)
    execution = _contains_any(q, _EXECUTION)

    if continuation and previous_goal:
        return InteractionMode(
            "continuation",
            1.0,
            True,
            continuation=True,
            correction=correction,
            reason="explicit_continuation_of_active_goal",
        )

    if correction:
        return InteractionMode(
            "correction",
            0.98,
            True,
            correction=True,
            reason="founder_requests_result_correction",
        )

    # Planning/suggestion wording has priority only when the Founder did not also
    # issue an explicit execution verb such as نفذ/طبق/سوي.
    if planning and not execution:
        return InteractionMode("planning", 0.95, False, reason="explicit_planning_request")
    if suggestion and not execution:
        return InteractionMode("suggestion", 0.95, False, reason="explicit_suggestion_request")
    if decision and not execution:
        return InteractionMode("decision", 0.9, False, reason="decision_request")

    if execution:
        return InteractionMode("execution", 0.98, True, reason="explicit_execution_language")

    if q.endswith("؟") or q.endswith("?") or any(q.startswith(_norm(p)) for p in _QUESTION_PREFIXES):
        return InteractionMode("question", 0.9, False, reason="question_form")

    return InteractionMode("conversation", 0.65, False, reason="contextual_conversation_default")


def reconcile_classifier(
    founder_text: str,
    classifier_mode: Optional[str],
    *,
    previous_goal: str = "",
) -> dict:
    """Reconcile a legacy/LLM classifier with the Founder-first mode.

    The external classifier may add confidence or routing hints, but it cannot
    downgrade explicit execution/continuation/correction into planning, analysis,
    question, or conversation-only behavior.
    """
    founder_mode = classify_interaction_mode(founder_text, previous_goal=previous_goal)
    proposed = (classifier_mode or "").strip().lower()

    protected_modes = {"execution", "continuation", "correction"}
    non_execution_modes = {"planning", "analysis", "question", "conversation", "conversation_only", "suggestion"}

    overridden = founder_mode.mode in protected_modes and proposed in non_execution_modes
    effective = founder_mode.mode if overridden or not proposed else proposed

    # A classifier is never allowed to manufacture execution where the Founder
    # explicitly requested only planning/suggestion.
    if founder_mode.mode in {"planning", "suggestion"} and proposed in protected_modes:
        effective = founder_mode.mode
        overridden = True

    return {
        "founder_mode": founder_mode.mode,
        "classifier_mode": proposed or None,
        "effective_mode": effective,
        "execution_requested": founder_mode.execution_requested,
        "classifier_overridden": overridden,
        "semantic_authority": "founder_directive",
        "reason": founder_mode.reason,
    }
