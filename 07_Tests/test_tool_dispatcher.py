import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from kernel.capability_registry import CapabilityRegistry
from kernel.execution_authorization import ExecutionAuthorization
from kernel.execution_boundary import BoundaryVerdict, ExecutionBoundary
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


class ToolDispatcherTests(unittest.TestCase):
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
        boundary = _SpyBoundary()
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
        )

        dispatcher.dispatch(
            tool_name="file.read",
            guardian={"status": "pass"},
            context={"action": "write", "risk_level": "high", "capability": "x"},
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

        boundary = ExecutionBoundary(execution_auth=_DeniedAuth())
        dispatcher_denied = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=_DeniedAuth(),
        )
        result_denied = dispatcher_denied.dispatch(
            tool_name="file.read", guardian={"status": "pass"}
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

            result = dispatcher.dispatch(tool_name="file.read", guardian={"status": "pass"})
            self.assertEqual(result["decision"], "DENY")
            self.assertEqual(result["reason"], "execution_authorization_denied")

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
        executor = Mock()
        boundary = _SpyBoundary(verdict=BoundaryVerdict.DENY, reason="forced_deny")
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=boundary,
            execution_authorization=_ApprovedAuth(),
            executor=executor,
        )
        result = dispatcher.dispatch(tool_name="file.read", guardian={"status": "pass"})
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
        dispatcher = ToolDispatcher(
            tool_registry=ToolRegistry(),
            execution_boundary=_SpyBoundary(),
            execution_authorization=_ApprovedAuth(),
        )
        result = dispatcher.dispatch(
            tool_name="file.read",
            guardian={"status": "pass"},
            context={"capability": "external_network"},
        )
        self.assertEqual(result["execution_request"]["capability_name"], "file_operations")


if __name__ == "__main__":
    unittest.main()
