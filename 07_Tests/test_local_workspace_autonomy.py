"""
test_local_workspace_autonomy.py
=================================
LOCAL WORKSPACE AUTONOMY / EXTERNAL EFFECT APPROVAL — behavioural tests.

Proves that Ameer operates with full autonomy inside runtime_workspace
and only requests Founder approval for operations with external effects.

Test matrix
-----------
A. "ابنِ موقع" (build_homepage)     → executes without repeated approvals
B. "أضف صندوق دردشة" (add_chat_box) → executes inside workspace automatically
C. "اختبر الموقع" (run_test/pytest)  → executes locally automatically
D. "انشر الموقع" (publish site)      → requires Founder approval (git push)
E. "git push" shell command           → requires Founder approval
F. "merge PR" (gh pr merge)          → requires Founder approval

Supporting tests
----------------
G. EffectScope.classify_effect_scope — local intents → LOCAL_WORKSPACE
H. EffectScope.classify_effect_scope — external intents → EXTERNAL_EFFECT
I. EffectScope.classify_effect_scope — shell commands classification
J. ApprovalGate NOT invoked for local workspace operations
K. Audit/Authorization logging still written for local ops (audit ≠ approval)
L. file.read inside runtime_workspace → auto-allowed
M. file.create inside runtime_workspace → auto-allowed
N. Multiple local steps in one plan → none require repeated approval
"""

from __future__ import annotations

import json
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

from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import (
    BoundaryVerdict,
    EffectScope,
    ExecutionBoundary,
    KERNEL_ACTIONABLE_INTENTS,
    _LOCAL_WORKSPACE_INTENTS,
    _EXTERNAL_EFFECT_INTENTS,
)
from kernel.tool_dispatcher import ToolDispatcher
from kernel.tool_registry import ToolRegistry


# ── Shared helpers ──────────────────────────────────────────────────────────

GUARDIAN_PASS = {"status": "pass", "reason": "autonomy_test"}


class _ApprovedAuth:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-local-auto"}


class _AllowBoundary:
    def evaluate(self, **kwargs):
        return SimpleNamespace(verdict=BoundaryVerdict.ALLOW, reason="test_allow", detail={})


def _make_shell_spy():
    calls = []

    def executor(task):
        calls.append(task)
        return {
            "status": "completed",
            "stdout": "ok",
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
    shell_executor=None,
    file_executor=None,
    boundary=None,
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


# ── Test A: "ابنِ موقع" — build_homepage executes locally without approval ──

class TestA_BuildHomepage(unittest.TestCase):
    """
    'ابنِ موقع' (build_homepage) must execute all local steps without
    requesting Founder approval at any point.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.gate = ApprovalGate(self.workspace)
        self.shell_spy = _make_shell_spy()
        self.file_spy = _make_file_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            shell_executor=self.shell_spy,
            file_executor=self.file_spy,
        )

    def test_build_homepage_executes_without_approval(self):
        """file.create for building a homepage must be auto-allowed."""
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/index.html",
                "content": "<html><body>Home</body></html>",
            },
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="build_homepage",
        )
        self.assertTrue(result.get("executed"), f"build_homepage must execute: {result}")
        self.assertEqual(result.get("decision"), "ALLOW")

    def test_build_homepage_no_pending_approvals_created(self):
        """Building the homepage must NOT create any pending approval requests."""
        self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/index.html",
                "content": "<html><body>Home</body></html>",
            },
            guardian=GUARDIAN_PASS,
            intent="build_homepage",
        )
        pending = self.gate.pending()
        self.assertEqual(len(pending), 0, "No pending approvals for local build")

    def test_multiple_local_build_steps_no_repeated_approval(self):
        """Multiple file operations for build_homepage must all execute without approval."""
        pages = ["index.html", "about.html", "contact.html"]
        for page in pages:
            result = self.dispatcher.dispatch(
                tool_name="file.create",
                context={
                    "target": f"09_Assets/runtime_workspace/home/{page}",
                    "content": f"<html>{page}</html>",
                },
                guardian=GUARDIAN_PASS,
                intent="build_homepage",
            )
            self.assertTrue(
                result.get("executed"),
                f"Step {page} must execute without approval: {result}",
            )
        # Still no pending approvals after all steps
        self.assertEqual(len(self.gate.pending()), 0)


# ── Test B: "أضف صندوق دردشة" — add_chat_box executes inside workspace ──────

class TestB_AddChatBox(unittest.TestCase):
    """
    'أضف صندوق دردشة' must execute local file operations
    inside runtime_workspace without requesting approval.
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

    def test_add_chat_box_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/chat.js",
                "content": "// chat widget",
            },
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="add_chat_box",
        )
        self.assertTrue(result.get("executed"), f"add_chat_box must auto-execute: {result}")
        self.assertEqual(result.get("decision"), "ALLOW")

    def test_add_chat_box_no_approvals_requested(self):
        self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/chat.js",
                "content": "// chat widget",
            },
            guardian=GUARDIAN_PASS,
            intent="add_chat_box",
        )
        self.assertEqual(len(self.gate.pending()), 0)

    def test_build_generic_intent_also_auto_allowed(self):
        """build_generic is the canonical intent for building inside workspace."""
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/chat.html",
                "content": "<div id='chat'></div>",
            },
            guardian=GUARDIAN_PASS,
            intent="build_generic",
        )
        self.assertTrue(result.get("executed"), f"build_generic must auto-execute: {result}")


