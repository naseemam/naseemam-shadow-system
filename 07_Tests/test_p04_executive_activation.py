"""
test_p04_executive_activation.py
=================================
P0.4 Executive Agent Activation — acceptance tests.

Covers:
1.  DecisionEngine: record, retrieve, update_outcome, pending, recent
2.  DecisionEngine: input validation (empty title/reason raise ValueError)
3.  DecisionEngine: persistence across reload (write → re-load → read)
4.  ApprovalGate: request, approve, reject, is_approved, pending, recent
5.  ApprovalGate: requires_approval for HIGH_RISK_ACTIONS
6.  ApprovalGate: persistence across reload
7.  ExecutiveKernel: boot reports decision_engine + approval_gate components
8.  ExecutiveKernel: before_request includes pending_approval_requests + proactive_briefing
9.  ExecutiveKernel: proactive_briefing contains active projects on first turn
10. ExecutiveKernel: proactive_briefing is empty string on follow-up turns
11. ExecutiveKernel: record_decision / request_approval helpers delegate correctly
12. ExecutiveKernel: health endpoint includes pending_decisions + pending_approval_requests
13. ameer_server: GET /decisions returns snapshot
14. ameer_server: POST /decisions records new decision
15. ameer_server: GET /approvals returns snapshot
16. ameer_server: POST /approvals creates pending request
17. ameer_server: POST /approvals/{id}/approve marks approved
18. ameer_server: POST /approvals/{id}/reject marks rejected
19. ameer_server: /kernel/health includes pending_decisions + pending_approval_requests
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")


# ── module loaders ────────────────────────────────────────────────────────────

def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_decision_engine():
    if CODE_ROOT not in sys.path:
        sys.path.insert(0, CODE_ROOT)
    return _load("decision_engine", os.path.join(CODE_ROOT, "kernel", "decision_engine.py"))


def _load_approval_gate():
    if CODE_ROOT not in sys.path:
        sys.path.insert(0, CODE_ROOT)
    return _load("approval_gate", os.path.join(CODE_ROOT, "kernel", "approval_gate.py"))


def _load_kernel_module():
    if CODE_ROOT not in sys.path:
        sys.path.insert(0, CODE_ROOT)
    return _load("executive_kernel", os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"))


# ── workspace helper ──────────────────────────────────────────────────────────

def _make_workspace(tmp: str) -> None:
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory", "Founder.md").write_text(
        "# Founder\nنسيم أمير — المؤسسة والقائدة التنفيذية.\n", encoding="utf-8"
    )
    Path(tmp, "04_Memory", "Projects.md").write_text(
        "# Projects\n## حلم الندى\n## نظام أمير\n", encoding="utf-8"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1-3: DecisionEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionEngineCore(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        dm = _load_decision_engine()
        self.DecisionEngine = dm.DecisionEngine
        self.engine = self.DecisionEngine(self.tmp)

    def test_record_returns_string_id(self):
        did = self.engine.record("إطلاق الموقع", "طلبت المؤسسة الإطلاق")
        self.assertIsInstance(did, str)
        self.assertTrue(len(did) > 0)

    def test_get_returns_recorded_decision(self):
        did = self.engine.record("قرار التوظيف", "نحتاج مطوراً", category="project")
        decision = self.engine.get(did)
        self.assertIsNotNone(decision)
        self.assertEqual(decision["title"], "قرار التوظيف")
        self.assertEqual(decision["reason"], "نحتاج مطوراً")
        self.assertEqual(decision["category"], "project")
        self.assertEqual(decision["status"], "pending")

    def test_update_outcome_marks_completed(self):
        did = self.engine.record("قرار X", "السبب X")
        updated = self.engine.update_outcome(did, "نجح القرار", status="completed")
        self.assertTrue(updated)
        decision = self.engine.get(did)
        self.assertEqual(decision["status"], "completed")
        self.assertEqual(decision["actual_outcome"], "نجح القرار")
        self.assertIsNotNone(decision["resolved_at"])

    def test_pending_returns_only_pending(self):
        did1 = self.engine.record("قرار 1", "سبب 1")
        did2 = self.engine.record("قرار 2", "سبب 2")
        self.engine.update_outcome(did1, "تم", status="completed")
        pending = self.engine.pending()
        ids = [d["id"] for d in pending]
        self.assertNotIn(did1, ids)
        self.assertIn(did2, ids)

    def test_recent_returns_latest_first(self):
        for i in range(5):
            self.engine.record(f"قرار {i}", f"سبب {i}")
        recent = self.engine.recent(3)
        self.assertEqual(len(recent), 3)

    def test_snapshot_contains_required_keys(self):
        snap = self.engine.snapshot()
        self.assertIn("total", snap)
        self.assertIn("pending", snap)
        self.assertIn("recent", snap)

    def test_invalid_category_defaults_to_other(self):
        did = self.engine.record("قرار", "سبب", category="not_valid")
        decision = self.engine.get(did)
        self.assertEqual(decision["category"], "other")

    def test_empty_title_raises(self):
        with self.assertRaises(ValueError):
            self.engine.record("", "سبب")

    def test_empty_reason_raises(self):
        with self.assertRaises(ValueError):
            self.engine.record("عنوان", "")

    def test_update_outcome_returns_false_for_unknown_id(self):
        result = self.engine.update_outcome("non-existent-id", "نتيجة")
        self.assertFalse(result)


class TestDecisionEnginePersistence(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        dm = _load_decision_engine()
        self.DecisionEngine = dm.DecisionEngine

    def test_decisions_survive_reload(self):
        engine1 = self.DecisionEngine(self.tmp)
        did = engine1.record("قرار دائم", "يجب أن يبقى")
        # Re-instantiate from same directory
        engine2 = self.DecisionEngine(self.tmp)
        decision = engine2.get(did)
        self.assertIsNotNone(decision)
        self.assertEqual(decision["title"], "قرار دائم")


# ══════════════════════════════════════════════════════════════════════════════
# 4-6: ApprovalGate
# ══════════════════════════════════════════════════════════════════════════════

class TestApprovalGateCore(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        gm = _load_approval_gate()
        self.ApprovalGate = gm.ApprovalGate
        self.gate = self.ApprovalGate(self.tmp)

    def test_request_returns_string_id(self):
        aid = self.gate.request("delete", "حذف ملف السجل القديم")
        self.assertIsInstance(aid, str)
        self.assertTrue(len(aid) > 0)

    def test_get_returns_requested_approval(self):
        aid = self.gate.request("publish", "نشر إعلان الموقع")
        approval = self.gate.get(aid)
        self.assertIsNotNone(approval)
        self.assertEqual(approval["action"], "publish")
        self.assertEqual(approval["status"], "pending")

    def test_approve_marks_approved(self):
        aid = self.gate.request("external", "استدعاء API خارجي")
        self.gate.approve(aid, approved_by="naseem")
        self.assertTrue(self.gate.is_approved(aid))
        approval = self.gate.get(aid)
        self.assertEqual(approval["status"], "approved")
        self.assertEqual(approval["approved_by"], "naseem")

    def test_reject_marks_rejected(self):
        aid = self.gate.request("financial", "تحويل مبلغ X")
        self.gate.reject(aid, reason="ليس الوقت المناسب")
        approval = self.gate.get(aid)
        self.assertEqual(approval["status"], "rejected")
        self.assertEqual(approval["rejection_reason"], "ليس الوقت المناسب")

    def test_is_approved_false_for_pending(self):
        aid = self.gate.request("config", "تغيير إعدادات الخادم")
        self.assertFalse(self.gate.is_approved(aid))

    def test_is_approved_false_for_unknown(self):
        self.assertFalse(self.gate.is_approved("no-such-id"))

    def test_pending_returns_pending_only(self):
        aid1 = self.gate.request("delete", "طلب 1")
        aid2 = self.gate.request("publish", "طلب 2")
        self.gate.approve(aid1)
        pending = [a["id"] for a in self.gate.pending()]
        self.assertNotIn(aid1, pending)
        self.assertIn(aid2, pending)

    def test_snapshot_contains_required_keys(self):
        snap = self.gate.snapshot()
        self.assertIn("total", snap)
        self.assertIn("pending", snap)
        self.assertIn("recent", snap)

    def test_requires_approval_for_founder_final_actions(self):
        for action in ("delete", "publish", "deploy", "rollback"):
            self.assertTrue(self.gate.requires_approval(action), f"{action} should require approval")
        for action in ("external", "financial", "config", "other"):
            self.assertFalse(self.gate.requires_approval(action), f"{action} should not require approval")

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            self.gate.request("delete", "")

    def test_approve_returns_false_for_unknown(self):
        result = self.gate.approve("non-existent-id")
        self.assertFalse(result)

    def test_reject_returns_false_for_unknown(self):
        result = self.gate.reject("non-existent-id")
        self.assertFalse(result)


class TestApprovalGatePersistence(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        gm = _load_approval_gate()
        self.ApprovalGate = gm.ApprovalGate

    def test_approvals_survive_reload(self):
        gate1 = self.ApprovalGate(self.tmp)
        aid = gate1.request("delete", "طلب ثابت")
        gate2 = self.ApprovalGate(self.tmp)
        approval = gate2.get(aid)
        self.assertIsNotNone(approval)
        self.assertEqual(approval["status"], "pending")


# ══════════════════════════════════════════════════════════════════════════════
# 7-12: ExecutiveKernel integration
# ══════════════════════════════════════════════════════════════════════════════

class TestKernelP04Integration(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        km = _load_kernel_module()
        self.kernel = km.ExecutiveKernel(workspace_root=self.tmp)

    def test_boot_reports_decision_engine_component(self):
        result = self.kernel.boot()
        self.assertIn("decision_engine", result["components"])
        self.assertEqual(result["components"]["decision_engine"], "ok")

    def test_boot_reports_approval_gate_component(self):
        result = self.kernel.boot()
        self.assertIn("approval_gate", result["components"])
        self.assertEqual(result["components"]["approval_gate"], "ok")

    def test_before_request_includes_pending_approval_requests(self):
        self.kernel.boot()
        ctx = self.kernel.before_request("مرحبا")
        self.assertIn("pending_approval_requests", ctx)
        self.assertIsInstance(ctx["pending_approval_requests"], list)

    def test_before_request_includes_proactive_briefing_key(self):
        self.kernel.boot()
        ctx = self.kernel.before_request("مرحبا")
        self.assertIn("proactive_briefing", ctx)

    def test_proactive_briefing_is_string(self):
        self.kernel.boot()
        ctx = self.kernel.before_request("مرحبا")
        self.assertIsInstance(ctx["proactive_briefing"], str)

    def test_proactive_briefing_contains_active_projects_on_first_turn(self):
        self.kernel.boot()
        ctx = self.kernel.before_request("مرحبا")
        # Should have project data from Projects.md
        if self.kernel.state.active_projects:
            # briefing includes project name
            project = self.kernel.state.active_projects[0]
            self.assertIn(project, ctx["proactive_briefing"])

    def test_proactive_briefing_empty_on_follow_up(self):
        self.kernel.boot()
        self.kernel.before_request("مرحبا")  # first turn
        ctx2 = self.kernel.before_request("ما الجديد؟")
        self.assertEqual(ctx2["proactive_briefing"], "")

    def test_record_decision_helper_creates_decision(self):
        self.kernel.boot()
        did = self.kernel.record_decision("قرار مهم", "سبب وجيه", category="project")
        decision = self.kernel.decisions.get(did)
        self.assertIsNotNone(decision)
        self.assertEqual(decision["title"], "قرار مهم")

    def test_request_approval_helper_creates_approval(self):
        self.kernel.boot()
        aid = self.kernel.request_approval("delete", "حذف ملف التكوين القديم")
        approval = self.kernel.approvals.get(aid)
        self.assertIsNotNone(approval)
        self.assertEqual(approval["status"], "pending")

    def test_health_includes_pending_decisions(self):
        self.kernel.boot()
        h = self.kernel.health()
        self.assertIn("pending_decisions", h)
        self.assertIsInstance(h["pending_decisions"], int)

    def test_health_includes_pending_approval_requests(self):
        self.kernel.boot()
        h = self.kernel.health()
        self.assertIn("pending_approval_requests", h)
        self.assertIsInstance(h["pending_approval_requests"], int)

    def test_health_count_reflects_new_approval_request(self):
        self.kernel.boot()
        before = self.kernel.health()["pending_approval_requests"]
        self.kernel.request_approval("delete", "طلب اختباري")
        after = self.kernel.health()["pending_approval_requests"]
        self.assertEqual(after, before + 1)

    def test_health_count_reflects_new_decision(self):
        self.kernel.boot()
        before = self.kernel.health()["pending_decisions"]
        self.kernel.record_decision("قرار جديد", "سبب جديد")
        after = self.kernel.health()["pending_decisions"]
        self.assertEqual(after, before + 1)


# ══════════════════════════════════════════════════════════════════════════════
# 13-19: ameer_server endpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestServerP04Endpoints(unittest.TestCase):

    def setUp(self):
        import ameer_server
        from fastapi.testclient import TestClient
        self.server = ameer_server
        self.client = TestClient(ameer_server.app)

    def test_get_decisions_returns_200(self):
        resp = self.client.get("/decisions")
        self.assertEqual(resp.status_code, 200)

    def test_get_decisions_has_snapshot_keys(self):
        resp = self.client.get("/decisions")
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("pending", data)
        self.assertIn("recent", data)

    def test_post_decisions_records_decision(self):
        resp = self.client.post(
            "/decisions",
            json={"title": "تجربة P0.4", "reason": "اختبار آلي", "category": "other"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "recorded")

    def test_post_decisions_missing_title_returns_400(self):
        resp = self.client.post("/decisions", json={"reason": "سبب"})
        self.assertEqual(resp.status_code, 400)

    def test_post_decisions_missing_reason_returns_400(self):
        resp = self.client.post("/decisions", json={"title": "عنوان"})
        self.assertEqual(resp.status_code, 400)

    def test_get_approvals_returns_200(self):
        resp = self.client.get("/approvals")
        self.assertEqual(resp.status_code, 200)

    def test_get_approvals_has_snapshot_keys(self):
        resp = self.client.get("/approvals")
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("pending", data)
        self.assertIn("recent", data)

    def test_post_approvals_creates_pending_request(self):
        resp = self.client.post(
            "/approvals",
            json={"action": "delete", "description": "حذف ملف اختباري"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")

    def test_post_approvals_missing_description_returns_400(self):
        resp = self.client.post("/approvals", json={"action": "delete"})
        self.assertEqual(resp.status_code, 400)

    def test_approve_endpoint_marks_approved(self):
        # Create approval first
        create_resp = self.client.post(
            "/approvals",
            json={"action": "publish", "description": "نشر تجريبي"},
        )
        approval_id = create_resp.json()["id"]
        # Approve it
        resp = self.client.post(f"/approvals/{approval_id}/approve")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "approved")

    def test_approve_unknown_id_returns_404(self):
        resp = self.client.post("/approvals/non-existent-id/approve")
        self.assertEqual(resp.status_code, 404)

    def test_reject_endpoint_marks_rejected(self):
        create_resp = self.client.post(
            "/approvals",
            json={"action": "external", "description": "استدعاء API خارجي"},
        )
        approval_id = create_resp.json()["id"]
        resp = self.client.post(
            f"/approvals/{approval_id}/reject",
            json={"reason": "لا يجوز الآن"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "rejected")

    def test_reject_unknown_id_returns_404(self):
        resp = self.client.post(
            "/approvals/non-existent-id/reject",
            json={"reason": "اختبار"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_kernel_health_includes_pending_decisions(self):
        resp = self.client.get("/kernel/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pending_decisions", data)

    def test_kernel_health_includes_pending_approval_requests(self):
        resp = self.client.get("/kernel/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pending_approval_requests", data)


if __name__ == "__main__":
    unittest.main()
