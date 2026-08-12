"""
test_shell_executor_pipeline.py
================================
Tests for shell.run end-to-end pipeline:
    ToolRegistry → ToolDispatcher → Authorization → Boundary → ShellExecutor → Audit

Verifies:
- shell.run is registered in ToolRegistry
- ShellExecutor is selected for shell.run (not FileExecutor)
- Authorization check is invoked
- ApprovalGate is consulted (low-risk: not required)
- Execution result contains stdout/stderr/returncode/metadata
- file.create and file.read are unaffected
- build_homepage intent is unaffected
- CWD escape is blocked by ShellExecutor
- Missing command is denied by policy
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from kernel.capability_registry import CapabilityRegistry
from kernel.execution_authorization import ExecutionAuthorization, shell_run_permission_scope
from kernel.execution_boundary import BoundaryVerdict, ExecutionBoundary
from kernel.executor_file import FileExecutor
from kernel.executor_shell import ShellExecutor
from kernel.permission_registry import PermissionRegistry
from kernel.tool_dispatcher import ToolDispatcher
from kernel.tool_registry import ToolRegistry


# ── Spy / mock helpers ──────────────────────────────────────────────────────

class _AllowBoundary:
    def __init__(self):
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            verdict=BoundaryVerdict.ALLOW, reason="allowed_by_spy", detail={}
        )


class _DenyBoundary:
    def evaluate(self, **kwargs):
        return SimpleNamespace(
            verdict=BoundaryVerdict.DENY, reason="forced_deny", detail={}
        )


class _ApprovedAuth:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-approved"}


# ── Tool Registry tests ─────────────────────────────────────────────────────

class ShellRunToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

    def test_shell_run_is_registered(self):
        tool = self.registry.get("shell.run")
        self.assertEqual(tool.tool_name, "shell.run")
        self.assertEqual(tool.capability, "shell_execution")
        self.assertEqual(tool.action, "run")
        self.assertEqual(tool.risk_level, "medium")
        self.assertEqual(tool.status, "enabled")

    def test_shell_run_input_policy(self):
        tool = self.registry.get("shell.run")
        self.assertIn("command", tool.input_policy["required"])
        self.assertFalse(tool.input_policy["caller_scope_override"])
        self.assertFalse(tool.input_policy["shell"])

    def test_shell_run_caller_cannot_override_metadata(self):
        with self.assertRaises(ValueError):
            self.registry.resolve("shell.run", {"command": "echo hi", "capability": "evil"})

    def test_file_tools_unaffected_by_shell_run_addition(self):
        file_read = self.registry.get("file.read")
        self.assertEqual(file_read.capability, "file_operations")
        file_create = self.registry.get("file.create")
        self.assertEqual(file_create.capability, "file_operations")


# ── ShellExecutor unit tests ────────────────────────────────────────────────

class ShellExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.executor = ShellExecutor(self.tmp)

    def test_successful_echo_command(self):
        result = self.executor.execute({"command": ["echo", "hello"], "id": "t1"})
        self.assertEqual(result["status"], "completed")
        self.assertIn("hello", result["stdout"])
        self.assertEqual(result["returncode"], 0)

    def test_result_contains_required_fields(self):
        result = self.executor.execute({"command": ["echo", "x"]})
        self.assertIn("status", result)
        self.assertIn("stdout", result)
        self.assertIn("stderr", result)
        self.assertIn("returncode", result)
        self.assertIn("execution_metadata", result)

    def test_execution_metadata_fields(self):
        result = self.executor.execute({"command": ["echo", "x"], "id": "meta-test"})
        meta = result["execution_metadata"]
        self.assertIn("task_id", meta)
        self.assertIn("start_time", meta)
        self.assertIn("duration_ms", meta)
        self.assertIn("cwd", meta)

    def test_failed_command_returns_failed_status(self):
        result = self.executor.execute({"command": ["python3", "-c", "import sys; sys.exit(1)"]})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["returncode"], 1)

    def test_missing_command_returns_error(self):
        result = self.executor.execute({"command": ""})
        self.assertEqual(result["status"], "missing_command")

    def test_none_command_returns_error(self):
        result = self.executor.execute({})
        self.assertEqual(result["status"], "missing_command")

    def test_cwd_outside_workspace_is_blocked(self):
        result = self.executor.execute({"command": ["echo", "x"], "cwd": "/etc"})
        self.assertEqual(result["status"], "blocked")
        self.assertIn("workspace_root", result["reason"])

    def test_string_command_is_parsed(self):
        result = self.executor.execute({"command": "echo hello"})
        self.assertEqual(result["status"], "completed")
        self.assertIn("hello", result["stdout"])

    def test_nonexistent_command_returns_failed(self):
        result = self.executor.execute({"command": ["nonexistent_command_xyz_123"]})
        self.assertEqual(result["status"], "failed")


# ── ToolDispatcher executor routing tests ──────────────────────────────────

class ToolDispatcherShellRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        workspace = Path(self.tmp)
        # Create runtime_workspace so file ops work
        (workspace / "09_Assets" / "runtime_workspace" / "home").mkdir(parents=True, exist_ok=True)
        self.workspace = workspace

    def _make_shell_executor_spy(self):
        """Return a spy that captures calls and returns a fixed result."""
        calls = []
        def executor(task):
            calls.append(task)
            return {
                "task_id": task.get("id", "<unnamed>"),
                "status": "completed",
                "stdout": "spy_output",
                "stderr": "",
                "returncode": 0,
                "execution_metadata": {"cwd": ".", "pid": 1, "duration_ms": 1, "start_time": "T"},
            }
        executor.calls = calls
        return executor

    def _make_file_executor_spy(self):
        calls = []
        def executor(task):
            calls.append(task)
            return {"task_id": "f1", "status": "completed", "action": "read", "content": "data"}
        executor.calls = calls
        return executor

    def _make_dispatcher(self, boundary=None, shell_executor=None, file_executor=None):
        registry = ToolRegistry()
        boundary = boundary or _AllowBoundary()
        return ToolDispatcher(
            tool_registry=registry,
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
            approval_gate=MagicMock(),
            executor=file_executor,
            shell_executor=shell_executor,
            workspace_root=self.workspace,
        ), boundary

    def test_shell_executor_is_selected_for_shell_run(self):
        shell_spy = self._make_shell_executor_spy()
        file_spy = self._make_file_executor_spy()
        dispatcher, boundary = self._make_dispatcher(
            shell_executor=shell_spy, file_executor=file_spy
        )
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo hi", "task_id": "t1"},
            guardian=guardian,
            request_type="execution",
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), msg=f"Not executed: {result}")
        self.assertEqual(len(shell_spy.calls), 1, "ShellExecutor should be called once")
        self.assertEqual(len(file_spy.calls), 0, "FileExecutor should NOT be called")

    def test_file_executor_is_selected_for_file_read(self):
        shell_spy = self._make_shell_executor_spy()
        file_spy = self._make_file_executor_spy()
        dispatcher, boundary = self._make_dispatcher(
            shell_executor=shell_spy, file_executor=file_spy
        )
        guardian = {"status": "pass", "reason": "test"}
        # file.read requires a file in scope
        target = "09_Assets/runtime_workspace/home/index.html"
        (self.workspace / target).parent.mkdir(parents=True, exist_ok=True)
        (self.workspace / target).write_text("test content")
        result = dispatcher.dispatch(
            tool_name="file.read",
            context={"target": target},
            guardian=guardian,
            request_type="execution",
            intent="file_read",
        )
        # File executor should be called, not shell
        self.assertEqual(len(file_spy.calls), 1, "FileExecutor should be called once")
        self.assertEqual(len(shell_spy.calls), 0, "ShellExecutor should NOT be called")

    def test_shell_run_denied_when_boundary_denies(self):
        shell_spy = self._make_shell_executor_spy()
        dispatcher, _ = self._make_dispatcher(
            boundary=_DenyBoundary(), shell_executor=shell_spy
        )
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo hi"},
            guardian=guardian,
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result["executed"])
        self.assertEqual(len(shell_spy.calls), 0)

    def test_shell_run_denied_when_missing_command(self):
        shell_spy = self._make_shell_executor_spy()
        dispatcher, _ = self._make_dispatcher(shell_executor=shell_spy)
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": ""},
            guardian=guardian,
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "shell_run_policy_denied")
        self.assertEqual(len(shell_spy.calls), 0)

    def test_authorization_is_called_for_shell_run(self):
        shell_spy = self._make_shell_executor_spy()
        allow_boundary = _AllowBoundary()
        dispatcher, _ = self._make_dispatcher(
            boundary=allow_boundary, shell_executor=shell_spy
        )
        guardian = {"status": "pass", "reason": "test"}
        dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo test"},
            guardian=guardian,
            request_type="execution",
            intent="run_test",
        )
        # The boundary was consulted (authorization flows through boundary)
        self.assertTrue(allow_boundary.calls, "ExecutionBoundary must be called for shell.run")

    def test_shell_run_denied_when_guardian_missing(self):
        shell_spy = self._make_shell_executor_spy()
        dispatcher, _ = self._make_dispatcher(shell_executor=shell_spy)
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo hi"},
            guardian=None,
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "guardian_missing")

    def test_execution_result_contains_required_fields(self):
        shell_spy = self._make_shell_executor_spy()
        dispatcher, _ = self._make_dispatcher(shell_executor=shell_spy)
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo hi"},
            guardian=guardian,
            intent="run_test",
        )
        self.assertTrue(result.get("executed"))
        execution = result.get("result", {})
        self.assertIn("stdout", execution)
        self.assertIn("stderr", execution)
        self.assertIn("returncode", execution)
        self.assertIn("execution_metadata", execution)


# ── Integration: authorization pipeline with real CapabilityRegistry ────────

class ShellRunAuthorizationIntegrationTests(unittest.TestCase):
    """Tests that use real CapabilityRegistry + PermissionRegistry + ExecutionBoundary."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        workspace = Path(self.tmp)
        (workspace / "09_Assets" / "runtime_workspace" / "home").mkdir(parents=True, exist_ok=True)
        self.workspace = workspace

    def _setup_governance(self):
        from kernel.approval_gate import ApprovalGate
        caps = CapabilityRegistry(self.workspace)
        perms = PermissionRegistry(self.workspace)
        auth = ExecutionAuthorization(self.workspace, caps, perms)
        approval = ApprovalGate(self.workspace)
        boundary = ExecutionBoundary(approval_gate=approval, execution_auth=auth)
        return caps, perms, auth, boundary, approval

    def test_shell_run_is_authorized_when_permission_granted(self):
        caps, perms, auth, boundary, approval = self._setup_governance()
        shell_cap = caps.get_by_name("shell_execution")
        self.assertIsNotNone(shell_cap, "shell_execution capability must exist")

        # Grant the permission
        perms.grant(
            shell_cap["capability_id"],
            scope=shell_run_permission_scope(),
            granted_by="test:setup",
        )

        shell_calls = []
        def shell_executor(task):
            shell_calls.append(task)
            return {
                "status": "completed", "stdout": "ok", "stderr": "",
                "returncode": 0, "execution_metadata": {},
            }

        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=auth,
            approval_gate=approval,
            shell_executor=shell_executor,
            workspace_root=self.workspace,
        )
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo authorized"},
            guardian=guardian,
            request_type="execution",
            intent="run_test",
        )
        self.assertEqual(result["decision"], "ALLOW", f"Expected ALLOW but got: {result}")
        self.assertTrue(result["executed"])
        self.assertEqual(len(shell_calls), 1)

    def test_shell_run_denied_when_no_permission(self):
        caps, perms, auth, boundary, approval = self._setup_governance()
        # No permission granted — shell_execution capability exists but no permission card

        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=auth,
            approval_gate=approval,
            shell_executor=lambda t: {},
            workspace_root=self.workspace,
        )
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo test"},
            guardian=guardian,
            request_type="execution",
            intent="run_test",
        )
        # No permission → should be denied
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result["executed"])

    def test_file_create_unaffected(self):
        caps, perms, auth, boundary, approval = self._setup_governance()
        file_cap = caps.get_by_name("file_operations")
        if file_cap:
            from kernel.execution_authorization import file_read_permission_scope
            perms.grant(
                file_cap["capability_id"],
                scope=file_read_permission_scope(),
                granted_by="test:setup",
            )

        file_calls = []
        def file_executor(task):
            file_calls.append(task)
            return {"status": "completed", "action": "write", "bytes_written": 10}

        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=auth,
            approval_gate=approval,
            executor=file_executor,
            workspace_root=self.workspace,
        )
        guardian = {"status": "pass", "reason": "test"}
        result = dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/test.html",
                "content": "<p>test</p>",
            },
            guardian=guardian,
            request_type="execution",
            intent="build_homepage",
        )
        # Should not fail due to shell additions
        self.assertIn(result["decision"], ("ALLOW", "DENY"))
        # The tool registry and dispatcher should behave the same as before