# ── Test C: "اختبر الموقع" — run_test executes locally automatically ─────────

class TestC_TestWebsite(unittest.TestCase):
    """
    Local test commands (pytest, npm test) must execute without
    requesting Founder approval.
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

    def test_pytest_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "pytest tests/"},
            guardian=GUARDIAN_PASS,
            request_type="execution",
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"pytest must execute locally: {result}")
        self.assertEqual(len(self.gate.pending()), 0)

    def test_npm_test_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "npm test"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"npm test must execute locally: {result}")
        self.assertEqual(len(self.gate.pending()), 0)

    def test_python_local_script_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "python check_links.py"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"python script must execute locally: {result}")

    def test_git_status_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git status"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertTrue(result.get("executed"), f"git status must execute locally: {result}")

    def test_local_test_no_pending_approvals(self):
        """Running local tests must not create any pending approvals."""
        for cmd in ["pytest tests/", "npm test", "python -m pytest", "git status"]:
            self.dispatcher.dispatch(
                tool_name="shell.run",
                context={"command": cmd},
                guardian=GUARDIAN_PASS,
                intent="run_test",
            )
        self.assertEqual(len(self.gate.pending()), 0)


# ── Test D: "انشر الموقع" — publish site requires Founder approval ────────────

class TestD_PublishSiteRequiresApproval(unittest.TestCase):
    """
    Deploying/publishing the website (git push, railway up) must
    require Founder approval before execution.
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

    def test_publish_via_git_push_requires_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main"},
            guardian=GUARDIAN_PASS,
            intent="publish_site",
        )
        self.assertFalse(result.get("executed"), "publish must NOT execute without approval")
        self.assertEqual(len(self.shell_spy.calls), 0)

    def test_publish_via_git_push_returns_approval_required(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main"},
            guardian=GUARDIAN_PASS,
            intent="publish_site",
        )
        self.assertEqual(
            result.get("status"), "approval_required",
            f"Must return approval_required: {result}",
        )
        self.assertTrue(result.get("approval_required"))

    def test_railway_deploy_requires_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "railway up"},
            guardian=GUARDIAN_PASS,
            intent="deploy",
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")

    def test_publish_creates_approval_record(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main"},
            guardian=GUARDIAN_PASS,
            intent="publish_site",
        )
        approval_id = result.get("approval_id")
        self.assertIsNotNone(approval_id)
        pending = self.gate.pending()
        self.assertGreater(len(pending), 0, "Must have a pending approval record")

    def test_publish_after_approval_executes(self):
        """After Founder approves, git push must execute."""
        approval_id = self.gate.request(
            action="external",
            description="Founder approved: git push origin main",
            requested_by="test",
        )
        self.gate.approve(approval_id, approved_by="naseem")

        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main", "approval_id": approval_id},
            guardian=GUARDIAN_PASS,
            intent="publish_site",
        )
        self.assertTrue(result.get("executed"), f"Must execute after approval: {result}")


