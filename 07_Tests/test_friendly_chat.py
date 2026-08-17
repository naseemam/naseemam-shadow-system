import os


def test_friendly_chat_is_separate_and_non_executing(tmp_path):
    os.environ["AMEER_DATA_DIR"] = str(tmp_path)
    from fastapi.testclient import TestClient
    from ameer_server import app

    client = TestClient(app)
    friendly = client.post("/friendly-chat", json={"query": "كيف حالك اليوم؟", "room": "friendly"})
    assert friendly.status_code == 200, friendly.text
    payload = friendly.json()
    assert payload["room"] == "friendly"
    assert payload["status"] == "completed"
    assert payload["execution"]["started"] is False
    assert payload["execution"]["external_effect"] is False

    blocked = client.post("/friendly-chat", json={"query": "نفذ تعديل المخزون", "room": "friendly"})
    assert blocked.status_code == 200, blocked.text
    blocked_payload = blocked.json()
    assert blocked_payload["status"] == "room_switch_required"
    assert blocked_payload["execution"]["started"] is False
