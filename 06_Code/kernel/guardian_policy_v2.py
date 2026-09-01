"""Guardian v2: validation without invented authority.

Guardian may validate request structure, technical preconditions, and malformed
inputs. It does not classify ordinary execution as high risk and it cannot invent
Founder approval requirements. Sovereign approval comes only from ameer_authority.
"""

from __future__ import annotations

from typing import Optional

from kernel.ameer_authority import canonical_sovereign_action, requires_founder_approval


def guardian_check_v2(action: str, *, context: Optional[dict] = None) -> dict:
    ctx = context or {}
    canonical = canonical_sovereign_action(action, ctx)
    sovereign = requires_founder_approval(action, ctx)

    if sovereign:
        return {
            "status": "needs_approval",
            "mode": "sovereign_gate",
            "risk_level": "sovereign",
            "approval_action": canonical,
            "reason": "explicit_founder_reserved_sovereign_gate",
            "authority_source": "ameer_authority",
        }

    return {
        "status": "pass",
        "mode": "execution_ready",
        "risk_level": "delegated",
        "approval_action": None,
        "reason": "delegated_execution_not_a_sovereign_gate",
        "authority_source": "ameer_authority",
    }


def validate_request_shape(*, action: str, target: str = "") -> dict:
    """Technical validation is allowed, but it is not an approval gate."""
    if not str(action or "").strip():
        return {"valid": False, "reason": "missing_action", "approval_required": False}
    if target is not None and not isinstance(target, str):
        return {"valid": False, "reason": "invalid_target_type", "approval_required": False}
    return {"valid": True, "reason": "request_shape_valid", "approval_required": False}