# ── Test E: "git push" requires approval ─────────────────────────────────────

class TestE_GitPushRequiresApproval(unittest.TestCase):
    """
    A raw 'git push' shell command must require Founder approval.
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

    def test_git_push_blocked_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")

    def test_git_push_origin_main_blocked(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main"},
            guardian=GUARDIAN_PASS,
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")

    def test_git_push_creates_pending_record(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git push origin main"},
            guardian=GUARDIAN_PASS,
        )
        self.assertGreater(len(self.gate.pending()), 0)

    def test_git_pull_also_requires_approval(self):
        """git pull also has external effects."""
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "git pull"},
            guardian=GUARDIAN_PASS,
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")


# ── Test F: "merge PR" requires approval ─────────────────────────────────────

class TestF_MergePRRequiresApproval(unittest.TestCase):
    """
    'gh pr merge' must require Founder approval.
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

    def test_gh_pr_merge_blocked_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "gh pr merge 42 --merge"},
            guardian=GUARDIAN_PASS,
        )
        self.assertFalse(result.get("executed"))
        self.assertEqual(result.get("status"), "approval_required")

    def test_gh_pr_merge_creates_pending_approval(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "gh pr merge 42"},
            guardian=GUARDIAN_PASS,
        )
        self.assertGreater(len(self.gate.pending()), 0)

    def test_gh_pr_merge_not_executed(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "gh pr merge 42"},
            guardian=GUARDIAN_PASS,
        )
        self.assertEqual(len(self.shell_spy.calls), 0, "Shell must NOT be called for gh pr merge")


# ── Test G: classify_effect_scope — local intents ────────────────────────────

class TestG_ClassifyLocalIntents(unittest.TestCase):
    """classify_effect_scope returns LOCAL_WORKSPACE for local intents."""

    def _scope(self, intent, action="write", context=None):
        return ExecutionBoundary.classify_effect_scope(
            intent=intent, action=action, context=context or {}
        )

    def test_build_homepage_is_local(self):
        self.assertEqual(self._scope("build_homepage"), EffectScope.LOCAL_WORKSPACE)

    def test_build_generic_is_local(self):
        self.assertEqual(self._scope("build_generic"), EffectScope.LOCAL_WORKSPACE)

    def test_create_website_is_local(self):
        self.assertEqual(self._scope("create_website"), EffectScope.LOCAL_WORKSPACE)

    def test_add_chat_box_is_local(self):
        self.assertEqual(self._scope("add_chat_box"), EffectScope.LOCAL_WORKSPACE)

    def test_run_test_is_local(self):
        self.assertEqual(self._scope("run_test"), EffectScope.LOCAL_WORKSPACE)

    def test_file_read_intent_is_local(self):
        self.assertEqual(self._scope("file_read"), EffectScope.LOCAL_WORKSPACE)

    def test_local_build_is_local(self):
        self.assertEqual(self._scope("local_build"), EffectScope.LOCAL_WORKSPACE)

    def test_local_test_is_local(self):
        self.assertEqual(self._scope("local_test"), EffectScope.LOCAL_WORKSPACE)

    def test_local_lint_is_local(self):
        self.assertEqual(self._scope("local_lint"), EffectScope.LOCAL_WORKSPACE)

    def test_local_format_is_local(self):
        self.assertEqual(self._scope("local_format"), EffectScope.LOCAL_WORKSPACE)


# ── Test H: classify_effect_scope — external intents ─────────────────────────

class TestH_ClassifyExternalIntents(unittest.TestCase):
    """classify_effect_scope returns EXTERNAL_EFFECT for external intents."""

    def _scope(self, intent, action="run", context=None):
        return ExecutionBoundary.classify_effect_scope(
            intent=intent, action=action, context=context or {}
        )

    def test_publish_site_is_external(self):
        self.assertEqual(self._scope("publish_site"), EffectScope.EXTERNAL_EFFECT)

    def test_deploy_is_external(self):
        self.assertEqual(self._scope("deploy"), EffectScope.EXTERNAL_EFFECT)

    def test_git_push_intent_is_external(self):
        self.assertEqual(self._scope("git_push"), EffectScope.EXTERNAL_EFFECT)

    def test_merge_pr_intent_is_external(self):
        self.assertEqual(self._scope("merge_pr"), EffectScope.EXTERNAL_EFFECT)

    def test_financial_operation_is_external(self):
        self.assertEqual(self._scope("financial_operation"), EffectScope.EXTERNAL_EFFECT)


