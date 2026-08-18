from pathlib import Path

import pytest

from kernel.commerce_test_environment import CommerceTestEnvironment


def test_test_environment_isolated_and_no_real_effects(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = env.create_order(customer_name="عميلة اختبار", total=250)
    assert order["project_id"] == "dream_al_nada_store"
    assert order["payment_status"] == "pending"
    session = env.create_payment_session(order["id"])
    assert session["no_real_charge"] is True
    with pytest.raises(ValueError, match="shipment_requires_paid_test_order"):
        env.create_test_shipment(order["id"])


def test_payment_webhook_is_idempotent_and_unlocks_test_shipment(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = env.create_order(customer_name="عميلة اختبار", total=180)
    payload = {"event_id": "evt-1", "order_id": order["id"], "event_type": "payment.updated", "status": "paid"}
    first = env.process_payment_webhook(event_id="evt-1", order_id=order["id"], event_type="payment.updated", status="paid", payload=payload)
    assert first["status"] == "processed"
    assert first["order"]["payment_status"] == "paid"
    duplicate = env.process_payment_webhook(event_id="evt-1", order_id=order["id"], event_type="payment.updated", status="paid", payload=payload)
    assert duplicate["status"] == "duplicate_ignored"
    shipment = env.create_test_shipment(order["id"])
    assert shipment["status"] == "created"
    assert shipment["no_real_shipment"] is True


def test_unknown_payment_status_is_rejected(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = env.create_order(customer_name="عميلة اختبار", total=100)
    with pytest.raises(ValueError, match="unsupported_test_payment_status"):
        env.process_payment_webhook(event_id="evt-x", order_id=order["id"], event_type="payment.updated", status="captured_live", payload={})
