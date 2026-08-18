import json

from fastapi.testclient import TestClient

import ameer_server


def test_booking_alias_and_production_fixture_guard(monkeypatch):
    client = TestClient(ameer_server.app)
    monkeypatch.delenv("AMEER_TEST_MODE", raising=False)
    monkeypatch.setenv("AMEER_ENV", "production")
    response = client.post("/test/booking/confirm", json={"scenario": "available", "actor": "ameer"})
    assert response.status_code == 404
    assert response.json()["reason"] == "test_endpoint_disabled_in_production"


def test_isolated_booking_fixtures(monkeypatch):
    client = TestClient(ameer_server.app)
    monkeypatch.setenv("AMEER_TEST_MODE", "true")
    monkeypatch.setenv("AMEER_ENV", "test")

    denied = client.post("/test/booking/confirm", json={"scenario": "available", "actor": "employee"})
    assert denied.status_code == 403
    assert denied.json()["reason"] == "ameer_authority_required"

    available = client.post("/test/booking/confirm", json={"scenario": "available", "actor": "ameer"})
    assert available.status_code == 200
    assert available.json()["status"] == "confirmed"
    assert available.json()["fixture"] is True

    conflict = client.post("/test/booking/confirm", json={"scenario": "conflict", "actor": "ameer"})
    assert conflict.status_code == 409
    assert conflict.json()["reason"] == "booking_conflict_detected"


def test_official_booking_aliases_exist():
    paths = {route.path for route in ameer_server.app.routes}
    assert "/booking/confirm" in paths
    assert "/center/bookings/confirm" in paths
