"""Always-on autonomous operations contract for Ameer.

Ameer is expected to operate as a persistent service, not as a chat session that
waits for the Founder to reopen the application.
"""

from __future__ import annotations

from typing import Dict, Tuple


ALWAYS_ON_DOMAINS: Tuple[str, ...] = (
    "websites",
    "repositories",
    "systems",
    "programs",
    "deployments",
    "endpoints",
    "connectors",
    "commerce_operations",
    "inventory",
    "bookings",
    "customer_journeys",
)


def always_on_operations_contract() -> Dict[str, object]:
    return {
        "service_mode": "continuous_24_7",
        "requires_founder_presence": False,
        "requires_chat_session_open": False,
        "requires_manual_wake": False,
        "domains": list(ALWAYS_ON_DOMAINS),
        "may_continue_persistent_goals": True,
        "may_generate_next_tasks": True,
        "may_monitor_health": True,
        "may_repair_operational_failures": True,
        "may_resume_after_restart": True,
        "founder_interruption_rule": (
            "interrupt_only_for_preclassified_sovereign_decision_or_material_attention_event"
        ),
        "ordinary_operational_work": "continue_without_waiting_for_founder",
    }
