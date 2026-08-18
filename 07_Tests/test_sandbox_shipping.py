from pathlib import Path

import pytest

from kernel.commerce_test_environment import CommerceTestEnvironment


def _paid_order(env: CommerceTestEnvironment):
    order = env.create_order(customer_name="عميلة شحن اختبار", total=120)
    env.process_payment_webhook(
        event_id="payment_ship_1",
        order_id=order["id"],
        event_type="payment.updated",
        status="paid",
        payload={"event_id": "payment_ship_1", "status": "paid"},
    )
    return order


def test_shipping_requires_paid_order(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = env.create_order(customer_name="عميلة", total=100)
    with pytest.raises(ValueError, match="shipment_requires_paid_test_order"):
        env.create_test_shipment(order["id"])


def test_shipping_webhook_updates_tracking_and_is_idempotent(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = _paid_order(env)
    created = env.create_test_shipment(order["id"])
    shipment_id = created["shipment"]["id"]
    first = env.process_shipping_webhook(
        event_id="ship_evt_1",
        shipment_id=shipment_id,
        status="in_transit",
        payload={"event_id": "ship_evt_1", "status": "in_transit"},
    )
    assert first["status"] == "processed"
    assert first["shipment"]["status"] == "in_transit"
    duplicate = env.process_shipping_webhook(
        event_id="ship_evt_1",
        shipment_id=shipment_id,
        status="delivered",
        payload={"event_id": "ship_evt_1", "status": "delivered"},
    )
    assert duplicate["status"] == "duplicate_ignored"
    assert duplicate["shipment"]["status"] == "in_transit"
    tracking = env.get_test_shipment(order["id"])
    assert tracking["no_real_shipment"] is True
    assert tracking["shipment"]["tracking_number"].startswith("TEST")


def test_unsupported_shipping_status_rejected(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = _paid_order(env)
    shipment = env.create_test_shipment(order["id"])
    with pytest.raises(ValueError, match="unsupported_test_shipping_status"):
        env.process_shipping_webhook(
            event_id="ship_evt_bad",
            shipment_id=shipment["shipment"]["id"],
            status="unknown",
            payload={"event_id": "ship_evt_bad", "status": "unknown"},
        )


def test_snapshot_includes_shipping_events(tmp_path: Path):
    env = CommerceTestEnvironment(tmp_path)
    order = _paid_order(env)
    shipment = env.create_test_shipment(order["id"])
    env.process_shipping_webhook(
        event_id="ship_evt_2",
        shipment_id=shipment["shipment"]["id"],
        status="delivered",
        payload={"event_id": "ship_evt_2", "status": "delivered"},
    )
    snapshot = env.snapshot()
    assert snapshot["no_real_shipments"] is True
    assert snapshot["shipping_events"][0]["status"] == "delivered"
    assert snapshot["shipments"][0]["status"] == "delivered"
