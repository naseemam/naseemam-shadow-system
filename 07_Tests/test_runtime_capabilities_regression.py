import json
import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import ameer_server


class RuntimeCapabilitiesRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(ameer_server.app)
        self.workspace_root = Path(ameer_server.ROOT)
        self.target = self.workspace_root / "runtime_edit_test.md"
        self.original = self.target.read_text(encoding="utf-8") if self.target.exists() else None

    def tearDown(self):
        if self.target.exists():
            self.target.unlink()
        if self.original is not None:
            self.target.write_text(self.original, encoding="utf-8")

    def test_update_request_appends_to_existing_file(self):
        self.target.write_text("السطر الأول\n", encoding="utf-8")
        response = self.client.post(
            "/ask",
            json={"query": 'أضف سطرًا جديدًا في runtime_edit_test.md يقول "السطر الثاني"'},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        file_result = payload.get("execution_engine", {}).get("file") or {}
        self.assertEqual(file_result.get("status"), "updated")
        self.assertIn("السطر الثاني", self.target.read_text(encoding="utf-8"))

    def test_memory_recall_request_is_routed_as_memory(self):
        self.client.post("/memory", json={"text": "كلمة السر للمشروع هي sky-123"})
        response = self.client.post(
            "/ask",
            json={"query": "ما كلمة السر للمشروع؟"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("context", {}).get("intent"), "memory")


if __name__ == "__main__":
    unittest.main()
