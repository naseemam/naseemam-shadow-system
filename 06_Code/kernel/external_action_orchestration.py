"""External real-world action orchestration for Ameer.

Ameer researches, compares, discusses, prepares and executes external work.  Routine
operational steps are autonomous.  A Founder decision is requested only at the final
specific commitment when that commitment crosses a preclassified sovereign gate,
such as an actual financial commitment or another irreversible sovereign action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


EXTERNAL_ACTION_PHASES: Tuple[str, ...] = (
    "understand_request",
    "research_options",
    "compare_options",
    "negotiate_or_discuss_when_supported",
    "prepare_complete_package",
    "present_final_decision",
    "execute_after_required_final_decision",
    "verify_completion",
    "deliver_confirmation_and_documents",
)


@dataclass(frozen=True)
class ExternalActionPlan:
    action_type: str
    phases: Tuple[str, ...]
    final_commitment_may_require_founder_decision: bool
    manual_handoff_is_default: bool = False


def plan_external_action(action_type: str) -> ExternalActionPlan:
    return ExternalActionPlan(
        action_type=action_type,
        phases=EXTERNAL_ACTION_PHASES,
        final_commitment_may_require_founder_decision=True,
    )


def travel_booking_contract() -> Dict[str, object]:
    return {
        "supported_scope": [
            "hotel_research",
            "hotel_comparison",
            "room_selection",
            "package_comparison",
            "flight_or_transport_research",
            "itinerary_building",
            "traveler_detail_preparation",
            "reservation_preparation",
            "post_approval_booking_execution",
            "confirmation_collection",
            "document_delivery",
        ],
        "research_and_preparation_are_autonomous": True,
        "final_financial_commitment_uses_sovereign_gate": True,
        "execution_continues_after_founder_decision": True,
        "connector_or_site_limitations_are_technical_blockers_not_new_approval_gates": True,
    }


def ordinary_device_operation_contract() -> Dict[str, object]:
    return {
        "examples": ["turn_off_light", "turn_on_light", "adjust_authorized_device"],
        "routine_operation_requires_founder_approval": False,
        "policy_layer_may_not_invent_human_approval": True,
        "technical_device_authorization_still_applies": True,
    }