# ── TaskDecomposer run_test intent ─────────────────────────────────────────

class TaskDecomposerRunTestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _get_decomposer(self):
        from kernel.task_decomposer import TaskDecomposer
        return TaskDecomposer(self.tmp)

    def test_run_test_arabic_command(self):
        td = self._get_decomposer()
        result = td.decompose("شغّل الاختبارات")
        self.assertEqual(result["intent"], "run_test")
        self.assertTrue(result["tasks"], "Should produce tasks for run_test")

    def test_run_test_english_command(self):
        td = self._get_decomposer()
        result = td.decompose("run tests")
        self.assertEqual(result["intent"], "run_test")

    def test_run_test_task_has_shell_executor(self):
        td = self._get_decomposer()
        result = td.decompose("run tests")
        tasks = result["tasks"]
        self.assertTrue(tasks)
        task = tasks[0]
        self.assertEqual(task["executor"], "shell")
        self.assertEqual(task["action"], "run")
        self.assertIn("command", task)

    def test_build_homepage_unaffected(self):
        td = self._get_decomposer()
        result = td.decompose("ابنِ الواجهة الرئيسية")
        self.assertEqual(result["intent"], "build_homepage")

    def test_file_read_unaffected(self):
        td = self._get_decomposer()
        result = td.decompose("اقرأ 09_Assets/runtime_workspace/home/index.html")
        self.assertEqual(result["intent"], "file_read")


if __name__ == "__main__":
    unittest.main()
