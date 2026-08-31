import pytest

from kernel.social_connector_runtime import (
    apply_provider_result,
    connector_ready,
    plan_tiktok_operation,
    plan_whatsapp_message,
    runtime_contract,
)


def _connector(*capabilities, status="healthy"):
    return {
        "connector_id": "conn-1",
        "project_id": "hilm",
        "connection_status": status,
        "credential_reference": "secret://hilm/social/1",
        "capabilities": capabilities,
    }


def test_whatsapp_requires_authenticated_healthy_capability():
    connector = _connector("send_message", "receive_webhook", "delivery_status")
    assert connector_ready(connector, required_capability="send_message") is True
    broken = dict(connector, credential_reference="")
    assert connector_ready(broken, required_capability="send_message") is False


def test_customer_whatsapp_respects_contact_preference():
    connector = _connector("send_message")
    with pytest.raises(ValueError, match="customer_contact_not_allowed"):
        plan_whatsapp_message(
            connector=connector,
            project_id="hilm",
            subject_id="cus-1",
            message_kind="booking_reminder",
            body="موعدك غدًا",
            idempotency_key="booking:bk-1:reminder:24h",
            customer_contact_allowed=False,
        )


def test_founder_digest_can_be_planned_without_customer_marketing_preference():
    connector = _connector("send_message")
    plan = plan_whatsapp_message(
        connector=connector,
        project_id="hilm",
        subject_id="founder",
        message_kind="purchase_digest",
        body="تقرير شراء مجمع",
        idempotency_key="purchase-digest:2026-09-01",
        recipient_kind="founder",
    )
    assert plan.channel == "whatsapp"
    assert plan.state == "planned"


def test_planned_whatsapp_is_not_claimed_sent_until_provider_evidence_exists():
    connector = _connector("send_message")
    plan = plan_whatsapp_message(
        connector=connector,
        project_id="hilm",
        subject_id="founder",
        message_kind="purchase_digest",
        body="تقرير شراء مجمع",
        idempotency_key="digest:1",
        recipient_kind="founder",
    )
    with pytest.raises(ValueError, match="provider_evidence_id_required"):
        apply_provider_result(plan, {"status": "sent"})
    result = apply_provider_result(
        plan,
        {"status": "sent", "provider_message_id": "wamid.123"},
    )
    assert result["state"] == "sent"
    assert result["delivery_claim_is_provider_backed"] is True


def test_tiktok_never_uses_capability_the_connector_does_not_expose():
    connector = _connector("read_account_metrics")
    with pytest.raises(ValueError, match="connector_not_ready_for:publish_content"):
        plan_tiktok_operation(
            connector=connector,
            project_id="hilm",
            operation="publish_content",
            subject_id="campaign-1",
            payload={"content_ref": "asset-1"},
            idempotency_key="tiktok:campaign-1:publish",
        )


def test_tiktok_publish_success_requires_provider_operation_reference():
    connector = _connector("publish_content")
    plan = plan_tiktok_operation(
        connector=connector,
        project_id="hilm",
        operation="publish_content",
        subject_id="campaign-1",
        payload={"content_ref": "asset-1"},
        idempotency_key="tiktok:campaign-1:publish",
    )
    result = apply_provider_result(
        plan,
        {"status": "published", "provider_operation_id": "tt-post-1"},
    )
    assert result["state"] == "published"
    assert result["provider_reference"] == "tt-post-1"


def test_runtime_contract_prevents_fake_delivery_claims():
    contract = runtime_contract()
    assert contract.ameer_is_operational_owner is True
    assert contract.planned_action_is_never_treated_as_delivered is True
    assert contract.provider_reference_required_for_success_claim is True
    assert contract.tiktok_actions_require_explicit_provider_capability is True
