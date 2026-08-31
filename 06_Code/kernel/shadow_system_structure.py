"""Canonical information architecture for the Shadow System mother site."""

from dataclasses import dataclass
from typing import Dict, Tuple

MAIN_NAVIGATION: Tuple[str, ...] = (
    "home",
    "friendly_chat",
    "business_chat",
    "customer_supervision",
    "projects",
    "administration",
)

HOME_CARDS: Tuple[str, ...] = (
    "hilm_alnada",
    "school",
    "trading",
    "add_project",
)

HOME_SUMMARY_WIDGETS: Tuple[str, ...] = (
    "ameer_status",
    "system_status",
    "important_alerts",
    "urgent_sovereign_decisions",
    "quick_actions",
    "hilm_summary",
    "school_summary",
    "trading_summary",
)

HOME_EXCLUDED_DETAIL: Tuple[str, ...] = (
    "raw_file_details",
    "long_execution_log",
    "worker_internal_detail",
    "technical_test_tools",
    "raw_execution_commands",
)

PROJECTS: Dict[str, Tuple[str, ...]] = {
    "hilm_alnada": (
        "hilm_mother_site",
        "hilm_management_program",
        "hilm_project_status",
        "hilm_storefront_management",
    ),
    "school": (
        "school_dashboard",
        "projects_and_tasks",
        "content",
        "achievement_portfolio",
        "records_and_forms",
        "schedule_and_appointments",
        "reports",
        "project_settings",
        "google_sites_publishing",
    ),
    "trading": (
        "trading_dashboard",
        "trading_bot",
        "strategies",
        "signals",
        "trades",
        "open_positions",
        "order_log",
        "performance_and_risk",
        "trading_settings",
    ),
}

ADMINISTRATION: Tuple[str, ...] = (
    "sovereign_approvals",
    "permissions",
    "workers",
    "execution_log",
    "costs",
    "global_reports",
    "records",
    "identity_and_users",
    "system_settings",
    "ameer_settings",
    "project_gateway_settings",
    "system_and_connector_health",
)

CUSTOMER_SUPERVISION: Tuple[str, ...] = (
    "important_customer_conversations",
    "important_inquiries",
    "generated_bookings",
    "complaints",
    "change_requests",
    "intervention_required",
    "customer_ratings",
    "ameer_escalations",
)

APPROVAL_DECISION_STATES: Tuple[str, ...] = (
    "pending",
    "approved",
    "rejected",
    "modified",
)

EXECUTION_STATES: Tuple[str, ...] = (
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
)

APPROVAL_ACTIONS: Tuple[str, ...] = (
    "approve",
    "reject",
    "discuss",
    "modify",
    "view_details",
)

PROJECT_GATEWAY_FLOW: Tuple[str, ...] = (
    "user_or_interface",
    "project_gateway",
    "ameer_orchestrator",
    "worker_or_project_system",
    "project_gateway",
    "central_execution_log_and_result",
    "interface",
)


@dataclass(frozen=True)
class ShadowSystemContract:
    mother_site_is_top_level: bool = True
    founder_has_final_authority: bool = True
    ameer_has_cross_project_operational_authority: bool = True
    projects_have_isolated_data: bool = True
    project_gateway_is_router_not_competing_brain: bool = True
    customer_supervision_is_projection_not_duplicate_source: bool = True
    friendly_chat_does_not_auto_execute_without_clear_request: bool = True
    worker_direct_chat_available_when_exposed: bool = True
    worker_remains_scoped_under_ameer_coordination: bool = True
    approvals_only_for_preclassified_sovereign_decisions: bool = True
    approval_state_is_separate_from_execution_state: bool = True
    internal_project_workspace_creation_is_operational: bool = True
    independent_root_asset_creation_uses_sovereign_gate: bool = True


def shadow_system_contract() -> ShadowSystemContract:
    return ShadowSystemContract()
