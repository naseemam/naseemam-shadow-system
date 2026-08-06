import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import ameer_server


class RuntimeCapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(ameer_server.app)
        self.workspace_root = Path(ameer_server.ROOT)
        self.projects_file = self.workspace_root / ".ameer" / "projects.json"
        self.plans_file = self.workspace_root / ".ameer" / "plans.json"
        self.original_projects = self.projects_file.read_text(encoding="utf-8") if self.projects_file.exists() else None
        self.original_plans = self.plans_file.read_text(encoding="utf-8") if self.plans_file.exists() else None

    def tearDown(self):
        if self.original_projects is None and self.projects_file.exists():
            self.projects_file.unlink()
        elif self.original_projects is not None:
            self.projects_file.write_text(self.original_projects, encoding="utf-8")

        if self.original_plans is None and self.plans_file.exists():
            self.plans_file.unlink()
        elif self.original_plans is not None:
            self.plans_file.write_text(self.original_plans, encoding="utf-8")

    def test_documents_search_returns_matches(self):
        response = self.client.get("/documents/search", params={"q": "vision"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["results"])
        self.assertTrue(any(item["path"].endswith("Vision.md") for item in payload["results"]))

    def test_memory_endpoint_persists_note(self):
        response = self.client.post("/memory", json={"text": "test memory from runtime capability"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["saved"])
        self.assertEqual(payload["status"], "pending_approval")
        self.assertIn("approval_id", payload)

    def test_projects_endpoint_creates_project(self):
        response = self.client.post("/projects", json={"name": "Runtime Project"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["created"])
        self.assertTrue(any(item["name"] == "Runtime Project" for item in payload["projects"]))

    def test_memory_candidate_visible_in_candidates_endpoint(self):
        response = self.client.post("/memory", json={"text": "اسم مشروعي هو حلم الندى"})
        self.assertEqual(response.status_code, 200)
        payload = self.client.get("/memory/candidates")
        self.assertEqual(payload.status_code, 200)
        results = payload.json()["pending_candidates"]
        self.assertTrue(any("حلم الندى" in item.get("content", "") for item in results))

    def test_execution_engine_appends_to_existing_file(self):
        target = self.workspace_root / "04_Memory" / "runtime_edit_test.md"
        target.write_text("السطر الأول\n", encoding="utf-8")
        try:
            plan = type("Plan", (), {"steps": ["append file line"], "executive_message": "append", "memory_note": None})()
            result = ameer_server.EXECUTIVE_BRAIN._execute_plan(
                'أضف سطرًا جديدًا في 04_Memory/runtime_edit_test.md يقول "السطر الثاني"',
                plan,
                workspace_root=str(self.workspace_root),
            )
            self.assertEqual(result["status"], "completed")
            self.assertIn("السطر الثاني", target.read_text(encoding="utf-8"))
            self.assertEqual(result["file"]["status"], "updated")
        finally:
            if target.exists():
                target.unlink()

    def test_autonomy_plan_endpoint_persists_plan(self):
        response = self.client.post(
            "/autonomy/plan",
            json={"query": "Create a short plan to improve memory and planning", "goal": "autonomy"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["stored"])
        self.assertTrue(payload["plan"]["steps"])
        self.assertTrue(self.plans_file.exists())
        stored = json.loads(self.plans_file.read_text(encoding="utf-8"))
        self.assertTrue(any(item.get("query") == "Create a short plan to improve memory and planning" for item in stored))


if __name__ == "__main__":
    unittest.main()
