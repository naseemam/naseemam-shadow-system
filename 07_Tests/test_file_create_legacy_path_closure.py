"""
test_file_create_legacy_path_closure.py
=========================================
Regression tests that verify the legacy direct file.create path inside
ExecutiveBrain is closed and that all file creation is fail-closed.

Tests
-----
A. No direct FileExecutor import or instantiation in ExecutiveBrain source.
B. _create_file() returns 'blocked' with reason 'file_create_requires_tool_dispatcher'
   — no actual file is written.
C. _append_to_existing_file() returns 'blocked' with the same reason.
D. file.create via ToolDispatcher is DENY (permission not_granted).
E. Boundary cannot be bypassed via legacy path — _create_file never writes.
F. file.read through ToolDispatcher is unaffected (ALLOW when permission granted).
G. Conversational requests that reach _execute_with_plan produce only 'blocked'
   for file operations — not 'created'.
H. Dispatcher unavailable → DENY (fail-closed).
I. Registry unavailable → DENY (fail-closed).
J. Boundary unavailable → DENY (fail-closed).
K. Authorization unavailable → DENY (fail-closed).
L. Permission missing → DENY (fail-closed).
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# ── Path setup ────────────────────────────────────────────────────────────────

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

EXECUTIVE_BRAIN_PATH = os.path.join(CODE_ROOT, "executive_brain.py")


def _load(name: str, rel_path: str):
    path = os.path.join(CODE_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_executive_brain():
    """Load ExecutiveBrain with all external deps stubbed so no network calls are made."""
    # Stub heavy optional deps before importing
    for stub in ("openai", "anthropic"):
        if stub not in sys.modules:
            sys.modules[stub] = types.ModuleType(stub)

    # Patch adapters to avoid real network clients
    adapters_mod = types.ModuleType("adapters")
    adapters_mod.inference_provider = types.ModuleType("adapters.inference_provider")
    adapters_mod.inference_provider.OpenAIProvider = None
    adapters_mod.inference_provider.OllamaProvider = None
    sys.modules.setdefault("adapters", adapters_mod)
    sys.modules.setdefault("adapters.inference_provider", adapters_mod.inference_provider)

    from executive_brain import ExecutiveBrain
    return ExecutiveBrain()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestStaticAudit_A_NoDirectFileExecutorInExecutiveBrain(unittest.TestCase):
    """A. Static audit: ExecutiveBrain source must not import or call FileExecutor."""

    def _get_source(self) -> str:
        with open(EXECUTIVE_BRAIN_PATH, encoding="utf-8") as fh:
            return fh.read()

    def test_A1_no_import_of_executor_file(self):
        source = self._get_source()
        self.assertNotIn(
            "executor_file",
            source,
            "executive_brain.py must not import executor_file",
        )

    def test_A2_no_import_of_FileExecutor(self):
        source = self._get_source()
        self.assertNotIn(
            "FileExecutor",
            source,
            "executive_brain.py must not reference FileExecutor",
        )

    def test_A3_static_ast_no_fileexecutor_call(self):
        """AST walk: no Name node 'FileExecutor' in executive_brain.py."""
        with open(EXECUTIVE_BRAIN_PATH, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=EXECUTIVE_BRAIN_PATH)
        names = [
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        ]
        self.assertNotIn(
            "FileExecutor",
            names,
            "AST: executive_brain.py must not reference FileExecutor",
        )


class TestLegacyPathClosed_B_CreateFileBlocked(unittest.TestCase):
    """B. _create_file returns blocked — no actual file is written."""

    def setUp(self):
        self.brain = _make_executive_brain()

    def test_B1_returns_blocked_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.brain._create_file(
                "09_Assets/runtime_workspace/test.txt",
                "hello",
                workspace_root=tmp,
            )
        self.assertEqual(result["status"], "blocked")

    def test_B2_reason_is_tool_dispatcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.brain._create_file(
                "09_Assets/runtime_workspace/test.txt",
                "hello",
                workspace_root=tmp,
            )
        self.assertEqual(result["reason"], "file_create_requires_tool_dispatcher")

    def test_B3_no_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "09_Assets", "runtime_workspace", "test.txt")
            self.brain._create_file(
                "09_Assets/runtime_workspace/test.txt",
                "hello",
                workspace_root=tmp,
            )
            self.assertFalse(
                os.path.exists(target),
                "_create_file must not write any file to disk",
            )


class TestLegacyPathClosed_C_AppendFileBlocked(unittest.TestCase):
    """C. _append_to_existing_file returns blocked — no actual file is written."""

    def setUp(self):
        self.brain = _make_executive_brain()

    def test_C1_returns_blocked_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.brain._append_to_existing_file(
                "09_Assets/runtime_workspace/notes.txt",
                "extra content",
                workspace_root=tmp,
            )
        self.assertEqual(result["status"], "blocked")

    def test_C2_reason_is_tool_dispatcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.brain._append_to_existing_file(
                "09_Assets/runtime_workspace/notes.txt",
                "extra content",
                workspace_root=tmp,
            )
        self.assertEqual(result["reason"], "file_create_requires_tool_dispatcher")

    def test_C3_no_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "09_Assets", "runtime_workspace", "notes.txt")
            self.brain._append_to_existing_file(
                "09_Assets/runtime_workspace/notes.txt",
                "extra content",
                workspace_root=tmp,
            )
            self.assertFalse(
                os.path.exists(target),
                "_append_to_existing_file must not write any file to disk",
            )


class TestDispatcherPath_D_FileCreateDenyViaDispatcher(unittest.TestCase):
    """D. file.create through ToolDispatcher is DENY — permission not_granted."""

    def _make_dispatcher(self, tmp: str):
        from kernel.capability_registry import CapabilityRegistry
        from kernel.execution_authorization import ExecutionAuthorization
        from kernel.execution_boundary import ExecutionBoundary
        from kernel.executor_file import FileExecutor
        from kernel.permission_registry import PermissionRegistry
        from kernel.tool_dispatcher import ToolDispatcher
        from kernel.tool_registry import ToolRegistry

        cap_reg = CapabilityRegistry()
        perm_reg = PermissionRegistry()
        auth = ExecutionAuthorization(
            root=tmp,
            capability_registry=cap_reg,
            permission_registry=perm_reg,
        )
        executor = FileExecutor(workspace_root=tmp)
        boundary = ExecutionBoundary(
            execution_authorization=auth,
        )
        return ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=auth,
            executor=executor.execute,
            workspace_root=tmp,
        )

    def test_D1_file_create_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = self._make_dispatcher(tmp)
            result = dispatcher.dispatch(
                tool_name="file.create",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/out.txt", "content": "x"},
            )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result["allowed"])

    def test_D2_file_create_denied_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = self._make_dispatcher(tmp)
            result = dispatcher.dispatch(
                tool_name="file.create",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/out.txt", "content": "x"},
            )
        self.assertFalse(result.get("executed", False))

    def test_D3_file_create_no_file_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "09_Assets", "runtime_workspace", "out.txt")
            dispatcher = self._make_dispatcher(tmp)
            dispatcher.dispatch(
                tool_name="file.create",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/out.txt", "content": "x"},
            )
            self.assertFalse(os.path.exists(target))


class TestBoundaryBypass_E_LegacyPathCannotBypassBoundary(unittest.TestCase):
    """E. Legacy path (_create_file) cannot bypass Boundary — it never writes."""

    def setUp(self):
        self.brain = _make_executive_brain()

    def test_E1_create_file_always_blocked_regardless_of_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            for content in ["", "x" * 1000, "special\x00chars"]:
                result = self.brain._create_file(
                    "09_Assets/runtime_workspace/x.txt",
                    content,
                    workspace_root=tmp,
                )
                self.assertEqual(
                    result["status"],
                    "blocked",
                    f"Must be blocked for content={content!r[:20]}",
                )
                self.assertEqual(result["reason"], "file_create_requires_tool_dispatcher")

    def test_E2_append_always_blocked_regardless_of_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = [
                "09_Assets/runtime_workspace/a.txt",
                "09_Assets/runtime_workspace/sub/b.txt",
            ]
            for t in targets:
                result = self.brain._append_to_existing_file(t, "data", workspace_root=tmp)
                self.assertEqual(result["status"], "blocked")


class TestFileRead_F_FileReadUnaffected(unittest.TestCase):
    """F. file.read through ToolDispatcher is unaffected."""

    def test_F1_file_read_inside_workspace_allows(self):
        from kernel.capability_registry import CapabilityRegistry
        from kernel.execution_authorization import ExecutionAuthorization, file_read_permission_scope
        from kernel.execution_boundary import BoundaryVerdict, ExecutionBoundary
        from kernel.executor_file import FileExecutor
        from kernel.permission_registry import PermissionRegistry
        from kernel.tool_dispatcher import ToolDispatcher
        from kernel.tool_registry import ToolRegistry

        with tempfile.TemporaryDirectory() as tmp:
            runtime_ws = Path(tmp) / "09_Assets" / "runtime_workspace"
            runtime_ws.mkdir(parents=True)
            (runtime_ws / "data.txt").write_text("hello", encoding="utf-8")

            cap_reg = CapabilityRegistry()
            perm_reg = PermissionRegistry()
            perm_reg.grant(
                capability="file_operations",
                permission_scope=file_read_permission_scope(),
                granted_by="test",
            )
            auth = ExecutionAuthorization(
                root=tmp,
                capability_registry=cap_reg,
                permission_registry=perm_reg,
            )
            executor = FileExecutor(workspace_root=tmp)
            boundary = ExecutionBoundary(execution_authorization=auth)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=auth,
                executor=executor.execute,
                workspace_root=tmp,
            )

            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/data.txt"},
            )
            self.assertEqual(result["decision"], "ALLOW")
            self.assertTrue(result["executed"])
            self.assertEqual(result["result"]["content"], "hello")

    def test_F2_file_read_policy_unchanged(self):
        from kernel.execution_authorization import file_read_permission_scope
        scope = file_read_permission_scope()
        self.assertIn("file.read", scope)
        self.assertIn("read", scope)


class TestConversational_G_ConversationalDoesNotCreateFile(unittest.TestCase):
    """G. Conversational requests that enter _execute_with_plan produce blocked for files."""

    def setUp(self):
        self.brain = _make_executive_brain()

    def test_G1_create_file_never_returns_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.brain._create_file(
                "09_Assets/runtime_workspace/page.html",
                "<html></html>",
                workspace_root=tmp,
            )
        self.assertNotEqual(result.get("status"), "created")
        self.assertNotEqual(result.get("status"), "updated")

    def test_G2_append_file_never_returns_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.brain._append_to_existing_file(
                "09_Assets/runtime_workspace/page.html",
                "more content",
                workspace_root=tmp,
            )
        self.assertNotEqual(result.get("status"), "updated")
        self.assertNotEqual(result.get("status"), "created")


class TestFailClosed_H_DispatcherUnavailableDenies(unittest.TestCase):
    """H. Dispatcher unavailable → DENY."""

    def test_H1_no_dispatcher_create_file_returns_blocked(self):
        brain = _make_executive_brain()
        with tempfile.TemporaryDirectory() as tmp:
            result = brain._create_file("09_Assets/runtime_workspace/x.txt", "x", workspace_root=tmp)
        self.assertEqual(result["status"], "blocked")


class TestFailClosed_I_RegistryUnavailableDenies(unittest.TestCase):
    """I. Registry unavailable → DENY."""

    def test_I1_tool_registry_none_denies(self):
        from kernel.tool_dispatcher import ToolDispatcher
        dispatcher = ToolDispatcher(tool_registry=None)
        result = dispatcher.dispatch(tool_name="file.create", guardian={"status": "pass"})
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "tool_registry_unavailable")


class TestFailClosed_J_BoundaryUnavailableDenies(unittest.TestCase):
    """J. Boundary unavailable → DENY."""

    def test_J1_no_boundary_denies(self):
        from kernel.tool_dispatcher import ToolDispatcher
        from kernel.tool_registry import ToolRegistry
        from kernel.execution_authorization import ExecutionAuthorization, file_read_permission_scope
        from kernel.capability_registry import CapabilityRegistry
        from kernel.permission_registry import PermissionRegistry

        with tempfile.TemporaryDirectory() as tmp:
            cap_reg = CapabilityRegistry()
            perm_reg = PermissionRegistry()
            auth = ExecutionAuthorization(root=tmp, capability_registry=cap_reg, permission_registry=perm_reg)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=None,
                execution_authorization=auth,
            )
            result = dispatcher.dispatch(
                tool_name="file.create",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/x.txt", "content": "x"},
            )
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "execution_boundary_unavailable")


class TestFailClosed_K_AuthorizationUnavailableDenies(unittest.TestCase):
    """K. Authorization unavailable → DENY."""

    def test_K1_no_auth_denies(self):
        from kernel.tool_dispatcher import ToolDispatcher
        from kernel.tool_registry import ToolRegistry
        from kernel.execution_boundary import ExecutionBoundary

        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=ExecutionBoundary(execution_authorization=None),
            execution_authorization=None,
        )
        result = dispatcher.dispatch(
            tool_name="file.create",
            guardian={"status": "pass"},
            context={"target": "09_Assets/runtime_workspace/x.txt", "content": "x"},
        )
        self.assertEqual(result["decision"], "DENY")


class TestFailClosed_L_PermissionMissingDenies(unittest.TestCase):
    """L. Permission not_granted → DENY."""

    def test_L1_file_create_not_granted(self):
        from kernel.capability_registry import CapabilityRegistry
        from kernel.execution_authorization import ExecutionAuthorization
        from kernel.execution_boundary import ExecutionBoundary
        from kernel.executor_file import FileExecutor
        from kernel.permission_registry import PermissionRegistry
        from kernel.tool_dispatcher import ToolDispatcher
        from kernel.tool_registry import ToolRegistry

        with tempfile.TemporaryDirectory() as tmp:
            cap_reg = CapabilityRegistry()
            perm_reg = PermissionRegistry()
            # Deliberately do NOT grant file_operations for file.create
            auth = ExecutionAuthorization(
                root=tmp, capability_registry=cap_reg, permission_registry=perm_reg
            )
            boundary = ExecutionBoundary(execution_authorization=auth)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=auth,
                executor=FileExecutor(workspace_root=tmp).execute,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.create",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/out.txt", "content": "x"},
            )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result.get("executed", False))


if __name__ == "__main__":
    unittest.main()
