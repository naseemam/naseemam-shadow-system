"""
test_regression_external_effect_approval.py
=============================================
Regression tests for the external-effect / ApprovalGate enforcement fix.

These tests prove that shell.run CANNOT execute external-effect commands
without passing through the formal approval path, and that the audit trail
is always written.

Test matrix:
  Test 1 – shell.run + external effect + no approval   → blocked, approval_required, audit
  Test 2 – shell.run + external effect + approved       → executes successfully
  Test 3 – shell.run + safe local test command          → executes (existing policy)
  Test 4 – bypass attempts are all blocked
  Test 5 – file.create still works
  Test 6 – file.read still works
  Test 7 – build_homepage still works
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import BoundaryVerdict, ExecutionBoundary
from kernel.tool_dispatcher import ToolDispatcher
from kernel.tool_registry import ToolRegistry


# ── Shared helpers ──────────────────────────────────────────────────────────

class _AllowBoundary:
    def evaluate(self, **kwargs):
        return SimpleNamespace(verdict=BoundaryVerdict.ALLOW, reason="test_allow", detail={})


class _ApprovedAuth:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-approved"}


def _make_shell_spy():
    calls = []

    def executor(task):
        calls.append(task)
        return {
            "status": "completed",
            "stdout": "spy_stdout",
            "stderr": "",
            "returncode": 0,
            "execution_metadata": {"cwd": ".", "pid": 1, "duration_ms": 1, "start_time": "T"},
        }

    executor.calls = calls
    return executor


def _make_file_spy():
    calls = []

    def executor(task):
        calls.append(task)
        return {"status": "completed", "action": task.get("action", "write")}

    executor.calls = calls
    return executor


def _make_workspace(base: Path) -> Path:
    ws = base / "workspace"
    (ws / "09_Assets" / "runtime_workspace" / "home").mkdir(parents=True, exist_ok=True)
    (ws / ".ameer").mkdir(parents=True, exist_ok=True)
    return ws


def _make_dispatcher(
    workspace: Path,
    approval_gate=None,
    boundary=None,
    shell_executor=None,
    file_executor=None,
    auth=None,
):
    registry = ToolRegistry()
    return ToolDispatcher(
        tool_registry=registry,
        execution_boundary=boundary or _AllowBoundary(),
        execution_authorization=auth or _ApprovedAuth(),
        approval_gate=approval_gate,
        executor=file_executor,
        shell_executor=shell_executor,
        workspace_root=workspace,
    )


GUARDIAN_PASS = {"status": "pass", "reason": "regression_test"}


# ── Test 1: external-effect + no approval → blocked ─────────────────────────

class Test1ExternalEffectNoApproval(unittest.TestCase):
    """
    shell.run with external-effect command and no prior approval MUST:
    - NOT execute the command
    - Return status=approval_required
    - Create an approval record
    - Write an audit record
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.shell_spy = _make_shell_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            shell_executor=self.shell_spy,
        )

    def test_external_effect_command_blocked_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        # MUST NOT execute
        self.assertFalse(result.get("executed"), "Shell MUST NOT execute without approval")
        self.assertEqual(len(self.shell_spy.calls), 0, "ShellExecutor MUST NOT be called")

    def test_external_effect_returns_approval_required_status(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        self.assertEqual(result.get("status"), "approval_required",
                         f"Expected approval_required, got: {result}")
        self.assertTrue(result.get("approval_required"),
                        "approval_required flag must be True")

    def test_external_effect_creates_approval_record(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        approval_id = result.get("approval_id")
        self.assertIsNotNone(approval_id, "An approval_id must be returned")
        # Approval record must exist in the gate
        pending = self.gate.pending()
        pending_ids = [r["id"] for r in pending]
        self.assertIn(approval_id, pending_ids, "Approval record must exist in ApprovalGate")

    def test_external_effect_writes_audit_record(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        audit_path = self.workspace / ".ameer" / "shell_audit.jsonl"
        self.assertTrue(audit_path.exists(), "shell_audit.jsonl must be created")
        records = [json.loads(l) for l in audit_path.read_text().splitlines() if l.strip()]
        self.assertTrue(records, "Audit file must contain at least one record")
        last = records[-1]
        self.assertEqual(last["tool_name"], "shell.run")
        self.assertTrue(last["command_classification"]["is_external_effect"])
        self.assertTrue(last["approval_required"])
        self.assertEqual(last["executed"], False)

    def test_git_push_is_external_and_blocked(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")

    def test_railway_deploy_is_external_and_blocked(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "railway up"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")


# ── Test 2: external-effect + approved → executes ───────────────────────────

class Test2ExternalEffectApproved(unittest.TestCase):
    """
    shell.run with external-effect command AND a valid pre-approved approval_id
    MUST execute the command successfully.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.shell_spy = _make_shell_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            shell_executor=self.shell_spy,
        )

    def test_external_effect_executes_when_approved(self):
        # Create and approve an approval request
        approval_id = self.gate.request(
            action="external",
            description="pre-approved for regression test",
            requested_by="test",
            context={},
        )
        self.gate.approve(approval_id, approved_by="naseem")

        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com", "approval_id": approval_id},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"Should execute when approved: {result}")
        self.assertEqual(len(self.shell_spy.calls), 1)

    def test_audit_written_for_approved_execution(self):
        approval_id = self.gate.request(
            action="external",
            description="audit regression",
            requested_by="test",
            context={},
        )
        self.gate.approve(approval_id, approved_by="naseem")

        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com", "approval_id": approval_id},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        audit_path = self.workspace / ".ameer" / "shell_audit.jsonl"
        records = [json.loads(l) for l in audit_path.read_text().splitlines() if l.strip()]
        executed_records = [r for r in records if r.get("executed")]
        self.assertTrue(executed_records, "Audit must record successful execution")


# ── Test 3: safe local test command → executes ───────────────────────────────

class Test3SafeLocalCommand(unittest.TestCase):
    """
    shell.run with a safe local command (pytest, echo, ls) executes without
    needing an approval (per existing policy).
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.shell_spy = _make_shell_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            shell_executor=self.shell_spy,
        )

    def test_echo_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo hello"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"Safe local command must execute: {result}")
        self.assertEqual(len(self.shell_spy.calls), 1)

    def test_pytest_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "pytest --version"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"pytest must execute without approval: {result}")

    def test_git_status_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git status"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"git status must execute without approval: {result}")

    def test_audit_written_for_safe_command(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo audit_test"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        audit_path = self.workspace / ".ameer" / "shell_audit.jsonl"
        self.assertTrue(audit_path.exists())
        records = [json.loads(l) for l in audit_path.read_text().splitlines() if l.strip()]
        last = records[-1]
        self.assertFalse(last["command_classification"]["is_external_effect"])
        self.assertFalse(last["approval_required"])


# ── Test 4: bypass attempts are all blocked ──────────────────────────────────

class Test4BypassAttempts(unittest.TestCase):
    """
    All bypass routes must be blocked:
    - Injecting registry-owned fields (capability, action, risk_level) via context
    - Calling shell.run without guardian
    - Providing an invalid / unapproved approval_id for an external command
    - Providing a false approval_id for an external command
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.shell_spy = _make_shell_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            shell_executor=self.shell_spy,
        )

    def test_caller_cannot_override_capability_via_context(self):
        # Attempt to override capability to a safe capability
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={
                "command": "curl https://evil.com",
                "capability": "file_operations",
                "action": "read",
                "risk_level": "low",
            },
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        # Registry-owned fields are stripped; external-effect enforcement still applies
        self.assertFalse(result.get("executed"))

    def test_no_guardian_is_blocked(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com"},
            guardian=None,
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result.get("executed"))
        self.assertEqual(len(self.shell_spy.calls), 0)

    def test_missing_guardian_status_is_blocked(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "curl https://example.com"},
            guardian={"reason": "no_status_field"},
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result.get("executed"))

    def test_invalid_approval_id_for_external_command_blocked(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={
                "command": "curl https://example.com",
                "approval_id": "non-existent-id-12345",
            },
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        # Non-existent approval_id → not approved → must be blocked
        self.assertFalse(result.get("executed"))

    def test_pending_approval_id_does_not_allow_execution(self):
        # Create an approval but do NOT approve it
        approval_id = self.gate.request(
            action="external",
            description="pending test",
            requested_by="test",
            context={},
        )
        # Status is still pending
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={
                "command": "curl https://example.com",
                "approval_id": approval_id,
            },
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertFalse(result.get("executed"), "Pending approval must NOT allow execution")

    def test_rejected_approval_id_does_not_allow_execution(self):
        approval_id = self.gate.request(
            action="external",
            description="rejected test",
            requested_by="test",
            context={},
        )
        self.gate.reject(approval_id, rejected_by="naseem", reason="regression test")
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={
                "command": "curl https://example.com",
                "approval_id": approval_id,
            },
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertFalse(result.get("executed"), "Rejected approval must NOT allow execution")


# ── Test 5: file.create still works ─────────────────────────────────────────

class Test5FileCreateWorks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.file_spy = _make_file_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            file_executor=self.file_spy,
        )
        # Ensure the allowed scope directory exists
        target_dir = self.workspace / "09_Assets" / "runtime_workspace" / "home"
        target_dir.mkdir(parents=True, exist_ok=True)

    def test_file_create_executes_inside_scope(self):
        target = "09_Assets/runtime_workspace/home/test_output.txt"
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={"target": target, "content": "regression test"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="build_homepage",
        )
        self.assertTrue(
            result.get("executed") or result.get("decision") == "ALLOW",
            f"file.create must work inside scope: {result}",
        )

    def test_file_create_blocked_outside_scope(self):
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={"target": "/etc/passwd", "content": "hack"},
            guardian=GUARDIAN_PASS,
            intent="build_homepage",
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result.get("executed"))


# ── Test 6: file.read still works ────────────────────────────────────────────

class Test6FileReadWorks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.file_spy = _make_file_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            file_executor=self.file_spy,
        )

    def test_file_read_executes_inside_scope(self):
        # Create a readable file inside scope
        target = "09_Assets/runtime_workspace/home/readable.txt"
        (self.workspace / target).write_text("content")
        result = self.dispatcher.dispatch(
            tool_name="file.read",
            context={"target": target},
            guardian=GUARDIAN_PASS,
            intent="file_read",
        )
        self.assertTrue(
            result.get("executed") or result.get("decision") == "ALLOW",
            f"file.read must work inside scope: {result}",
        )

    def test_file_read_blocked_outside_scope(self):
        result = self.dispatcher.dispatch(
            tool_name="file.read",
            context={"target": "/etc/passwd"},
            guardian=GUARDIAN_PASS,
            intent="file_read",
        )
        self.assertEqual(result["decision"], "DENY")


# ── Test 7: build_homepage still works ───────────────────────────────────────

class Test7BuildHomepageWorks(unittest.TestCase):
    """
    build_homepage intent using file.create must work end-to-end.
    The approval enforcement for shell.run must not affect file.create.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.file_spy = _make_file_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            file_executor=self.file_spy,
        )

    def test_build_homepage_file_create_works(self):
        target = "09_Assets/runtime_workspace/home/index.html"
        (self.workspace / target).parent.mkdir(parents=True, exist_ok=True)
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={"target": target, "content": "<html></html>"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="build_homepage",
        )
        self.assertTrue(
            result.get("executed") or result.get("decision") == "ALLOW",
            f"build_homepage file.create must succeed: {result}",
        )

    def test_build_homepage_unaffected_by_shell_external_policy(self):
        """Shell policy changes must not regress build_homepage file.create."""
        # This test deliberately dispatches a shell.run (safe) alongside
        # a file.create — verifying neither is broken by the other.
        shell_spy = _make_shell_spy()
        dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            file_executor=self.file_spy,
            shell_executor=shell_spy,
        )
        target = "09_Assets/runtime_workspace/home/page.html"
        (self.workspace / target).parent.mkdir(parents=True, exist_ok=True)
        file_result = dispatcher.dispatch(
            tool_name="file.create",
            context={"target": target, "content": "<p>hi</p>"},
            guardian=GUARDIAN_PASS,
            intent="build_homepage",
        )
        shell_result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "echo build_done"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertTrue(
            file_result.get("executed") or file_result.get("decision") == "ALLOW",
            f"file.create must succeed: {file_result}",
        )
        self.assertTrue(shell_result.get("executed"), f"safe shell must execute: {shell_result}")


if __name__ == "__main__":
    unittest.main()
