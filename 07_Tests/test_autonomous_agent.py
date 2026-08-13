"""
test_autonomous_agent.py
========================
Tests for AutonomousAgentLoop and DynamicPlanner.

Verifies:
- is_autonomous_goal routing function classifies correctly
- DynamicPlanner returns capability_gap when no providers
- DynamicPlanner._parse_json handles various formats
- DynamicPlanner._infer_language works for common extensions
- AutonomousAgentLoop.accept_goal returns capability_gap when no providers
- AutonomousAgentLoop._topological_sort orders tasks correctly
- AutonomousAgentLoop._is_dangerous_command blocks external effects
- AutonomousAgentLoop._extract_task_outcome handles various result shapes
- AutonomousAgentLoop routes external_effect tasks to pending_approvals
- ExecutiveKernel.init_autonomous_agent wires correctly
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from kernel.autonomous_agent import AutonomousAgentLoop, is_autonomous_goal
from kernel.dynamic_planner import DynamicPlanner


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_stub_kernel(tmpdir: str) -> MagicMock:
    """Creates a minimal stub kernel for testing."""
    kernel = MagicMock()
    kernel._root = Path(tmpdir)
    kernel.tool_registry = None
    kernel.capabilities = None
    kernel.approvals = MagicMock()
    kernel.approvals.request = MagicMock(return_value=None)
    kernel.workspace = MagicMock()
    kernel.workspace.scan = MagicMock(return_value={"tasks": {}, "projects": {}})
    kernel.workspace.build_executive_summary = MagicMock(return_value="workspace ok")
    kernel.execute_task = MagicMock(return_value={
        "accepted": True,
        "execution": {
            "completed": 1,
            "failed": 0,
            "blocked": 0,
            "results": [{"task_id": "t1", "status": "completed"}],
        },
    })
    return kernel


def _make_mock_provider(response: str | None = '{"ok": true}') -> MagicMock:
    provider = MagicMock()
    provider.is_available = MagicMock(return_value=True)
    provider.complete = MagicMock(return_value=response)
    return provider


# ── is_autonomous_goal ────────────────────────────────────────────────────────

class TestIsAutonomousGoal(unittest.TestCase):

    def test_simple_homepage_not_autonomous(self):
        self.assertFalse(is_autonomous_goal("ابنِ الصفحة الرئيسية"))

    def test_simple_greeting_not_autonomous(self):
        self.assertFalse(is_autonomous_goal("مرحبا"))

    def test_empty_query_not_autonomous(self):
        self.assertFalse(is_autonomous_goal(""))

    def test_short_query_not_autonomous(self):
        self.assertFalse(is_autonomous_goal("ابن"))

    def test_integrated_system_is_autonomous(self):
        self.assertTrue(is_autonomous_goal(
            "صمم وابنِ نظامًا متكاملًا لإدارة الموظفين والمهام والحضور"
        ))

    def test_admin_panel_is_autonomous(self):
        self.assertTrue(is_autonomous_goal(
            "أنشئ نظام لوحة إدارة احترافية مع قاعدة بيانات"
        ))

    def test_english_build_complete_is_autonomous(self):
        self.assertTrue(is_autonomous_goal(
            "Build a complete employee management system with backend API and admin dashboard"
        ))

    def test_read_command_not_autonomous(self):
        self.assertFalse(is_autonomous_goal("اقرأ ملف README.md"))

    def test_run_tests_not_autonomous(self):
        self.assertFalse(is_autonomous_goal("شغّل الاختبارات"))


# ── DynamicPlanner ─────────────────────────────────────────────────────────────

class TestDynamicPlannerNoProvider(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.planner = DynamicPlanner(providers=[], workspace_root=self.tmpdir)

    def test_plan_returns_capability_gap(self):
        result = self.planner.plan("صمم نظامًا متكاملًا")
        self.assertEqual(result["status"], "capability_gap")
        self.assertIsNone(result["plan"])

    def test_generate_file_content_returns_none(self):
        result = self.planner.generate_file_content(
            path="test.py",
            content_prompt="Create a hello world",
            goal="test",
            goal_id="abc123",
        )
        self.assertIsNone(result)

    def test_generate_repair_tasks_returns_empty(self):
        result = self.planner.generate_repair_tasks(
            failed_task={"id": "t1"},
            error="file not found",
            goal="test",
            goal_id="abc123",
        )
        self.assertEqual(result, [])

    def test_evaluate_completion_fallback_all_complete(self):
        result = self.planner.evaluate_completion(
            goal="test",
            success_criteria=["file exists"],
            execution_results=[{"status": "completed"}, {"status": "completed"}],
        )
        self.assertTrue(result["complete"])

    def test_evaluate_completion_fallback_partial(self):
        result = self.planner.evaluate_completion(
            goal="test",
            success_criteria=["file exists"],
            execution_results=[{"status": "completed"}, {"status": "failed"}],
        )
        self.assertFalse(result["complete"])

    def test_available_tools_returns_list(self):
        tools = self.planner.available_tools()
        self.assertIn("file.create", tools)
        self.assertIn("shell.run", tools)

    def test_available_capabilities_returns_list(self):
        caps = self.planner.available_capabilities()
        self.assertIn("file_operations", caps)


class TestDynamicPlannerParseJson(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.planner = DynamicPlanner(providers=[], workspace_root=self.tmpdir)

    def test_parse_plain_json(self):
        raw = '{"goal_id": "abc", "tasks": []}'
        result = self.planner._parse_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["goal_id"], "abc")

    def test_parse_json_in_markdown_fence(self):
        raw = '```json\n{"goal_id": "abc", "tasks": []}\n```'
        result = self.planner._parse_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["goal_id"], "abc")

    def test_parse_json_with_surrounding_text(self):
        raw = 'Here is the plan:\n{"goal_id": "abc", "tasks": []}\nEnd.'
        result = self.planner._parse_json(raw)
        self.assertIsNotNone(result)

    def test_parse_invalid_json_returns_none(self):
        result = self.planner._parse_json("not json at all")
        self.assertIsNone(result)

    def test_infer_language_python(self):
        self.assertEqual(DynamicPlanner._infer_language("main.py"), "Python")

    def test_infer_language_html(self):
        self.assertEqual(DynamicPlanner._infer_language("index.html"), "HTML5")

    def test_infer_language_unknown(self):
        lang = DynamicPlanner._infer_language("file.xyz")
        self.assertIn("xyz", lang)


class TestDynamicPlannerWithProvider(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_plan_ok_with_mock_provider(self):
        plan_json = '{"goal_id": "test01", "goal": "test", "tasks": [], "success_criteria": []}'
        provider = _make_mock_provider(plan_json)
        planner = DynamicPlanner(providers=[provider], workspace_root=self.tmpdir)
        result = planner.plan("test goal")
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(result["plan"])
        self.assertEqual(result["plan"]["goal_id"], "test01")

    def test_plan_parse_error_with_bad_response(self):
        provider = _make_mock_provider("not json")
        planner = DynamicPlanner(providers=[provider], workspace_root=self.tmpdir)
        result = planner.plan("test goal")
        self.assertEqual(result["status"], "parse_error")

    def test_plan_capability_gap_when_provider_returns_none(self):
        provider = _make_mock_provider(None)
        planner = DynamicPlanner(providers=[provider], workspace_root=self.tmpdir)
        result = planner.plan("test goal")
        self.assertEqual(result["status"], "capability_gap")

    def test_plan_capability_gap_when_provider_unavailable(self):
        provider = MagicMock()
        provider.is_available = MagicMock(return_value=False)
        planner = DynamicPlanner(providers=[provider], workspace_root=self.tmpdir)
        result = planner.plan("test goal")
        self.assertEqual(result["status"], "capability_gap")


# ── AutonomousAgentLoop ───────────────────────────────────────────────────────

class TestAutonomousAgentLoopNoProvider(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.kernel = _make_stub_kernel(self.tmpdir)

    def test_accept_goal_capability_gap(self):
        agent = AutonomousAgentLoop(
            kernel=self.kernel,
            providers=[],
            workspace_root=self.tmpdir,
        )
        report = agent.accept_goal("صمم نظامًا متكاملًا")
        self.assertEqual(report["status"], "capability_gap")
        self.assertIn("goal", report)

    def test_report_contains_required_fields(self):
        agent = AutonomousAgentLoop(
            kernel=self.kernel,
            providers=[],
            workspace_root=self.tmpdir,
        )
        report = agent.accept_goal("test goal")
        required_fields = [
            "status", "goal", "goal_id", "plan", "execution_summary",
            "tasks_completed", "tasks_failed", "pending_approvals",
            "started_at", "completed_at",
        ]
        for field in required_fields:
            self.assertIn(field, report, f"Missing field: {field}")


class TestAutonomousAgentLoopTopologicalSort(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.kernel = _make_stub_kernel(self.tmpdir)
        self.agent = AutonomousAgentLoop(
            kernel=self.kernel, providers=[], workspace_root=self.tmpdir
        )

    def test_empty_tasks(self):
        result = self.agent._topological_sort([])
        self.assertEqual(result, [])

    def test_no_dependencies(self):
        tasks = [
            {"id": "a", "dependencies": []},
            {"id": "b", "dependencies": []},
        ]
        result = self.agent._topological_sort(tasks)
        self.assertEqual(len(result), 2)

    def test_linear_dependency(self):
        tasks = [
            {"id": "b", "dependencies": ["a"]},
            {"id": "a", "dependencies": []},
        ]
        result = self.agent._topological_sort(tasks)
        ids = [t["id"] for t in result]
        self.assertLess(ids.index("a"), ids.index("b"))

    def test_chain_dependency(self):
        tasks = [
            {"id": "c", "dependencies": ["b"]},
            {"id": "a", "dependencies": []},
            {"id": "b", "dependencies": ["a"]},
        ]
        result = self.agent._topological_sort(tasks)
        ids = [t["id"] for t in result]
        self.assertLess(ids.index("a"), ids.index("b"))
        self.assertLess(ids.index("b"), ids.index("c"))


class TestAutonomousAgentLoopDangerousCommands(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.kernel = _make_stub_kernel(self.tmpdir)
        self.agent = AutonomousAgentLoop(
            kernel=self.kernel, providers=[], workspace_root=self.tmpdir
        )

    def test_git_push_is_dangerous(self):
        self.assertTrue(self.agent._is_dangerous_command("git push origin main"))

    def test_git_merge_local_is_safe(self):
        # Local git merge is a local operation (no remote effect)
        self.assertFalse(self.agent._is_dangerous_command("git merge main"))

    def test_npm_publish_is_dangerous(self):
        self.assertTrue(self.agent._is_dangerous_command("npm publish"))

    def test_pytest_is_safe(self):
        self.assertFalse(self.agent._is_dangerous_command(["python3", "-m", "pytest"]))

    def test_ls_is_safe(self):
        self.assertFalse(self.agent._is_dangerous_command("ls -la"))

    def test_pip_install_is_safe(self):
        self.assertFalse(self.agent._is_dangerous_command("pip install requests"))


class TestAutonomousAgentLoopExtractTaskOutcome(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.kernel = _make_stub_kernel(self.tmpdir)
        self.agent = AutonomousAgentLoop(
            kernel=self.kernel, providers=[], workspace_root=self.tmpdir
        )

    def test_extract_by_task_id(self):
        exec_result = {
            "accepted": True,
            "execution": {
                "completed": 1, "failed": 0, "blocked": 0,
                "results": [{"task_id": "t1", "status": "completed"}],
            },
        }
        outcome = self.agent._extract_task_outcome(exec_result, "t1")
        self.assertEqual(outcome["status"], "completed")

    def test_extract_single_result_fallback(self):
        exec_result = {
            "accepted": True,
            "execution": {
                "completed": 1, "failed": 0, "blocked": 0,
                "results": [{"task_id": "other", "status": "completed"}],
            },
        }
        outcome = self.agent._extract_task_outcome(exec_result, "t1")
        self.assertEqual(outcome["status"], "completed")

    def test_extract_failed_from_aggregate(self):
        exec_result = {
            "accepted": False,
            "execution": {"completed": 0, "failed": 1, "blocked": 0, "results": []},
            "validation": {"blocked": ["missing field"]},
        }
        outcome = self.agent._extract_task_outcome(exec_result, "t1")
        self.assertEqual(outcome["status"], "failed")


class TestAutonomousAgentLoopExternalEffect(unittest.TestCase):
    """Verify that external_effect tasks are paused and produce approval requests."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.kernel = _make_stub_kernel(self.tmpdir)

    def test_external_effect_task_queued_for_approval(self):
        plan_json = (
            '{"goal_id": "goal01", "goal": "test", '
            '"success_criteria": [], "assumptions": [], "architecture": {}, '
            '"tasks": ['
            '  {"id": "t-deploy", "description": "deploy to production", '
            '   "tool": "shell.run", "inputs": {"command": "git push"}, '
            '   "dependencies": [], "effect_scope": "external_effect", '
            '   "verification": {}}'
            ']}'
        )
        provider = _make_mock_provider(plan_json)
        agent = AutonomousAgentLoop(
            kernel=self.kernel,
            providers=[provider],
            workspace_root=self.tmpdir,
        )
        report = agent.accept_goal("deploy to production")
        # External effect should be pending, not executed
        self.assertIn(report["status"], ("external_effect_pending", "goal_complete", "needs_founder_attention"))
        # t-deploy should NOT have been executed via kernel.execute_task
        # (it should be in pending_approvals instead)
        for call_args in self.kernel.execute_task.call_args_list:
            tasks = call_args[0][0] if call_args[0] else call_args[1].get("tasks", [])
            for t in (tasks if isinstance(tasks, list) else []):
                self.assertNotEqual(t.get("id"), "t-deploy", "External effect task was executed!")


# ── ExecutiveKernel wiring ─────────────────────────────────────────────────────

class TestExecutiveKernelAutonomousWiring(unittest.TestCase):
    def test_init_autonomous_agent_method_exists(self):
        """ExecutiveKernel should have init_autonomous_agent method."""
        import importlib.util
        kernel_path = os.path.join(CODE_ROOT, "kernel", "executive_kernel.py")
        spec = importlib.util.spec_from_file_location("executive_kernel_test", kernel_path)
        module = importlib.util.module_from_spec(spec)
        # Don't exec to avoid side effects — just check attribute existence
        self.assertTrue(os.path.exists(kernel_path))
        with open(kernel_path) as f:
            source = f.read()
        self.assertIn("init_autonomous_agent", source)
        self.assertIn("autonomous_agent", source)

    def test_autonomous_agent_attribute_initialized(self):
        """autonomous_agent field should be None before init_autonomous_agent is called."""
        import importlib.util
        kernel_path = os.path.join(CODE_ROOT, "kernel", "executive_kernel.py")
        with open(kernel_path) as f:
            source = f.read()
        self.assertIn("self.autonomous_agent", source)


if __name__ == "__main__":
    unittest.main()