# ── Test I: classify_effect_scope — shell command classification ──────────────

class TestI_ClassifyShellCommands(unittest.TestCase):
    """classify_effect_scope uses ShellExternalEffectClassifier for shell.run."""

    def _scope(self, command, intent="run_test"):
        return ExecutionBoundary.classify_effect_scope(
            intent=intent,
            action="run",
            context={"tool_name": "shell.run", "command": command},
        )

    # Local/safe commands
    def test_pytest_is_local(self):
        self.assertEqual(self._scope("pytest tests/"), EffectScope.LOCAL_WORKSPACE)

    def test_npm_test_is_local(self):
        self.assertEqual(self._scope("npm test"), EffectScope.LOCAL_WORKSPACE)

    def test_python_script_is_local(self):
        self.assertEqual(self._scope("python build.py"), EffectScope.LOCAL_WORKSPACE)

    def test_git_status_is_local(self):
        self.assertEqual(self._scope("git status"), EffectScope.LOCAL_WORKSPACE)

    def test_echo_is_local(self):
        self.assertEqual(self._scope("echo hello"), EffectScope.LOCAL_WORKSPACE)

    # External-effect commands
    def test_git_push_is_external(self):
        self.assertEqual(self._scope("git push origin main"), EffectScope.EXTERNAL_EFFECT)

    def test_curl_post_is_external(self):
        self.assertEqual(self._scope("curl -X POST https://api.example.com"), EffectScope.EXTERNAL_EFFECT)

    def test_railway_is_external(self):
        self.assertEqual(self._scope("railway up"), EffectScope.EXTERNAL_EFFECT)

    def test_gh_merge_is_external(self):
        self.assertEqual(self._scope("gh pr merge 42"), EffectScope.EXTERNAL_EFFECT)

    def test_npm_publish_is_external(self):
        self.assertEqual(self._scope("npm publish"), EffectScope.EXTERNAL_EFFECT)


# ── Test J: ApprovalGate NOT invoked for local workspace ops ─────────────────

class TestJ_ApprovalGateNotInvokedForLocal(unittest.TestCase):
    """
    ApprovalGate.request() must NOT be called for local workspace operations.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        self.mock_gate = MagicMock(spec=ApprovalGate)
        # Ensure is_approved returns True so if it's called by accident it passes
        self.mock_gate.is_approved.return_value = True
        self.shell_spy = _make_shell_spy()
        self.file_spy = _make_file_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.mock_gate,
            shell_executor=self.shell_spy,
            file_executor=self.file_spy,
        )

    def test_build_homepage_does_not_call_approval_gate_request(self):
        self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/index.html",
                "content": "<html></html>",
            },
            guardian=GUARDIAN_PASS,
            intent="build_homepage",
        )
        self.mock_gate.request.assert_not_called()

    def test_pytest_does_not_call_approval_gate_request(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "pytest tests/"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.mock_gate.request.assert_not_called()

    def test_npm_test_does_not_call_approval_gate_request(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "npm test"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        self.mock_gate.request.assert_not_called()

    def test_add_chat_box_does_not_call_approval_gate_request(self):
        self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/chat.js",
                "content": "// chat",
            },
            guardian=GUARDIAN_PASS,
            intent="add_chat_box",
        )
        self.mock_gate.request.assert_not_called()


# ── Test K: Audit logging still works for local ops (audit ≠ approval) ───────

class TestK_AuditLoggingPresent(unittest.TestCase):
    """
    Audit log must be written for shell.run even for local commands,
    but audit is NOT the same as approval — no pending approvals are created.
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

    def test_local_shell_writes_audit_record(self):
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "pytest tests/"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        audit_path = self.workspace / ".ameer" / "shell_audit.jsonl"
        self.assertTrue(audit_path.exists(), "shell_audit.jsonl must be written for local ops")
        records = [
            json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()
        ]
        self.assertTrue(records, "Audit file must contain at least one record")

    def test_audit_is_not_approval_for_local_ops(self):
        """Audit records exist but no pending approvals for local commands."""
        self.dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": "pytest tests/"},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        # Audit written
        audit_path = self.workspace / ".ameer" / "shell_audit.jsonl"
        self.assertTrue(audit_path.exists())
        # No pending approvals
        self.assertEqual(len(self.gate.pending()), 0, "Audit ≠ approval: no pending approvals for local ops")


