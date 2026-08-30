"""Ameer self-development and capability acquisition contract.

Ameer's skills are not a closed list. He may discover candidate capabilities from
the web, documentation, repositories, tools and trusted technical sources,
evaluate them, test them in a controlled scope, adopt successful candidates and
retire weak or obsolete implementations.

The Founder should not need to manually re-program Ameer for every new skill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


SELF_DEVELOPMENT_PHASES: Tuple[str, ...] = (
    "observe_limitations",
    "search_for_candidate_skill",
    "review_sources_and_requirements",
    "design_or_select_candidate",
    "sandbox_or_controlled_test",
    "evaluate_result",
    "adopt_or_reject",
    "register_capability",
    "monitor_real_use",
    "improve_or_replace",
)


@dataclass(frozen=True)
class SkillCandidate:
    name: str
    source: str
    purpose: str
    requires_new_root_asset: bool = False
    requires_financial_commitment: bool = False
    requires_external_top_level_access: bool = False


def self_development_policy() -> Dict[str, object]:
    return {
        "skills_are_open_ended": True,
        "web_research_for_new_skills": True,
        "documentation_research": True,
        "repository_research": True,
        "controlled_testing_before_adoption": True,
        "automatic_capability_registration_after_successful_validation": True,
        "continuous_benchmarking": True,
        "replace_obsolete_implementations": True,
        "founder_not_required_for_routine_skill_acquisition": True,
        "sovereign_gate_rule": "only_a_preclassified_sovereign_action_pauses_adoption_or_execution",
        "phases": list(SELF_DEVELOPMENT_PHASES),
    }
