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

from kernel.capability_registry import CapabilityRegistry
from kernel.execution_authorization import ExecutionAuthorization, file_read_permission_scope
from kernel.execution_boundary import BoundaryVerdict, ExecutionBoundary
from kernel.executor_file import FileExecutor
from kernel.permission_registry import PermissionRegistry
from kernel.tool_dispatcher import ToolDispatcher
from kernel.tool_registry import ToolRegistry


class _SpyBoundary:
    def __init__(self, verdict=BoundaryVerdict.DENY, reason="forced_deny"):
        self.verdict = verdict
        self.reason = reason
        self.called = False
        self.last_kwargs = None

    def evaluate(self, **kwargs):
        self.called = True
        self.last_kwargs = kwargs
        return SimpleNamespace(verdict=self.verdict, reason=self.reason, detail={})


class _ApprovedAuth:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-approved"}


class _DeniedAuth:
    def check(self, **kwargs):
        return {"status": "denied", "request_id": "req-denied"}


class _TrackingAuth:
    def __init__(self, workspace_root, status="denied"):
        self._root = Path(workspace_root).resolve()
        self.status = status
        self.calls = []

    def check(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": self.status, "request_id": "req-tracked"}


class ToolDispatcherTests(unittest.TestCase):
    def _make_runtime_workspace(self, tmp):
        runtime_ws = Path(tmp, "09_Assets", "runtime_workspace", "home")
        runtime_ws.mkdir(parents=True, exist_ok=True)
        (runtime_ws / "index.html").write_text("<html></html>", encoding="utf-8")
        return "09_Assets/runtime_workspace/home/index.html"

    def test_A_tool_unregistered_denies(self):
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=_SpyBoundary(),
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(tool_name="file.delete", guardian={"status": "pass"})
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "tool_not_registered")

    def test_B_tool_registry_unavailable_denies(self):
        dispatcher = ToolDispatcher(
            tool_registry=None,
            execution_boundary=_SpyBoundary(),
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(tool_name="file.read", guardian={"status": "pass"})
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "tool_registry_unavailable")

    def test_C_metadata_cannot_be_overridden_by_caller(self):
        boundary = _SpyBoundary()
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
        )

        result = dispatcher.dispatch(
            tool_name="file.create",
            guardian={"status": "pass"},
            context={
                "capability": "evil_capability",
                "capability_name": "evil_capability",
                "action": "read",
                "risk_level": "low",
                "extra": "ok",
            },
        )

        self.assertEqual(result["execution_request"]["capability_name"], "file_operations")
        self.assertEqual(result["execution_request"]["action"], "write")
        self.assertEqual(result["execution_request"]["risk_level"], "medium")
        self.assertEqual(result["execution_request"]["context"], {"extra": "ok"})
        self.assertEqual(boundary.last_kwargs["capability_name"], "file_operations")
        self.assertEqual(boundary.last_kwargs["action"], "write")

    def test_D_capability_action_risk_come_from_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            boundary = _SpyBoundary()
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=_ApprovedAuth(),
                workspace_root=tmp,
            )

            dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={
                    "target": self._make_runtime_workspace(tmp),
                    "action": "write",
                    "risk_level": "high",
                    "capability": "x",
                },
            )

            self.assertEqual(boundary.last_kwargs["capability_name"], "file_operations")
            self.assertEqual(boundary.last_kwargs["action"], "read")
            self.assertEqual(boundary.last_kwargs["context"]["risk_level"], "low")

    def test_E_boundary_unavailable_denies(self):
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=None,
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(tool_name="file.read", guardian={"status": "pass"})
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "execution_boundary_unavailable")

    def test_F_guardian_missing_denies(self):
        boundary = _SpyBoundary(verdict=BoundaryVerdict.ALLOW, reason="execution_authorized")
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(tool_name="file.read", guardian=None)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "guardian_missing")
        self.assertFalse(boundary.called)

    def test_G_authorization_missing_or_denied_denies(self):
        dispatcher_missing = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=_SpyBoundary(),
            execution_authorization=None,
        )
        result_missing = dispatcher_missing.dispatch(
            tool_name="file.read", guardian={"status": "pass"}
        )
        self.assertEqual(result_missing["decision"], "DENY")
        self.assertEqual(result_missing["reason"], "execution_authorization_missing")

        with tempfile.TemporaryDirectory() as tmp:
            denied_auth = _TrackingAuth(tmp, status="denied")
            boundary = ExecutionBoundary(execution_auth=denied_auth)
            dispatcher_denied = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=denied_auth,
                workspace_root=tmp,
            )
            result_denied = dispatcher_denied.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": self._make_runtime_workspace(tmp)},
            )
            self.assertEqual(result_denied["decision"], "DENY")
            self.assertEqual(result_denied["reason"], "execution_authorization_denied")

    def test_H_file_read_without_permission_denies(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap_reg = CapabilityRegistry(tmp)
            perm_reg = PermissionRegistry(tmp)
            auth = ExecutionAuthorization(tmp, cap_reg, perm_reg)
            file_cap = cap_reg.get_by_name("file_operations")
            perm_reg.ensure(file_cap["capability_id"])

            boundary = ExecutionBoundary(execution_auth=auth)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=auth,
            )

            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": self._make_runtime_workspace(tmp)},
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "execution_authorization_denied")

    def test_H_file_read_inside_workspace_reaches_authorization_then_denies_not_granted(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._make_runtime_workspace(tmp)
            auth = _TrackingAuth(tmp, status="denied")
            boundary = ExecutionBoundary(execution_auth=auth)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=auth,
                workspace_root=tmp,
            )

            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": target},
            )

            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "execution_authorization_denied")
            self.assertEqual(len(auth.calls), 1)
            self.assertEqual(auth.calls[0]["context"]["target"], target)

    def test_H_file_read_inside_workspace_allows_and_executes_real_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._make_runtime_workspace(tmp)
            cap_reg = CapabilityRegistry(tmp)
            perm_reg = PermissionRegistry(tmp)
            file_cap = cap_reg.get_by_name("file_operations")
            perm_reg.grant(
                file_cap["capability_id"],
                scope=file_read_permission_scope(),
                granted_by="Naseem",
            )
            auth = ExecutionAuthorization(tmp, cap_reg, perm_reg)
            boundary = Mock(wraps=ExecutionBoundary(execution_auth=auth))
            registry = Mock(wraps=ToolRegistry())
            executor = Mock(wraps=FileExecutor(tmp).execute)
            dispatcher = ToolDispatcher(
                tool_registry=registry,
                execution_boundary=boundary,
                execution_authorization=auth,
                executor=executor,
                workspace_root=tmp,
            )

            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": target},
            )

            self.assertEqual(result["decision"], "ALLOW")
            self.assertTrue(result["executed"])
            self.assertEqual(result["result"]["status"], "completed")
            self.assertEqual(result["result"]["relative_path"], target)
            self.assertEqual(result["result"]["content"], "<html></html>")
            registry.resolve.assert_called_once()
            boundary.evaluate.assert_called_once()
            executor.assert_called_once()

    def test_I_file_create_without_permission_denies(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap_reg = CapabilityRegistry(tmp)
            perm_reg = PermissionRegistry(tmp)
            auth = ExecutionAuthorization(tmp, cap_reg, perm_reg)
            file_cap = cap_reg.get_by_name("file_operations")
            perm_reg.ensure(file_cap["capability_id"])

            boundary = ExecutionBoundary(execution_auth=auth)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=auth,
            )

            result = dispatcher.dispatch(tool_name="file.create", guardian={"status": "pass"})
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "execution_authorization_denied")

    def test_J_executor_not_called_on_deny(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = Mock()
            boundary = _SpyBoundary(verdict=BoundaryVerdict.DENY, reason="forced_deny")
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=_ApprovedAuth(),
                executor=executor,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": self._make_runtime_workspace(tmp)},
            )
            self.assertEqual(result["decision"], "DENY")
            executor.assert_not_called()

    def test_K_no_fallback_allows_execution(self):
        cases = (
            ToolDispatcher(tool_registry=None, execution_boundary=_SpyBoundary(), execution_authorization=_ApprovedAuth()),
            ToolDispatcher(tool_registry=ToolRegistry(), execution_boundary=None, execution_authorization=_ApprovedAuth()),
            ToolDispatcher(tool_registry=ToolRegistry(), execution_boundary=_SpyBoundary(), execution_authorization=None),
        )
        for dispatcher in cases:
            with self.subTest(dispatcher=dispatcher):
                result = dispatcher.dispatch(tool_name="file.read", guardian={"status": "pass"})
                self.assertEqual(result["decision"], "DENY")
                self.assertFalse(result["allowed"])

    def test_L_caller_cannot_downgrade_risk_medium_to_low(self):
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=_SpyBoundary(),
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(
            tool_name="file.create",
            guardian={"status": "pass"},
            context={"risk_level": "low"},
        )
        self.assertEqual(result["execution_request"]["risk_level"], "medium")

    def test_M_caller_cannot_change_action_write_to_read(self):
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=_SpyBoundary(),
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(
            tool_name="file.create",
            guardian={"status": "pass"},
            context={"action": "read"},
        )
        self.assertEqual(result["execution_request"]["action"], "write")

    def test_N_caller_cannot_change_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=_SpyBoundary(),
                execution_authorization=_ApprovedAuth(),
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={
                    "target": self._make_runtime_workspace(tmp),
                    "capability": "external_network",
                },
            )
            self.assertEqual(result["execution_request"]["capability_name"], "file_operations")

    def test_O_file_read_outside_workspace_denies_before_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = _TrackingAuth(tmp, status="approved")
            boundary = _SpyBoundary(verdict=BoundaryVerdict.ALLOW, reason="execution_authorized")
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=auth,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": "01_Docs/outside.md"},
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "file_read_scope_denied")
            self.assertFalse(boundary.called)
            self.assertEqual(auth.calls, [])

    def test_P_file_read_traversal_denies_before_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = _TrackingAuth(tmp, status="approved")
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=_SpyBoundary(verdict=BoundaryVerdict.ALLOW, reason="execution_authorized"),
                execution_authorization=auth,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/home/../../../../etc/passwd"},
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "file_read_scope_denied")
            self.assertEqual(auth.calls, [])

    def test_Q_file_read_absolute_outside_workspace_denies(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = _TrackingAuth(tmp, status="approved")
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=_SpyBoundary(verdict=BoundaryVerdict.ALLOW, reason="execution_authorized"),
                execution_authorization=auth,
                workspace_root=tmp,
            )
            outside = str(Path(tmp).parent / "absolute-outside.txt")
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": outside},
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "file_read_scope_denied")
            self.assertEqual(auth.calls, [])

    def test_R_file_read_scope_override_denies(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = _TrackingAuth(tmp, status="approved")
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=_SpyBoundary(verdict=BoundaryVerdict.ALLOW, reason="execution_authorized"),
                execution_authorization=auth,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={
                    "target": self._make_runtime_workspace(tmp),
                    "scope_root": "/tmp/override",
                },
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertIn(result["reason"], {"tool_policy_denied", "file_read_scope_override_denied"})
            self.assertEqual(auth.calls, [])

    def test_S_file_read_symlink_escape_denies(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_home = Path(tmp, "09_Assets", "runtime_workspace", "home")
            runtime_home.mkdir(parents=True, exist_ok=True)
            outside_dir = Path(tmp, "outside")
            outside_dir.mkdir()
            outside_target = outside_dir / "secret.txt"
            outside_target.write_text("secret", encoding="utf-8")
            link = runtime_home / "escape.txt"
            try:
                link.symlink_to(outside_target)
            except (NotImplementedError, OSError):
                self.skipTest("symlink creation not supported on this filesystem")

            auth = _TrackingAuth(tmp, status="approved")
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=_SpyBoundary(verdict=BoundaryVerdict.ALLOW, reason="execution_authorized"),
                execution_authorization=auth,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                context={"target": "09_Assets/runtime_workspace/home/escape.txt"},
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "file_read_scope_denied")
            self.assertEqual(auth.calls, [])

    def test_T_file_create_unaffected_by_file_read_scope_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap_reg = CapabilityRegistry(tmp)
            perm_reg = PermissionRegistry(tmp)
            file_cap = cap_reg.get_by_name("file_operations")
            perm_reg.grant(
                file_cap["capability_id"],
                scope=file_read_permission_scope(),
                granted_by="Naseem",
            )
            auth = ExecutionAuthorization(tmp, cap_reg, perm_reg)
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=ExecutionBoundary(execution_auth=auth),
                execution_authorization=auth,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.create",
                guardian={"status": "pass"},
                context={
                    "target": "/tmp/absolute-create-path-is-not-validated-here",
                    "content": "safe",
                },
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "execution_authorization_denied")

    def test_U_conversational_request_cannot_reach_file_read_executor(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = Mock(return_value={"status": "completed"})
            boundary = ExecutionBoundary(execution_auth=_ApprovedAuth())
            dispatcher = ToolDispatcher(
                tool_registry=ToolRegistry(),
                execution_boundary=boundary,
                execution_authorization=_ApprovedAuth(),
                executor=executor,
                workspace_root=tmp,
            )
            result = dispatcher.dispatch(
                tool_name="file.read",
                guardian={"status": "pass"},
                request_type="question",
                intent="chat",
                context={"target": self._make_runtime_workspace(tmp)},
            )
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "conversational_request_blocked")
            executor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
