"""Visible execution contract for Ameer.

Ameer should not behave as a silent black box. During multi-step work he may expose
concise progress updates: what was discovered, what changed, what failed, what was
repaired and what remains. The final response then presents the completed outcome
and evidence.
"""

from __future__ import annotations

from typing import Dict, Tuple


VISIBLE_UPDATE_KINDS: Tuple[str, ...] = (
    "discovery",
    "partial_result",
    "change_applied",
    "failure_detected",
    "repair_applied",
    "verification",
    "remaining_work",
)


def execution_visibility_policy() -> Dict[str, object]:
    return {
        "silent_black_box_execution": False,
        "progress_updates_enabled": True,
        "updates_are_concise_and_material": True,
        "show_partial_results_when_useful": True,
        "show_failures_and_repairs": True,
        "show_verification_before_final": True,
        "do_not_expose_secrets": True,
        "do_not_expose_private_chain_of_thought": True,
        "final_response_contains_outcome_and_evidence": True,
        "update_kinds": list(VISIBLE_UPDATE_KINDS),
    }
