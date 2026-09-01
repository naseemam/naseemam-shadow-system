"""Founder Directive integrity layer.

This module preserves the Founder's original directive as the authoritative
semantic source. Normalization, intent classification, decomposition, routing,
LLM interpretation, and assistant/provider transformations may add structure,
but may not silently replace, narrow, soften, redirect, or expand the directive.

Derived interpretations are evidence, never authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple


PROHIBITED_TRANSFORMATIONS = {
    "narrow",
    "soften",
    "redirect",
    "substitute",
    "expand_scope",
    "add_approval_gate",
    "remove_explicit_exception",
    "change_final_decision_owner",
}


@dataclass(frozen=True)
class FounderDirective:
    original_text: str
    derived_text: str
    source: str = "founder"
    previous_goal: str = ""
    interpretation_notes: Tuple[str, ...] = field(default_factory=tuple)
    explicit_constraints: Tuple[str, ...] = field(default_factory=tuple)
    semantic_authority: str = "original_text"

    def as_context(self) -> Dict[str, Any]:
        return {
            "founder_directive": self.original_text,
            "derived_interpretation": self.derived_text,
            "semantic_authority": self.semantic_authority,
            "source": self.source,
            "previous_goal": self.previous_goal,
            "interpretation_notes": list(self.interpretation_notes),
            "explicit_constraints": list(self.explicit_constraints),
            "directive_integrity_rule": (
                "derived interpretation may organize execution but may not replace, "
                "narrow, soften, redirect, expand, or override the Founder directive"
            ),
        }


def create_directive(
    original_text: str,
    *,
    derived_text: Optional[str] = None,
    source: str = "founder",
    previous_goal: str = "",
    interpretation_notes: Optional[Iterable[str]] = None,
    explicit_constraints: Optional[Iterable[str]] = None,
) -> FounderDirective:
    original = (original_text or "").strip()
    if not original:
        raise ValueError("Founder directive must not be empty")
    derived = (derived_text if derived_text is not None else original).strip()
    if not derived:
        derived = original
    return FounderDirective(
        original_text=original,
        derived_text=derived,
        source=source,
        previous_goal=(previous_goal or "").strip(),
        interpretation_notes=tuple(interpretation_notes or ()),
        explicit_constraints=tuple(explicit_constraints or ()),
    )


def validate_interpretation(
    directive: FounderDirective,
    *,
    transformation_types: Optional[Iterable[str]] = None,
    added_approval_requirement: bool = False,
) -> Dict[str, Any]:
    """Validate that a derived interpretation did not claim authority over Founder intent.

    Semantic equivalence itself may require an LLM or domain-specific checker. This
    deterministic layer enforces the non-negotiable structural rules and exposes
    any declared semantic transformation for blocking/audit.
    """
    declared = {str(item).strip().lower() for item in (transformation_types or ()) if str(item).strip()}
    violations = sorted(declared & PROHIBITED_TRANSFORMATIONS)
    if added_approval_requirement:
        violations.append("add_approval_gate")
    return {
        "valid": not violations,
        "violations": sorted(set(violations)),
        "semantic_authority": directive.semantic_authority,
        "original_text": directive.original_text,
        "derived_text": directive.derived_text,
    }


def execution_payload(directive: FounderDirective, **extra: Any) -> Dict[str, Any]:
    """Build an execution payload that always carries both original and derived text."""
    payload = directive.as_context()
    payload.update(extra)
    return payload
