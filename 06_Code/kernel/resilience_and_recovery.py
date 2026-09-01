"""Ameer resilience, recovery and self-operation contract.

Ameer must be able to operate, diagnose, repair, restore and rebuild his execution
environment without depending on one provider, model, deployment or operator.
Identity and durable state live in the platform harness and recoverable state, not
in a transient inference model.
"""

from __future__ import annotations

from typing import Dict, Tuple


RECOVERY_PHASES: Tuple[str, ...] = (
    "detect_failure",
    "identify_surviving_state",
    "restore_constitution_and_identity",
    "restore_persistent_goals",
    "restore_memory_and_permissions",
    "restore_capability_registry",
    "restore_connectors_and_credentials_from_secure_store",
    "restore_or_replace_model_provider",
    "restore_execution_services",
    "verify_health",
    "resume_incomplete_goals",
)

CORE_DOMAINS: Tuple[str, ...] = (
    "software_engineering",
    "coding_and_codex_style_execution",
    "systems_architecture",
    "infrastructure_and_devops",
    "operational_management",
    "executive_management",
    "financial_analysis_and_operations",
    "business_operations",
    "data_analysis",
    "security_and_credential_operations",
    "research_and_web_navigation",
)


def resilience_policy() -> Dict[str, object]:
    return {
        "self_operation_required": True,
        "self_diagnosis_required": True,
        "self_repair_required": True,
        "backup_restore_required": True,
        "cold_start_recovery_required": True,
        "provider_independence": True,
        "model_independence": True,
        "deployment_independence": True,
        "single_operator_dependency": False,
        "resume_persistent_goals_after_recovery": True,
        "core_domains": list(CORE_DOMAINS),
        "recovery_phases": list(RECOVERY_PHASES),
    }
