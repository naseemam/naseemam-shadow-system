"""Evidence-driven recovery loop for operational failures."""

from __future__ import annotations

from kernel.ameer_authority import requires_founder_approval

INCIDENT_PHASES = (
    "detect",
    "diagnose",
    "gather_evidence",
    "propose_fix",
    "execute_or_gate",
    "verify",
)


def recovery_decision(action: str, context=None):
    context = context or {}
    gated = requires_founder_approval(action, context)
    return {
        "action": action,
        "founder_approval_required": gated,
        "may_execute_fix_now": not gated,
        "approval_rule": "only_if_the_fix_crosses_a_preclassified_sovereign_gate",
        "failure_is_not_an_approval_gate": True,
        "phases": list(INCIDENT_PHASES),
        "must_return_diagnosis": True,
        "must_return_evidence": True,
        "must_verify_after_fix": True,
    }
