import os
import tempfile


def test_agent_channel_smoke():
    with tempfile.TemporaryDirectory() as data_dir:
        os.environ["AMEER_DATA_DIR"] = data_dir
        from fastapi.testclient import TestClient
        from ameer_server import app

        client = TestClient(app)
        authority = client.get("/agent/authority")
        assert authority.status_code == 200, authority.text
        payload = authority.json()
        assert payload["executive"] == "ameer"
        assert len(payload["workers"]) == 8
        assert "store" in payload["workers"]
        assert payload["worker_direct_founder_contact"] is False

        orchestrator = client.get("/orchestrator/status")
        assert orchestrator.status_code == 200, orchestrator.text
        assert orchestrator.json()["executive"] == "ameer"
        audit = client.get("/audit/execution")
        assert audit.status_code == 200, audit.text
        assert audit.json()["audit"]["owner"] == "ameer"
        assert audit.json()["audit"]["append_only"] is True

        center = client.get("/center/dashboard")
        assert center.status_code == 200, center.text
        assert center.json()["center"]["name"] == "مركز حلم الندى"
        assert set(center.json()["modules"]) >= {"inventory", "employees", "bookings"}
        customers = client.get("/center/customers")
        assert customers.status_code == 200, customers.text
        assert customers.json()["customers"] == []

        incoming = client.post(
            "/agent/messages",
            json={"sender": "user", "body": "راجع حالة الموقع", "channel": "web"},
        )
        assert incoming.status_code == 200, incoming.text
        assert incoming.json()["message"]["recipient"] == "ameer"

        blocked = client.post(
            "/agent/delegate",
            json={"worker_id": "design", "objective": "حلل الواجهة"},
        )
        assert blocked.status_code == 422, blocked.text
        assert blocked.json()["reason"] == "ameer_review_required"

        pending = client.post(
            "/agent/delegate",
            json={
                "worker_id": "design",
                "objective": "انشر الإصدار في الإنتاج",
                "ameer_review": True,
                "external_effect": True,
                "approval_action": "publish",
            },
        )
        assert pending.status_code == 202, pending.text
        pending_data = pending.json()
        assert pending_data["status"] == "pending_final_approval"
        assert pending_data["approval_id"]

        messages = client.get("/agent/messages").json()["messages"]
        assert any(
            item["kind"] == "final_approval_request" and item["recipient"] == "user"
            for item in messages
        )
