"""AEX-1 Agent-first acceptance tests."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_decomposer = _load("aex1_task_decomposer", ROOT / "06_Code/kernel/task_decomposer.py")
_boundary = _load("aex1_execution_boundary", ROOT / "06_Code/kernel/execution_boundary.py")


class TestAEX1IntentAcceptance(unittest.TestCase):
    def setUp(self):
        self.decomposer = _decomposer.TaskDecomposer(str(ROOT))

    def assert_execution_intent(self, command: str, intent: str):
        result = self.decomposer.decompose(command)
        self.assertEqual(result["intent"], intent)
        self.assertTrue(result["execution_intent"])
        self.assertGreater(result["task_count"], 0)
        for task in result["tasks"]:
            self.assertIn("permission_mode", task)
            self.assertIn("description", task)
        return result

    def test_ameer_review_repository(self):
        result = self.assert_execution_intent("أمير راجع المستودع", "repository_review")
        self.assertEqual(result["permission_mode"], "read_only")
        self.assertFalse(result["requires_approval"])

    def test_ameer_build_new_website(self):
        result = self.assert_execution_intent("أمير ابن موقع جديد عن منصة أمير", "build_website")
        self.assertEqual(result["permission_mode"], "tracked_write")
        self.assertTrue(all(task["action"] == "write" for task in result["tasks"]))

    def test_ameer_improve_user_interface(self):
        result = self.assert_execution_intent("تحسين واجهة المستخدم", "build_homepage")
        self.assertEqual(result["permission_mode"], "tracked_write")
        self.assertFalse(result["requires_approval"])
        self.assertTrue(all(task["action"] == "write" for task in result["tasks"]))

    def test_ameer_run_tests(self):
        result = self.assert_execution_intent("أمير شغل الاختبارات", "run_test")
        self.assertEqual(result["permission_mode"], "read_only")
        self.assertEqual(result["tasks"][0]["command"][:3], ["python3", "-m", "pytest"])

    def test_ameer_deploy_railway_requires_approval(self):
        result = self.assert_execution_intent("أمير انشر على Railway", "deploy_railway")
        self.assertEqual(result["permission_mode"], "external_approval")
        self.assertTrue(result["requires_approval"])
        self.assertEqual(result["tasks"][0]["target"], "railway/deploy")

    def test_additional_aex1_intents_are_mapped(self):
        expected = {
            "أمير عدل الكود": "code_edit",
            "أمير ابن متجر إلكتروني": "build_store",
            "أمير افتح فرع جديد": "open_branch",
            "أمير افتح طلب سحب": "open_pull_request",
        }
        for command, intent in expected.items():
            with self.subTest(command=command):
                self.assert_execution_intent(command, intent)


class TestAEX1KernelTrace(unittest.TestCase):
    def test_deploy_railway_returns_trace_and_pending_approval(self):
        code_root = str(ROOT / "06_Code")
        if code_root not in sys.path:
            sys.path.insert(0, code_root)
        from kernel.executive_kernel import ExecutiveKernel

        with tempfile.TemporaryDirectory() as temp_root:
            kernel = ExecutiveKernel(temp_root)
            trace = kernel.execute_command(
                "أمير انشر على Railway",
                guardian={"status": "pass"},
                request_type="execution",
                requested_by="aex1_acceptance",
            )
            self.assertTrue(trace.get("trace_id"))
            self.assertEqual(trace["final"]["intent"], "deploy_railway")
            self.assertFalse(trace["final"]["accepted"])
            self.assertEqual(trace["final"]["reason"], "explicit_approval_required")
            self.assertTrue(trace["final"].get("approval_id"))
            self.assertEqual(trace["pipeline"][-1]["name"], "ApprovalGate")


class TestAEX1PermissionMatrix(unittest.TestCase):
    def test_matrix_is_explicit_and_fail_closed_for_external_effects(self):
        self.assertEqual(_boundary.KERNEL_ACTIONABLE_INTENTS.__class__, set)
        self.assertIn("repository_review", _boundary.KERNEL_ACTIONABLE_INTENTS)
        self.assertIn("build_website", _boundary.KERNEL_ACTIONABLE_INTENTS)
        self.assertIn("deploy_railway", _boundary.KERNEL_ACTIONABLE_INTENTS)

        class Auth:
            def check(self, **kwargs):
                return {"status": "approved", "request_id": "auth-1"}

        class Approval:
            VALID_ACTIONS = {"publish", "external"}
            def recent(self, _limit):
                return []
            def pending(self):
                return []
            def request(self, **kwargs):
                return "approval-1"

        boundary = _boundary.ExecutionBoundary(approval_gate=Approval(), execution_auth=Auth())
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="deploy_railway",
            capability_name="engineering",
            action="publish",
        )
        self.assertEqual(result.verdict, _boundary.BoundaryVerdict.PENDING)
        self.assertEqual(result.reason, "approval_gate_created")


if __name__ == "__main__":
    unittest.main()
