"""Central connector ownership and health policy for Ameer.

Ameer owns operational connector lifecycle across every Shadow System project.
Connector routing is project-scoped through Project Gateway. Secret values are
stored outside logs and registry metadata.
"""

from dataclasses import dataclass
from typing import Tuple

CONNECTOR_CLASSES: Tuple[str, ...] = (
    "github",
    "railway",
    "cloudflare",
    "google_workspace",
    "gmail",
    "google_calendar",
    "google_drive",
    "google_sheets",
    "whatsapp",
    "tiktok",
    "payment_gateways",
    "tabby",
    "tamara",
    "trading_platforms",
    "investment_funds",
    "other_project_connectors",
)

CONNECTOR_REGISTRY_FIELDS: Tuple[str, ...] = (
    "connector_id",
    "connector_type",
    "project_id",
    "environment",
    "capabilities",
    "permission_scope",
    "credential_reference",
    "connection_status",
    "last_health_check_at",
    "last_success_at",
    "last_error_code",
    "token_expiry_at_when_known",
    "recovery_strategy",
    "retry_policy",
    "owner",
)

CONNECTOR_HEALTH_STATES: Tuple[str, ...] = (
    "healthy",
    "degraded",
    "authentication_required",
    "rate_limited",
    "unreachable",
    "misconfigured",
    "recovering",
    "disabled",
)

CONNECTOR_LIFECYCLE: Tuple[str, ...] = (
    "discover_requirement",
    "select_official_or_supported_connector",
    "obtain_or_create_scoped_operational_credential_when_supported",
    "store_secret_in_secret_store",
    "register_metadata_without_secret_value",
    "connect_to_project_scope",
    "verify_connection",
    "monitor_health",
    "refresh_or_rotate_operational_credential_when_needed",
    "retry_and_recover",
    "record_redacted_execution_evidence",
)


@dataclass(frozen=True)
class ConnectorOrchestrationContract:
    operational_owner: str = "ameer"
    centralized_registry: bool = True
    secrets_stored_outside_registry: bool = True
    secret_values_forbidden_in_execution_logs: bool = True
    project_gateway_enforces_project_isolation: bool = True
    connector_health_visible_in_administration: bool = True
    ameer_may_create_scoped_operational_credentials_when_platform_supports_it: bool = True
    ameer_may_refresh_and_rotate_operational_tokens: bool = True
    ameer_may_repair_and_reconnect_without_founder_micro_approval: bool = True
    principal_root_credential_change_uses_existing_sovereign_gate: bool = True
    unverified_service_critical_revocation_uses_existing_sovereign_gate: bool = True
    connectors_are_replaceable_resources_not_ameer_identity: bool = True


def connector_orchestration_contract() -> ConnectorOrchestrationContract:
    return ConnectorOrchestrationContract()
