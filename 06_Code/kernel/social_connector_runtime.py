"""Operational dispatch rules for WhatsApp and TikTok connectors.

This module is provider-neutral. It never treats a planned action as delivered.
An authenticated, healthy connector with the required capability must exist, and
provider results are required before delivery/publish state can advance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple


READY_STATES = {"healthy", "degraded"}

WHATSAPP_REQUIRED_CAPABILITIES: Tuple[str, ...] = (
    "send_message",
    "receive_webhook",
    "delivery_status",
)

TIKTOK_OPTIONAL_CAPABILITIES: Tuple[str, ...] = (
    "publish_content",
    "read_account_metrics",
    "read_content_metrics",
    "receive_supported_engagement_events",
    "reply_to_supported_customer_interactions",
)


def connector_ready(
    connector: Mapping[str, object], *, required_capability: str
) -> bool:
    capabilities = set(connector.get("capabilities") or ())
    return (
        connector.get("connection_status") in READY_STATES
        and bool(connector.get("credential_reference"))
        and required_capability in capabilities
    )


def _require_ready(connector: Mapping[str, object], capability: str) -> None:
    if not connector_ready(connector, required_capability=capability):
        raise ValueError(f"connector_not_ready_for:{capability}")


@dataclass(frozen=True)
class DispatchPlan:
    channel: str
    operation: str
    project_id: str
    subject_id: str
    idempotency_key: str
    payload: Dict[str, object]
    state: str = "planned"


def plan_whatsapp_message(
    *,
    connector: Mapping[str, object],
    project_id: str,
    subject_id: str,
    message_kind: str,
    body: str,
    idempotency_key: str,
    customer_contact_allowed: Optional[bool] = None,
    recipient_kind: str = "customer",
) -> DispatchPlan:
    _require_ready(connector, "send_message")
    if recipient_kind == "customer" and customer_contact_allowed is not True:
        raise ValueError("customer_contact_not_allowed")
    if not body.strip():
        raise ValueError("message_body_required")
    return DispatchPlan(
        channel="whatsapp",
        operation="send_message",
        project_id=project_id,
        subject_id=subject_id,
        idempotency_key=idempotency_key,
        payload={
            "message_kind": message_kind,
            "body": body,
            "recipient_kind": recipient_kind,
        },
    )


def plan_tiktok_operation(
    *,
    connector: Mapping[str, object],
    project_id: str,
    operation: str,
    subject_id: str,
    payload: Mapping[str, object],
    idempotency_key: str,
) -> DispatchPlan:
    if operation not in TIKTOK_OPTIONAL_CAPABILITIES:
        raise ValueError("unsupported_tiktok_operation")
    _require_ready(connector, operation)
    return DispatchPlan(
        channel="tiktok",
        operation=operation,
        project_id=project_id,
        subject_id=subject_id,
        idempotency_key=idempotency_key,
        payload=dict(payload),
    )


def apply_provider_result(
    plan: DispatchPlan,
    result: Mapping[str, object],
) -> Dict[str, object]:
    """Advance state only from explicit provider evidence."""
    provider_status = str(result.get("status") or "").lower()
    provider_id = result.get("provider_message_id") or result.get("provider_operation_id")
    if provider_status in {"sent", "accepted", "published", "delivered"} and not provider_id:
        raise ValueError("provider_evidence_id_required")
    if provider_status not in {"sent", "accepted", "published", "delivered", "failed", "rejected"}:
        raise ValueError("unsupported_provider_status")
    return {
        "channel": plan.channel,
        "operation": plan.operation,
        "project_id": plan.project_id,
        "subject_id": plan.subject_id,
        "idempotency_key": plan.idempotency_key,
        "state": provider_status,
        "provider_reference": provider_id,
        "provider_error_code": result.get("error_code"),
        "delivery_claim_is_provider_backed": provider_status in {"sent", "accepted", "published", "delivered"},
    }


@dataclass(frozen=True)
class SocialConnectorRuntimeContract:
    ameer_is_operational_owner: bool = True
    whatsapp_requires_authenticated_healthy_connector: bool = True
    customer_whatsapp_respects_contact_preference: bool = True
    founder_operational_digest_is_not_customer_marketing: bool = True
    tiktok_actions_require_explicit_provider_capability: bool = True
    planned_action_is_never_treated_as_delivered: bool = True
    provider_reference_required_for_success_claim: bool = True
    idempotency_key_required_for_external_dispatch: bool = True
    secrets_never_live_in_dispatch_payload: bool = True


def runtime_contract() -> SocialConnectorRuntimeContract:
    return SocialConnectorRuntimeContract()
