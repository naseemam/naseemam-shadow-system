from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import BoundaryVerdict
from kernel.tool_dispatcher import ToolDispatcher
from kernel.tool_registry import ToolRegistry


class _AllowBoundary:
    def evaluate(self, **kwargs):
        return SimpleNamespace(verdict=BoundaryVerdict.ALLOW, reason="test_allow", detail={})


class _ApprovedAuth:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-founder-policy"}


def _workspace(base: Path) -> Path:
    path = base / "workspace"
    (path / "09_Assets" / "runtime_workspace" / "home").mkdir(parents=True, exist_ok=True)
    (path / ".ameer").mkdir(parents=True, exist_ok=True)
    return path


def _shell_spy():
    calls = []

    def execute(task):
        calls.append(task)
        return {"status": "completed", "stdout": "ok", "stderr": "", "returncode": 0}

    execute.calls = calls
    return execute


def _dispatcher(workspace: Path, gate: ApprovalGate, shell):
    return ToolDispatcher(
        tool_registry=ToolRegistry(),
        execution_boundary=_AllowBoundary(),
        execution_authorization=_ApprovedAuth(),
        approval_gate=gate,
        shell_executor=shell,
        workspace_root=workspace,
    )


GUARDIAN_PASS = {"status": "pass", "reason": "founder_delegated_test"}


def test_delegated_external_commands_execute_without_founder_approval():
    workspace = _workspace(Path(tempfile.mkdtemp()))
    gate = ApprovalGate(workspace)
    shell = _shell_spy()
    dispatcher = _dispatcher(workspace, gate, shell)

    for command in ("curl https://example.com", "git push origin main", "gh pr merge 12 --squash"):
        result = dispatcher.dispatch(
            tool_name="shell.run",
            context={"command": command},
            guardian=GUARDIAN_PASS,
            intent="run_test",
        )
        assert result["executed"], (command, result)
        assert not result.get("approval_required", False)

    assert len(shell.calls) == 3


def test_publish_command_executes_under_ameer_delegation():
    workspace = _workspace(Path(tempfile.mkdtemp()))
    gate = ApprovalGate(workspace)
    shell = _shell_spy()
    dispatcher = _dispatcher(workspace, gate, shell)

    result = dispatcher.dispatch(
        tool_name="shell.run",
        context={"command": "railway up"},
        guardian=GUARDIAN_PASS,
        intent="deploy_railway",
    )
    assert result["executed"] is True
    assert not result.get("approval_required", False)
    assert not gate.pending()
    assert result["execution_request"]["context"]["external_effect_classification"]["command_root"] == "railway"


def test_delete_command_executes_under_ameer_delegation():
    workspace = _workspace(Path(tempfile.mkdtemp()))
    gate = ApprovalGate(workspace)
    shell = _shell_spy()
    dispatcher = _dispatcher(workspace, gate, shell)

    result = dispatcher.dispatch(
        tool_name="shell.run",
        context={"command": "rm old_file.txt"},
        guardian=GUARDIAN_PASS,
        intent="delete",
    )
    assert result["executed"] is True
    assert not result.get("approval_required", False)
    assert not gate.pending()
    assert result["execution_request"]["context"]["external_effect_classification"]["command_root"] == "rm"


def test_guardian_remains_required_for_all_commands():
    workspace = _workspace(Path(tempfile.mkdtemp()))
    gate = ApprovalGate(workspace)
    shell = _shell_spy()
    dispatcher = _dispatcher(workspace, gate, shell)

    result = dispatcher.dispatch(
        tool_name="shell.run",
        context={"command": "git push origin main"},
        guardian=None,
        intent="run_test",
    )
    assert result["decision"] == "DENY"
    assert not shell.calls


def test_shell_audit_retains_delegated_execution_evidence():
    workspace = _workspace(Path(tempfile.mkdtemp()))
    gate = ApprovalGate(workspace)
    shell = _shell_spy()
    dispatcher = _dispatcher(workspace, gate, shell)

    result = dispatcher.dispatch(
        tool_name="shell.run",
        context={"command": "git push origin main"},
        guardian=GUARDIAN_PASS,
        intent="run_test",
    )
    assert result["executed"]
    audit_path = workspace / ".ameer" / "shell_audit.jsonl"
    record = json.loads(audit_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["executed"] is True
    assert record["approval_required"] is False
