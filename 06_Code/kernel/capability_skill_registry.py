"""Shared capability/skill abstraction for Ameer workers.

Workers receive capability handles, not raw service credentials.  A capability
owns its validation, permission requirements, connector binding and audit rules.
"""

from __future__ import annotations

from typing import Dict


DEFAULT_SKILLS: Dict[str, Dict[str, object]] = {
    "send_email": {"domain": "communications", "credential_exposure": False, "audited": True},
    "create_booking": {"domain": "commerce", "credential_exposure": False, "audited": True},
    "deploy_site": {"domain": "engineering", "credential_exposure": False, "audited": True},
    "issue_invoice": {"domain": "commerce", "credential_exposure": False, "audited": True},
    "update_inventory": {"domain": "commerce", "credential_exposure": False, "audited": True},
    "publish_content": {"domain": "communications", "credential_exposure": False, "audited": True},
}


def skill_registry_policy():
    return {
        "skills": DEFAULT_SKILLS,
        "workers_use_capability_handles": True,
        "workers_do_not_need_raw_service_keys": True,
        "permission_checks_live_with_capability": True,
        "validation_lives_with_capability": True,
        "connector_binding_lives_with_capability": True,
        "audit_lives_with_capability": True,
        "skills_are_reusable_across_workers": True,
    }
