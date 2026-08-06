"""
test_p05_memory_governance.py
=============================
P0.5 Memory Governance acceptance tests.
"""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class MemoryGovernanceUnitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        approval_mod = _load("approval_gate_p05", os.path.join(CODE_ROOT, "kernel", "approval_gate.py"))
        gov_mod = _load("memory_governance_p05", os.path.join(CODE_ROOT, "kernel", "memory_governance.py"))
        self.gate = approval_mod.ApprovalGate(self._tmp)
        self.gov = gov_mod.MemoryGovernanceEngine(self._tmp, self.gate)

    def test_founder_memory_requires_approval(self):
        result = self.gov.submit_candidate(content="تفضيلي أن يكون الرد بالعربية", requested_layer="founder_memory")
        self.assertFalse(result["saved"])
        self.assertEqual(result["status"], "pending_approval")
        self.assertIn("approval_id", result)

    def test_non_sensitive_learned_knowledge_stores_without_approval(self):
        result = self.gov.submit_candidate(
            content="ممارسة تشغيلية موصى بها: بدء كل جلسة بملخص قصير",
            requested_layer="learned_knowledge",
            source="runtime",
        )
        self.assertTrue(result["saved"])
        item = result["memory_item"]
        self.assertEqual(item["memory_type"], "learned_knowledge")
        self.assertEqual(item["approval_state"], "not_required")
        for key in ("source", "timestamp", "confidence", "approval_state"):
            self.assertIn(key, item)

    def test_sensitive_content_in_learned_layer_requires_approval(self):
        result = self.gov.submit_candidate(
            content="حالتي الصحية تحتاج متابعة أسبوعية",
            requested_layer="learned_knowledge",
        )
        self.assertFalse(result["saved"])
        self.assertEqual(result["status"], "pending_approval")

    def test_approval_finalizes_founder_memory_storage(self):
        result = self.gov.submit_candidate(content="هدفي الحالي هو إطلاق الإصدار هذا الشهر", requested_layer="founder_memory")
        approval_id = result["approval_id"]
        approved = self.gate.approve(approval_id, approved_by="naseem")
        self.assertTrue(approved)
        finalized = self.gov.finalize_approval(approval_id, approved_by="naseem")
        self.assertTrue(finalized["stored"])
        items = self.gov.list_items("founder_memory")
        self.assertTrue(any(x.get("approval_state") == "approved" for x in items))

    def test_promotion_requires_explicit_call_and_logs_governance(self):
        saved = self.gov.submit_candidate(content="ممارسة تشغيلية: مراجعة أولويات المشروع في بداية كل دورة", requested_layer="learned_knowledge")
        item_id = saved["memory_item"]["id"]
        promoted = self.gov.promote_learned_to_core(item_id, reason="اعتماد مؤسسي", approved_by="naseem")
        self.assertEqual(promoted["from_layer"], "learned_knowledge")
        self.assertEqual(promoted["to_layer"], "core_knowledge")
        snap = self.gov.snapshot()
        self.assertGreaterEqual(snap["governance_log_entries"], 1)


class MemoryGovernanceServerTests(unittest.TestCase):
    def setUp(self):
        import ameer_server

        self.client = TestClient(ameer_server.app)

    def test_memory_post_returns_pending_approval_by_default(self):
        resp = self.client.post("/memory", json={"text": "أفضّل أن تبدأ كل جلسة بتقرير سريع"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["saved"])
        self.assertEqual(data["status"], "pending_approval")
        self.assertIn("approval_id", data)

    def test_approve_flow_stores_founder_item_with_required_metadata(self):
        post = self.client.post("/memory", json={"text": "هدفي هذا الأسبوع هو إغلاق P0.5"})
        approval_id = post.json()["approval_id"]
        approve = self.client.post(f"/approvals/{approval_id}/approve", json={"approved_by": "naseem"})
        self.assertEqual(approve.status_code, 200)

        founder_items = self.client.get("/memory/items/founder_memory")
        self.assertEqual(founder_items.status_code, 200)
        items = founder_items.json()["items"]
        target = next((x for x in items if "إغلاق P0.5" in x.get("content", "")), None)
        self.assertIsNotNone(target)
        for key in ("source", "timestamp", "confidence", "approval_state"):
            self.assertIn(key, target)
        self.assertEqual(target["approval_state"], "approved")

    def test_delete_memory_item_without_system_breakage(self):
        post = self.client.post("/memory", json={"text": "نقطة مؤقتة للحذف لاحقًا"})
        approval_id = post.json()["approval_id"]
        self.client.post(f"/approvals/{approval_id}/approve", json={"approved_by": "naseem"})
        founder_items = self.client.get("/memory/items/founder_memory").json()["items"]
        target = next((x for x in founder_items if "للحذف لاحقًا" in x.get("content", "")), None)
        self.assertIsNotNone(target)

        delete = self.client.delete(f"/memory/items/founder_memory/{target['id']}")
        self.assertEqual(delete.status_code, 200)

        health = self.client.get("/kernel/health")
        self.assertEqual(health.status_code, 200)


if __name__ == "__main__":
    unittest.main()
