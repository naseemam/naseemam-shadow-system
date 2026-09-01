from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from kernel.founder_directive import FounderDirective, create_directive
from kernel.interaction_mode import InteractionMode, classify_interaction_mode


@dataclass(frozen=True)
class ArabicUnderstanding:
    raw: str
    normalized: str
    canonical_command: str
    continuation: bool
    correction: bool
    reference: Optional[str] = None
    founder_directive: Optional[FounderDirective] = None
    interaction_mode: Optional[InteractionMode] = None


# Saudi/Gulf conversational forms are normalized conservatively.
# The original Founder wording remains the semantic authority. canonical_command
# is only a derived execution aid and must never replace the original directive.
PHRASES = {
    "ابدا": "ابدأ",
    "ابدأ": "ابدأ",
    "كمل": "أكمل",
    "كمّل": "أكمل",
    "كمله": "أكمله",
    "خلص": "أكمل",
    "خلصها": "أكملها",
    "سوه": "نفذه",
    "سوي": "نفذ",
    "سوها": "نفذها",
    "نفذ": "نفذ",
    "نفذه": "نفذه",
    "عدل": "عدّل",
    "عدلها": "عدّلها",
    "صلح": "أصلح",
    "صلحها": "أصلحها",
    "شيك": "راجع",
    "شيك عليه": "راجعه",
    "راجعها": "راجعها",
    "اختبره": "اختبره",
    "م ضبط": "لم يعمل كما ينبغي",
    "ما ضبط": "لم يعمل كما ينبغي",
    "مو كذا": "ليس بهذا الشكل",
    "نفسه": "نفس العنصر السابق",
    "نفسها": "نفس المهمة السابقة",
    "الثاني": "العنصر الثاني من السياق",
    "الاول": "العنصر الأول من السياق",
    "الأول": "العنصر الأول من السياق",
    "ارجع": "ارجع للخطوة السابقة",
    "رجعه": "أعده للحالة السابقة",
    "وش صار": "ما حالة العمل الحالية",
    "وش وضعه": "ما حالة هذا العمل",
    "وين وصلنا": "ما آخر حالة وصلنا إليها",
}

CONTINUATION = {
    "ابدأ", "ابدا", "كمل", "كمّل", "أكمل", "خلص", "خلصها", "نفذ", "نفذه",
    "سوي", "سوه", "سوها", "اختبر", "اختبره", "راجع", "شيك", "صلحها", "عدلها",
}

CORRECTION_PATTERNS = (
    "م ضبط", "ما ضبط", "مو كذا", "غلط", "خطأ", "ناقص", "مو كامل", "غير كذا",
)


def _clean(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"[ـ]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def understand_arabic(text: str, *, previous_goal: str = "") -> ArabicUnderstanding:
    raw = _clean(text)
    lowered = raw.lower()
    canonical = PHRASES.get(lowered, raw)
    continuation = lowered in CONTINUATION or any(lowered.startswith(x + " ") for x in CONTINUATION)
    correction = any(p in lowered for p in CORRECTION_PATTERNS)

    notes = []
    # A short continuation turn may borrow operational context, but the inherited
    # goal is evidence only. It never replaces the Founder's current wording.
    if continuation and previous_goal:
        canonical = f"{canonical}. استمر في الهدف الحالي: {previous_goal}"
        notes.append("continuation_context_added")
    elif correction and previous_goal:
        canonical = f"{canonical}. راجع آخر نتيجة للهدف الحالي وأصلحها ذاتيًا: {previous_goal}"
        notes.append("correction_context_added")

    reference = None
    if lowered in {"نفسه", "نفسها", "الثاني", "الاول", "الأول"}:
        reference = PHRASES.get(lowered)
        notes.append("context_reference_resolved")

    directive = create_directive(
        raw,
        derived_text=canonical,
        previous_goal=previous_goal,
        interpretation_notes=notes,
    )
    interaction_mode = classify_interaction_mode(raw, previous_goal=previous_goal)

    return ArabicUnderstanding(
        raw=raw,
        normalized=lowered,
        canonical_command=canonical,
        continuation=continuation,
        correction=correction,
        reference=reference,
        founder_directive=directive,
        interaction_mode=interaction_mode,
    )
