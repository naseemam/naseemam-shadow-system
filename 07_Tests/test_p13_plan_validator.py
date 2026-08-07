"""
test_p13_plan_validator.py
==========================
P1.3 Plan Validator — comprehensive test suite.

Covers all five validation checks:
1.  Task completeness (action, executor, target are required)
2.  Dependency graph (unknown dep → blocked; cycle → blocked)
3.  Executor availability (only KNOWN_EXECUTORS are accepted)
4.  Permission compatibility (capability presence, approval flag)
5.  Sandbox safety (target must be inside runtime_workspace)

Plus:
6.  Structured output shape (valid / blocked / warnings / summary)
7.  Kernel.execute_task() enforces PlanValidator as the single gate
8.  A task batch that passes all checks produces valid=True
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)


# ── helpers ──────────────────────────────────────────────────────────────────

def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _validator_cls():
    mod = _load(
        "plan_validator",
        os.path.join(CODE_ROOT, "kernel", "plan_validator.py"),
    )
    return mod.PlanValidator, mod.KNOWN_EXECUTORS


def _make_workspace(tmp: str) -> None:
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    ws = Path(tmp, "09_Assets", "runtime_workspace")
    ws.mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory", "Founder.md").write_text("# Founder\nنسيم\n", encoding="utf-8")


def _make_valid_task(task_id: str = "t-1") -> Dict[str, Any]:
    """Minimal valid task that passes all five checks."""
    return {
        "id": task_id,
        "action": "write",
        "executor": "file",
        "target": "09_Assets/runtime_workspace/index.html",
        "content": "<h1>مرحبا</h1>",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Output shape
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputShape(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls, _ = _validator_cls()
        self.v = cls(self.tmp)

    def test_valid_result_has_all_keys(self):
        result = self.v.validate([_make_valid_task()])
        for key in ("valid", "blocked", "warnings", "summary"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_summary_has_required_fields(self):
        result = self.v.validate([_make_valid_task()])
        for key in ("tasks", "executors", "approval_required"):
            self.assertIn(key, result["summary"], f"Missing summary key: {key}")

    def test_summary_task_count_correct(self):
        tasks = [_make_valid_task("t-1"), _make_valid_task("t-2")]
        result = self.v.validate(tasks)
        self.assertEqual(result["summary"]["tasks"], 2)

    def test_summary_executors_list(self):
        result = self.v.validate([_make_valid_task()])
        self.assertIn("file", result["summary"]["executors"])

    def test_blocked_is_list(self):
        result = self.v.validate([_make_valid_task()])
        self.assertIsInstance(result["blocked"], list)

    def test_warnings_is_list(self):
        result = self.v.validate([_make_valid_task()])
        self.assertIsInstance(result["warnings"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Check 1: Task Completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskCompleteness(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls, _ = _validator_cls()
        self.v = cls(self.tmp)

    def test_missing_action_blocked(self):
        task = _make_valid_task()
        del task["action"]
        result = self.v.validate([task])
        self.assertFalse(result["valid"])
        self.assertTrue(any("action" in b for b in result["blocked"]))

    def test_missing_executor_blocked(self):
        task = _make_valid_task()
        del task["executor"]
        result = self.v.validate([task])
        self.assertFalse(result["valid"])
        self.assertTrue(any("executor" in b for b in result["blocked"]))

    def test_missing_target_blocked(self):
        task = _make_valid_task()
        del task["target"]
        result = self.v.validate([task])
        self.assertFalse(result["valid"])
        self.assertTrue(any("target" in b for b in result["blocked"]))

    def test_empty_action_blocked(self):
        task = _make_valid_task()
        task["action"] = ""
        result = self.v.validate([task])
        self.assertFalse(result["valid"])

    def test_complete_task_valid(self):
        result = self.v.validate([_make_valid_task()])
        self.assertTrue(result["valid"])

    def test_all_three_missing_produces_three_blocked_entries(self):
        task = {"id": "t-incomplete"}
        result = self.v.validate([task])
        missing_fields = [b for b in result["blocked"] if "missing required field" in b]
        self.assertEqual(len(missing_fields), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Check 2: Dependency Graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyGraph(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls, _ = _validator_cls()
        self.v = cls(self.tmp)

    def _t(self, tid: str, deps: list = None) -> Dict[str, Any]:
        task = _make_valid_task(tid)
        if deps:
            task["depends_on"] = deps
        return task

    def test_valid_dependency_chain_passes(self):
        tasks = [self._t("t-1"), self._t("t-2", ["t-1"])]
        result = self.v.validate(tasks)
        self.assertTrue(result["valid"])

    def test_unknown_dependency_blocked(self):
        tasks = [self._t("t-1", ["t-NONEXISTENT"])]
        result = self.v.validate(tasks)
        self.assertFalse(result["valid"])
        self.assertTrue(any("t-NONEXISTENT" in b for b in result["blocked"]))

    def test_cycle_two_nodes_blocked(self):
        tasks = [self._t("t-1", ["t-2"]), self._t("t-2", ["t-1"])]
        result = self.v.validate(tasks)
        self.assertFalse(result["valid"])
        self.assertTrue(any("cycle" in b.lower() for b in result["blocked"]))

    def test_cycle_three_nodes_blocked(self):
        tasks = [
            self._t("t-1", ["t-2"]),
            self._t("t-2", ["t-3"]),
            self._t("t-3", ["t-1"]),
        ]
        result = self.v.validate(tasks)
        self.assertFalse(result["valid"])
        self.assertTrue(any("cycle" in b.lower() for b in result["blocked"]))

    def test_no_deps_passes(self):
        tasks = [self._t("t-1"), self._t("t-2")]
        result = self.v.validate(tasks)
        self.assertTrue(result["valid"])


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Check 3: Executor Availability
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutorAvailability(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls, self.known = _validator_cls()
        self.v = cls(self.tmp)

    def test_known_executor_file_passes(self):
        result = self.v.validate([_make_valid_task()])
        self.assertTrue(result["valid"])

    def test_unknown_executor_blocked(self):
        task = _make_valid_task()
        task["executor"] = "browser"
        result = self.v.validate([task])
        self.assertFalse(result["valid"])
        self.assertTrue(any("browser" in b for b in result["blocked"]))

    def test_all_known_executors_pass(self):
        cls, known = _validator_cls()
        for executor in known:
            task = _make_valid_task()
            task["executor"] = executor
            # Use sandbox-safe target for all
            task["target"] = "09_Assets/runtime_workspace/test.txt"
            v = cls(self.tmp)
            result = v.validate([task])
            self.assertFalse(
                any(f"unknown executor '{executor}'" in b for b in result["blocked"]),
                f"Known executor '{executor}' was incorrectly blocked",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Check 4: Permission Compatibility
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermissionCompatibility(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)

    def _make_validator(self, cap_registry=None, perm_registry=None):
        cls, _ = _validator_cls()
        return cls(self.tmp, capability_registry=cap_registry,
                   permission_registry=perm_registry)

    def test_no_capability_field_passes(self):
        """Tasks without a capability field skip permission check."""
        task = _make_valid_task()
        v = self._make_validator()
        result = v.validate([task])
        self.assertTrue(result["valid"])

    def test_missing_capability_in_registry_blocked(self):
        cap_reg = MagicMock()
        cap_reg.get_by_name.return_value = None
        task = _make_valid_task()
        task["capability"] = "unknown_cap"
        v = self._make_validator(cap_registry=cap_reg)
        result = v.validate([task])
        self.assertFalse(result["valid"])
        self.assertTrue(any("not found" in b for b in result["blocked"]))

    def test_inactive_capability_blocked(self):
        cap_reg = MagicMock()
        cap_reg.get_by_name.return_value = {"id": "cap-1", "status": "suspended"}
        task = _make_valid_task()
        task["capability"] = "some_cap"
        v = self._make_validator(cap_registry=cap_reg)
        result = v.validate([task])
        self.assertFalse(result["valid"])

    def test_granted_capability_passes(self):
        cap_reg = MagicMock()
        cap_reg.get_by_name.return_value = {"id": "cap-1", "status": "core"}
        perm_reg = MagicMock()
        perm_reg.get_for_capability.return_value = {
            "permission_status": "granted",
            "enabled": True,
        }
        task = _make_valid_task()
        task["capability"] = "engineering"
        v = self._make_validator(cap_registry=cap_reg, perm_registry=perm_reg)
        result = v.validate([task])
        self.assertTrue(result["valid"])
        self.assertFalse(result["summary"]["approval_required"])

    def test_requires_approval_sets_warning_not_blocked(self):
        cap_reg = MagicMock()
        cap_reg.get_by_name.return_value = {"id": "cap-2", "status": "extended"}
        perm_reg = MagicMock()
        perm_reg.get_for_capability.return_value = {
            "permission_status": "requires_approval",
            "enabled": True,
        }
        task = _make_valid_task()
        task["capability"] = "github_management"
        v = self._make_validator(cap_registry=cap_reg, perm_registry=perm_reg)
        result = v.validate([task])
        # Not blocked — but approval_required and a warning
        self.assertTrue(result["valid"])
        self.assertTrue(result["summary"]["approval_required"])
        self.assertTrue(len(result["warnings"]) > 0)

    def test_not_granted_capability_blocked(self):
        cap_reg = MagicMock()
        cap_reg.get_by_name.return_value = {"id": "cap-3", "status": "extended"}
        perm_reg = MagicMock()
        perm_reg.get_for_capability.return_value = {
            "permission_status": "not_granted",
            "enabled": False,
        }
        task = _make_valid_task()
        task["capability"] = "financial_ops"
        v = self._make_validator(cap_registry=cap_reg, perm_registry=perm_reg)
        result = v.validate([task])
        self.assertFalse(result["valid"])


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Check 5: Sandbox Safety
# ═══════════════════════════════════════════════════════════════════════════════

class TestSandboxSafety(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls, _ = _validator_cls()
        self.v = cls(self.tmp)

    def test_target_inside_runtime_workspace_passes(self):
        task = _make_valid_task()
        task["target"] = "09_Assets/runtime_workspace/home/index.html"
        result = self.v.validate([task])
        self.assertTrue(result["valid"])

    def test_target_outside_runtime_workspace_blocked(self):
        task = _make_valid_task()
        task["target"] = "01_Docs/some_file.md"   # outside runtime_workspace
        result = self.v.validate([task])
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("runtime_workspace" in b for b in result["blocked"]),
            f"Expected 'runtime_workspace' in blocked. Got: {result['blocked']}",
        )

    def test_absolute_path_outside_blocked(self):
        task = _make_valid_task()
        task["target"] = "/etc/passwd"
        result = self.v.validate([task])
        self.assertFalse(result["valid"])

    def test_parent_traversal_blocked(self):
        task = _make_valid_task()
        task["target"] = "09_Assets/runtime_workspace/../../sensitive.md"
        result = self.v.validate([task])
        self.assertFalse(result["valid"])

    def test_non_path_target_ignored(self):
        """URL or DB identifier targets should not trigger sandbox check."""
        task = _make_valid_task()
        task["target"] = "memory://ameer-state"   # non-path target
        result = self.v.validate([task])
        # sandbox check skipped — valid
        self.assertTrue(result["valid"])

    def test_nested_path_inside_runtime_workspace_passes(self):
        task = _make_valid_task()
        task["target"] = "09_Assets/runtime_workspace/home/pages/about.html"
        result = self.v.validate([task])
        self.assertTrue(result["valid"])


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Full happy path
# ═══════════════════════════════════════════════════════════════════════════════

class TestHappyPath(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls, _ = _validator_cls()
        self.v = cls(self.tmp)

    def test_multi_task_batch_all_valid(self):
        tasks = [
            {
                "id": "t-1",
                "action": "write",
                "executor": "file",
                "target": "09_Assets/runtime_workspace/index.html",
            },
            {
                "id": "t-2",
                "action": "write",
                "executor": "file",
                "target": "09_Assets/runtime_workspace/style.css",
                "depends_on": ["t-1"],
            },
            {
                "id": "t-3",
                "action": "write",
                "executor": "file",
                "target": "09_Assets/runtime_workspace/app.js",
                "depends_on": ["t-1", "t-2"],
            },
        ]
        result = self.v.validate(tasks)
        self.assertTrue(result["valid"])
        self.assertEqual(result["summary"]["tasks"], 3)
        self.assertEqual(result["blocked"], [])

    def test_empty_task_list_valid(self):
        result = self.v.validate([])
        self.assertTrue(result["valid"])
        self.assertEqual(result["summary"]["tasks"], 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ExecutiveKernel.execute_task() enforces PlanValidator as single gate
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelGate(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        if CODE_ROOT not in sys.path:
            sys.path.insert(0, CODE_ROOT)
        kernel_mod = _load(
            "executive_kernel",
            os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"),
        )
        self.kernel = kernel_mod.ExecutiveKernel(workspace_root=self.tmp)

    def test_kernel_has_execute_task_method(self):
        self.assertTrue(
            hasattr(self.kernel, "execute_task"),
            "ExecutiveKernel must expose execute_task()",
        )

    def test_kernel_has_plan_validator(self):
        self.assertTrue(
            hasattr(self.kernel, "plan_validator"),
            "ExecutiveKernel must hold a PlanValidator instance",
        )

    def test_valid_tasks_accepted(self):
        tasks = [_make_valid_task()]
        result = self.kernel.execute_task(tasks)
        self.assertTrue(result["accepted"])
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["tasks_queued"], 1)

    def test_invalid_tasks_rejected(self):
        tasks = [{"id": "bad", "executor": "browser", "action": "", "target": ""}]
        result = self.kernel.execute_task(tasks)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["validation"]["valid"])
        self.assertEqual(result["tasks_queued"], 0)

    def test_blocked_tasks_not_queued_in_state(self):
        """Rejected tasks must NOT be added to running_tasks in state."""
        initial_count = len(self.kernel.state.running_tasks)
        tasks = [{"id": "rejected-task", "executor": "browser", "action": ""}]
        self.kernel.execute_task(tasks)
        self.assertEqual(len(self.kernel.state.running_tasks), initial_count)

    def test_accepted_tasks_are_persisted_in_state(self):
        """Accepted tasks remain persisted even after immediate execution."""
        self.kernel.execute_task([_make_valid_task("state-task-1")])
        stored = self.kernel.state.snapshot()["running_tasks"]
        self.assertTrue(any(task.get("id") == "state-task-1" for task in stored))

    def test_execute_task_result_shape(self):
        result = self.kernel.execute_task([_make_valid_task()])
        for key in ("accepted", "validation", "tasks_queued"):
            self.assertIn(key, result, f"Missing key in execute_task result: {key}")


if __name__ == "__main__":
    unittest.main()
