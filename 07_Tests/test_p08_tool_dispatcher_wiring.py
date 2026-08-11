import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kernel.executive_kernel import ExecutiveKernel
from kernel.execution_boundary import BoundaryVerdict
from kernel.tool_dispatcher import ToolDispatcher
from kernel.tool_registry import ToolRegistry


class _StaticDecomposer:
    def __init__(self, intent, tasks):
        self._intent = intent
        self._tasks = list(tasks)

    def decompose(self, _command):
        return {
            "intent": self._intent,
            "task_count": len(self._tasks),
            "tasks": list(self._tasks),
        }


class _SpyDispatcher:
    def __init__(self, result):
        self.result = dict(result)
        self.calls = []

    def dispatch(self, **kwargs):
        self.calls.append(kwargs)
        return dict(self.result)


class _CaptureBoundary:
    def __init__(self, verdict=BoundaryVerdict.DENY, reason="forced_deny"):
        self.verdict = verdict
        self.reason = reason
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(verdict=self.verdict, reason=self.reason, detail={})


class _ApprovedAuth:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-approved"}


def _task(action="write"):
    return {
        "id": "home-index",
        "action": action,
        "executor": "file",
        "target": "09_Assets/runtime_workspace/home/index.html",
        "content": "<html></html>",
        "priority": "high",
    }


class ToolDispatcherWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.kernel = ExecutiveKernel(self.tmp)

    # A. ExecutiveBrain/Orchestrator -> Dispatcher (command execution path)
    def test_A_command_path_reaches_dispatcher(self):
        spy = _SpyDispatcher(
            {
                "decision": "DENY",
                "allowed": False,
                "reason": "forced_deny",
                "execution_request": {"tool_name": "file.create"},
                "boundary_result": None,
                "executed": False,
                "result": None,
            }
        )
        self.kernel.tool_dispatcher = spy
        self.kernel.task_decomposer = _StaticDecomposer("build_homepage", [_task("write")])

        trace = self.kernel.execute_command("ابنِ الصفحة", guardian={"status": "pass"})
        self.assertTrue(spy.calls)
        self.assertEqual(spy.calls[0]["tool_name"], "file.create")
        self.assertFalse(trace["final"]["accepted"])

    # B. Dispatcher -> Registry -> Boundary
    def test_B_dispatcher_calls_registry_and_boundary(self):
        real_registry = ToolRegistry()
        registry_spy = Mock(wraps=real_registry)
        boundary = _CaptureBoundary(verdict=BoundaryVerdict.DENY, reason="forced_deny")
        dispatcher = ToolDispatcher(
            tool_registry=registry_spy,
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
            approval_gate=self.kernel.approvals,
            executor=Mock(),
        )
        self.kernel.tool_dispatcher = dispatcher

        report = self.kernel.execute_task([_task("write")], guardian={"status": "pass"})
        self.assertFalse(report["accepted"])
        registry_spy.resolve.assert_called()
        self.assertTrue(boundary.calls)

    # C. direct executor bypass prevented
    def test_C_direct_executor_bypass_is_blocked(self):
        executor_mock = Mock(return_value={"status": "completed"})
        self.kernel.file_executor.execute = executor_mock
        self.kernel.tool_dispatcher = _SpyDispatcher(
            {
                "decision": "DENY",
                "allowed": False,
                "reason": "execution_authorization_denied",
                "execution_request": {"tool_name": "file.create"},
                "boundary_result": None,
                "executed": False,
                "result": None,
            }
        )

        report = self.kernel.execute_task([_task("write")], guardian={"status": "pass"})
        self.assertFalse(report["accepted"])
        executor_mock.assert_not_called()

    # D. missing Dispatcher -> DENY
    def test_D_missing_dispatcher_denies(self):
        self.kernel.tool_dispatcher = None
        report = self.kernel.execute_task([_task("write")], guardian={"status": "pass"})
        self.assertFalse(report["accepted"])
        self.assertEqual(report["execution"]["results"][0]["reason"], "tool_dispatcher_unavailable")

    # E. missing Registry -> DENY
    def test_E_missing_registry_denies(self):
        self.kernel.tool_dispatcher = ToolDispatcher(
            tool_registry=None,
            execution_boundary=self.kernel.execution_boundary,
            execution_authorization=self.kernel.execution_auth,
            approval_gate=self.kernel.approvals,
            executor=self.kernel.file_executor.execute,
        )
        report = self.kernel.execute_task([_task("write")], guardian={"status": "pass"})
        self.assertFalse(report["accepted"])
        self.assertEqual(report["execution"]["results"][0]["reason"], "tool_registry_unavailable")

    # F. missing Boundary -> DENY
    def test_F_missing_boundary_denies(self):
        self.kernel.tool_dispatcher = ToolDispatcher(
            tool_registry=self.kernel.tool_registry,
            execution_boundary=None,
            execution_authorization=self.kernel.execution_auth,
            approval_gate=self.kernel.approvals,
            executor=self.kernel.file_executor.execute,
        )
        report = self.kernel.execute_task([_task("write")], guardian={"status": "pass"})
        self.assertFalse(report["accepted"])
        self.assertEqual(report["execution"]["results"][0]["reason"], "execution_boundary_unavailable")

    # G. file.read without permission -> DENY
    def test_G_file_read_inside_runtime_scope_allows(self):
        runtime_home = Path(self.tmp, "09_Assets", "runtime_workspace", "home")
        runtime_home.mkdir(parents=True, exist_ok=True)
        (runtime_home / "index.html").write_text("<html></html>", encoding="utf-8")
        report = self.kernel.execute_task([_task("read")], guardian={"status": "pass"})
        self.assertTrue(report["accepted"])
        self.assertEqual(report["execution"]["results"][0]["status"], "completed")

    # H. file.create without permission -> DENY
    def test_H_file_create_without_permission_denies(self):
        report = self.kernel.execute_task([_task("write")], guardian={"status": "pass"})
        self.assertFalse(report["accepted"])
        self.assertEqual(report["execution"]["results"][0]["reason"], "execution_authorization_denied")

    # I. caller cannot override capability/action/risk
    def test_I_caller_cannot_override_registry_metadata(self):
        boundary = _CaptureBoundary(verdict=BoundaryVerdict.DENY, reason="forced_deny")
        self.kernel.tool_dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
            approval_gate=self.kernel.approvals,
            executor=Mock(),
        )
        task = _task("write")
        task["capability_name"] = "evil_cap"
        task["risk_level"] = "low"
        task["action"] = "write"

        self.kernel.execute_task([task], guardian={"status": "pass"})

        self.assertTrue(boundary.calls)
        call = boundary.calls[0]
        self.assertEqual(call["capability_name"], "file_operations")
        self.assertEqual(call["action"], "write")
        self.assertEqual(call["context"]["risk_level"], "medium")

    # J. conversational request does not reach executor
    def test_J_conversational_request_does_not_execute(self):
        executor_mock = Mock(return_value={"status": "completed"})
        self.kernel.file_executor.execute = executor_mock
        self.kernel.tool_dispatcher = ToolDispatcher(
            tool_registry=self.kernel.tool_registry,
            execution_boundary=self.kernel.execution_boundary,
            execution_authorization=self.kernel.execution_auth,
            approval_gate=self.kernel.approvals,
            executor=self.kernel.file_executor.execute,
        )
        self.kernel.task_decomposer = _StaticDecomposer("legacy_reply", [_task("write")])

        trace = self.kernel.execute_command(
            "سؤال",
            guardian={"status": "pass"},
            request_type="question",
            requested_by="test",
        )
        self.assertFalse(trace["final"]["accepted"])
        executor_mock.assert_not_called()

    # K. no external execution path bypasses dispatcher
    def test_K_no_external_bypass_patterns(self):
        kernel_path = Path(ROOT) / "06_Code" / "kernel" / "executive_kernel.py"
        server_path = Path(ROOT) / "ameer_server.py"
        brain_path = Path(ROOT) / "06_Code" / "executive_brain.py"
        orch_path = Path(ROOT) / "06_Code" / "reasoning_orchestrator.py"

        kernel_src = kernel_path.read_text(encoding="utf-8")
        server_src = server_path.read_text(encoding="utf-8")
        brain_src = brain_path.read_text(encoding="utf-8")
        orch_src = orch_path.read_text(encoding="utf-8")

        self.assertIn("_dispatch_task_tool(", kernel_src)
        self.assertNotIn("self.file_executor.execute(task)", kernel_src)
        self.assertNotIn("EXECUTION_BOUNDARY.evaluate(", server_src)
        self.assertNotIn("file_executor.execute(", server_src)
        self.assertNotIn("file_executor.execute(", brain_src)
        self.assertNotIn("file_executor.execute(", orch_src)


if __name__ == "__main__":
    unittest.main()