# ── Test L: file.read inside runtime_workspace auto-allowed ──────────────────

class TestL_FileReadAutoAllowed(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = _make_workspace(self.tmp)
        # Create a readable file
        readable = self.workspace / "09_Assets" / "runtime_workspace" / "home" / "index.html"
        readable.write_text("<html></html>", encoding="utf-8")
        self.gate = ApprovalGate(self.workspace)
        self.file_spy = _make_file_spy()
        self.dispatcher = _make_dispatcher(
            workspace=self.workspace,
            approval_gate=self.gate,
            file_executor=self.file_spy,
        )

    def test_file_read_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="file.read",
            context={"target": "09_Assets/runtime_workspace/home/index.html"},
            guardian=GUARDIAN_PASS,
            intent="file_read",
        )
        self.assertTrue(result.get("executed"), f"file.read must auto-execute: {result}")
        self.assertEqual(result.get("decision"), "ALLOW")

    def test_file_read_no_pending_approvals(self):
        self.dispatcher.dispatch(
            tool_name="file.read",
            context={"target": "09_Assets/runtime_workspace/home/index.html"},
            guardian=GUARDIAN_PASS,
            intent="file_read",
        )
        self.assertEqual(len(self.gate.pending()), 0)


# ── Test M: file.create inside runtime_workspace auto-allowed ────────────────

class TestM_FileCreateAutoAllowed(unittest.TestCase):

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

    def test_file_create_executes_without_approval(self):
        result = self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/style.css",
                "content": "body { margin: 0; }",
            },
            guardian=GUARDIAN_PASS,
            intent="file_create",
        )
        self.assertTrue(result.get("executed"), f"file.create must auto-execute: {result}")

    def test_file_create_no_pending_approvals(self):
        self.dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": "09_Assets/runtime_workspace/home/style.css",
                "content": "body { margin: 0; }",
            },
            guardian=GUARDIAN_PASS,
            intent="file_create",
        )
        self.assertEqual(len(self.gate.pending()), 0)


# ── Test N: KERNEL_ACTIONABLE_INTENTS includes local workspace intents ────────

class TestN_KernelActionableIntents(unittest.TestCase):
    """All local workspace intents must be in KERNEL_ACTIONABLE_INTENTS."""

    def test_build_homepage_is_actionable(self):
        self.assertIn("build_homepage", KERNEL_ACTIONABLE_INTENTS)

    def test_build_generic_is_actionable(self):
        self.assertIn("build_generic", KERNEL_ACTIONABLE_INTENTS)

    def test_create_website_is_actionable(self):
        self.assertIn("create_website", KERNEL_ACTIONABLE_INTENTS)

    def test_add_chat_box_is_actionable(self):
        self.assertIn("add_chat_box", KERNEL_ACTIONABLE_INTENTS)

    def test_run_test_is_actionable(self):
        self.assertIn("run_test", KERNEL_ACTIONABLE_INTENTS)

    def test_file_read_is_actionable(self):
        self.assertIn("file_read", KERNEL_ACTIONABLE_INTENTS)

    def test_local_build_is_actionable(self):
        self.assertIn("local_build", KERNEL_ACTIONABLE_INTENTS)

    def test_local_test_is_actionable(self):
        self.assertIn("local_test", KERNEL_ACTIONABLE_INTENTS)

    def test_local_lint_is_actionable(self):
        self.assertIn("local_lint", KERNEL_ACTIONABLE_INTENTS)


if __name__ == "__main__":
    unittest.main()
