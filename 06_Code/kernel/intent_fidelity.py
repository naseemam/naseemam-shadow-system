"""Founder intent fidelity policy.

Classification and planning layers may infer structure, but they may not demote
an explicit Founder execution directive into planning, analysis, conversation,
or a request-for-approval flow. The original directive remains authoritative.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


EXECUTION_MARKERS = {
    "ابدأ", "ابدا", "نفذ", "نفّذ", "كمل", "كمّل", "أكمل", "سوي", "سو", "سوه", "سوها",
    "عدل", "عدّل", "اصلح", "أصلح", "شغل", "شغّل", "انشر", "ارسل", "أرسل", "انشئ", "أنشئ",
    "create", "build", "execute", "run", "edit", "modify", "fix", "deploy", "send", "continue",
}

PLANNING_ONLY_MARKERS = {
    "خطة", "خطط", "اقترح خطة", "اعطني خطة", "أعطني خطة", "plan", "roadmap", "proposal",
}

NON_EXECUTION_REQUEST_TYPES = {"planning", "analysis", "question", "creative", "conversation", "conversation_only", "unknown"}


def _normalize(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    value = re.sub(r"[ـ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def explicit_execution_requested(text: str, *, previous_goal: str = "") -> bool:
    """Return True when Founder language requests action rather than discussion.

    Short continuation commands such as «كمل» inherit the active goal. A request
    that explicitly asks only for a plan remains planning, even if it contains a
    word such as «ابدأ» as part of quoted/contextual language.
    """
    normalized = _normalize(text)
    if not normalized:
        return False

    if any(_normalize(marker) in normalized for marker in PLANNING_ONLY_MARKERS):
        return False

    words = set(re.findall(r"[\w\u0600-\u06ff]+", normalized))
    normalized_markers = {_normalize(marker) for marker in EXECUTION_MARKERS}
    if words & normalized_markers:
        return True

    short_continuation = normalized in {"كمل", "اكمل", "ابدأ", "ابدا", "نفذ", "سوي", "سوها", "سوه"}
    return bool(short_continuation and (previous_goal or "").strip())


def enforce_request_type(
    original_text: str,
    derived_request_type: str,
    *,
    previous_goal: str = "",
) -> Dict[str, Any]:
    """Prevent a classifier from demoting explicit execution intent.

    This does not invent execution. It only protects an execution signal already
    present in the Founder's own directive or an explicit continuation of an
    active goal.
    """
    derived = (derived_request_type or "").strip().lower() or "unknown"
    execution = explicit_execution_requested(original_text, previous_goal=previous_goal)
    overridden = execution and derived in NON_EXECUTION_REQUEST_TYPES
    effective = "execution" if overridden else derived
    return {
        "original_text": original_text,
        "derived_request_type": derived,
        "effective_request_type": effective,
        "explicit_execution": execution,
        "classifier_overridden": overridden,
        "reason": "founder_execution_signal_has_precedence" if overridden else "classifier_preserved",
    }


def preserve_scope(
    *,
    original_scope: Optional[str],
    derived_scope: Optional[str],
) -> Dict[str, Any]:
    """Expose attempted scope narrowing instead of silently accepting it."""
    original = (original_scope or "").strip()
    derived = (derived_scope or "").strip()
    narrowed = bool(original and derived and original != derived and derived in {"plan_only", "analysis_only", "conversation_only"})
    return {
        "original_scope": original,
        "derived_scope": derived,
        "valid": not narrowed,
        "violation": "narrow" if narrowed else None,
    }
