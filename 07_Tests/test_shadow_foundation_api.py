from fastapi.testclient import TestClient

from ameer_server import app


client = TestClient(app)


def test_shadow_foundation_endpoint_exposes_hierarchy_without_secrets():
    response = client.get("/shadow/foundation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["orchestrator"] == "ameer"
    project_ids = {item["project_id"] for item in payload["projects"]}
    assert {"dream_al_nada", "school", "trading"}.issubset(project_ids)
    assert payload["trading_execution_default"] == "disabled"
    assert "OPENAI_API_KEY" not in response.text
    assert "prompt" not in response.text.lower()


def test_shadow_projects_can_filter_by_parent():
    response = client.get("/shadow/projects", params={"parent_id": "dream_al_nada"})
    assert response.status_code == 200
    project_ids = {item["project_id"] for item in response.json()["projects"]}
    assert project_ids == {"dream_al_nada_admin", "dream_al_nada_status", "dream_al_nada_store"}


def test_shadow_policies_keep_trading_execution_disabled():
    response = client.get("/shadow/policies")
    assert response.status_code == 200
    payload = response.json()
    assert payload["trading_execution_default"] == "disabled"
    trading = next(item for item in payload["policies"] if item["capability"] == "trading.execute")
    assert trading["approval"] == "disabled_by_default"
