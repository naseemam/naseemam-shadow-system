"""Arabic semantic evidence extraction for Ameer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .arabic_lexicon import (
    ANALYSIS_REQUESTS,
    DIRECT_OPINION_PHRASES,
    EXECUTION_VERBS,
    EXECUTION_TARGETS,
    GREETINGS,
    IDENTITY_REQUESTS,
    MEMORY_REQUESTS,
    PROJECT_REQUESTS,
    QUESTION_CUES,
    RESEARCH_REQUESTS,
)
from .arabic_patterns import has_any_phrase, normalize_arabic_text


@dataclass
class ArabicSemanticEvidence:
    original_text: str
    normalized_text: str
    category: str
    confidence: float
    preferred_intent: str
    preferred_agent: str
    matched_signals: List[str] = field(default_factory=list)
    direct_addressed: bool = False
    is_arabic: bool = False


class ArabicLanguageLayer:
    """Extract semantic evidence from Arabic and Saudi/Gulf colloquial queries."""

    def __init__(self) -> None:
        self._route_map = {
            "greeting": ("greeting", "greeting_agent"),
            "identity_request": ("identity", "ameer_core"),
            "direct_question": ("identity", "ameer_core"),
            "direct_opinion": ("identity", "ameer_core"),
            "analysis_request": ("knowledge_lookup", "research_agent"),
            "research_request": ("knowledge_lookup", "research_agent"),
            "execution_request": ("execution", "project_agent"),
            "memory_request": ("onboarding", "memory_agent"),
            "project_request": ("project", "project_agent"),
            "unknown": ("knowledge_lookup", "research_agent"),
        }

    def normalize(self, text: str) -> str:
        return normalize_arabic_text(text)

    def analyze(self, text: str) -> ArabicSemanticEvidence:
        normalized = self.normalize(text)
        tokens = normalized.split()
        direct_addressed = "امير" in tokens or normalized.startswith("امير ") or normalized == "امير"
        matched_signals: list[str] = []

        if not normalized:
            intent, agent = self._route_for("unknown")
            return ArabicSemanticEvidence(
                original_text=text,
                normalized_text=normalized,
                category="unknown",
                confidence=0.0,
                preferred_intent=intent,
                preferred_agent=agent,
                matched_signals=[],
                direct_addressed=False,
                is_arabic=False,
            )

        is_arabic = any("\u0600" <= ch <= "\u06ff" for ch in normalized)

        if (direct_addressed and len(tokens) <= 2) or (normalized in GREETINGS):
            matched_signals.extend([phrase for phrase in GREETINGS if phrase in normalized])
            if direct_addressed and len(tokens) <= 2:
                matched_signals.append("direct_name_call")
            return self._build_evidence(
                text,
                normalized,
                "greeting",
                0.98,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if has_any_phrase(normalized, PROJECT_REQUESTS):
            matched_signals.extend([phrase for phrase in PROJECT_REQUESTS if phrase in normalized])
            return self._build_evidence(
                text,
                normalized,
                "project_request",
                0.84,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if has_any_phrase(normalized, IDENTITY_REQUESTS):
            matched_signals.extend([phrase for phrase in IDENTITY_REQUESTS if phrase in normalized])
            return self._build_evidence(
                text,
                normalized,
                "identity_request",
                0.97,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if has_any_phrase(normalized, MEMORY_REQUESTS):
            matched_signals.extend([phrase for phrase in MEMORY_REQUESTS if phrase in normalized])
            return self._build_evidence(
                text,
                normalized,
                "memory_request",
                0.95,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if self._looks_like_execution(normalized):
            matched_signals.extend([verb for verb in EXECUTION_VERBS if verb in normalized])
            return self._build_evidence(
                text,
                normalized,
                "execution_request",
                0.97,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if direct_addressed and has_any_phrase(normalized, DIRECT_OPINION_PHRASES):
            matched_signals.extend([phrase for phrase in DIRECT_OPINION_PHRASES if phrase in normalized])
            return self._build_evidence(
                text,
                normalized,
                "direct_opinion",
                0.94,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if has_any_phrase(normalized, RESEARCH_REQUESTS):
            matched_signals.extend([phrase for phrase in RESEARCH_REQUESTS if phrase in normalized])
            return self._build_evidence(
                text,
                normalized,
                "research_request",
                0.92,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if has_any_phrase(normalized, ANALYSIS_REQUESTS):
            matched_signals.extend([phrase for phrase in ANALYSIS_REQUESTS if phrase in normalized])
            return self._build_evidence(
                text,
                normalized,
                "analysis_request",
                0.88,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if direct_addressed and self._has_question_cue(normalized):
            cue = next((cue for cue in QUESTION_CUES if cue in normalized), None)
            if cue:
                matched_signals.append(cue)
            return self._build_evidence(
                text,
                normalized,
                "direct_question",
                0.79,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        if direct_addressed and "?" in text:
            matched_signals.append("question_mark")
            return self._build_evidence(
                text,
                normalized,
                "direct_question",
                0.72,
                matched_signals,
                direct_addressed,
                is_arabic,
            )

        intent, agent = self._route_for("unknown")
        return ArabicSemanticEvidence(
            original_text=text,
            normalized_text=normalized,
            category="unknown",
            confidence=0.45 if is_arabic else 0.2,
            preferred_intent=intent,
            preferred_agent=agent,
            matched_signals=matched_signals,
            direct_addressed=direct_addressed,
            is_arabic=is_arabic,
        )

    def suggest_route(self, text: str) -> dict[str, str | float | list[str]]:
        evidence = self.analyze(text)
        return {
            "semantic_category": evidence.category,
            "intent": evidence.preferred_intent,
            "agent": evidence.preferred_agent,
            "confidence": evidence.confidence,
            "signals": list(evidence.matched_signals),
        }

    def _build_evidence(
        self,
        original_text: str,
        normalized_text: str,
        category: str,
        confidence: float,
        matched_signals: List[str],
        direct_addressed: bool,
        is_arabic: bool,
    ) -> ArabicSemanticEvidence:
        intent, agent = self._route_for(category)
        return ArabicSemanticEvidence(
            original_text=original_text,
            normalized_text=normalized_text,
            category=category,
            confidence=confidence,
            preferred_intent=intent,
            preferred_agent=agent,
            matched_signals=matched_signals,
            direct_addressed=direct_addressed,
            is_arabic=is_arabic,
        )

    def _route_for(self, category: str) -> tuple[str, str]:
        return self._route_map.get(category, self._route_map["unknown"])

    def _looks_like_execution(self, normalized: str) -> bool:
        if not has_any_phrase(normalized, EXECUTION_VERBS):
            return False

        if normalized.startswith(tuple(QUESTION_CUES)):
            return False

        if not has_any_phrase(normalized, EXECUTION_TARGETS):
            return False

        start_tokens = normalized.split()[:3]
        start_text = " ".join(start_tokens)
        for verb in EXECUTION_VERBS:
            if start_text.startswith(verb):
                return True
            if normalized.startswith(f"امير {verb}"):
                return True
            if normalized.startswith(f"يا امير {verb}"):
                return True
        return False

    def _has_question_cue(self, normalized: str) -> bool:
        return any(cue in normalized for cue in QUESTION_CUES)
