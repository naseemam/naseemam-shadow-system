"""
test_p06_capability_governance.py
==================================
P0.6 Executive Capability Governance — acceptance tests.

Covers:
1.  CapabilityRegistry: core capabilities seeded on first load
2.  CapabilityRegistry: cannot register with status='core'
3.  CapabilityRegistry: register extended capability, retrieve by id and name
4.  CapabilityRegistry: input validation (empty name/description raise ValueError)
5.  CapabilityRegistry: invalid status raises ValueError
6.  CapabilityRegistry: transition lifecycle states
7.  CapabilityRegistry: cannot transition core capabilities
8.  CapabilityRegistry: conflict detection — duplicate name
9.  CapabilityRegistry: conflict detection — core identity override blocked
10. CapabilityRegistry: conflict detection — missing dependency
11. CapabilityRegistry: conflict detection — inactive dependency
12. CapabilityRegistry: registration blocked when conflict detected
13. CapabilityRegistry: persistence across reload
14. CapabilityRegistry: list_by_status and list_active
15. CapabilityRegistry: snapshot counts by status
16. PermissionRegistry: ensure creates not_granted card
17. PermissionRegistry: grant sets status and scope
18. PermissionRegistry: is_permitted returns True when granted
19. PermissionRegistry: is_permitted returns False when not_granted
20. PermissionRegistry: revoke resets to not_granted
21. PermissionRegistry: set_requires_approval
22. PermissionRegistry: disable / enable
23. PermissionRegistry: persistence across reload
24. PermissionRegistry: snapshot counts by status
25. ExecutionAuthorization: check denied when capability not registered
26. ExecutionAuthorization: check denied when capability suspended
27. ExecutionAuthorization: check denied when no permission card
28. ExecutionAuthorization: check denied when not_granted
29. ExecutionAuthorization: check pending when requires_approval
30. ExecutionAuthorization: check approved when granted
31. ExecutionAuthorization: authorize transitions pending to approved
32. ExecutionAuthorization: deny transitions pending to denied
33. ExecutionAuthorization: record_execution logs outcome
34. ExecutionAuthorization: persistence across reload
35. ExecutionAuthorization: pending_requests returns only pending
36. ExecutiveKernel: boot reports capability_registry + permission_registry + execution_authorization
37. ExecutiveKernel: before_request includes capability_governance + pending_execution_requests
38. ExecutiveKernel: health includes active_capabilities + pending_execution_requests
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")


# ── module loaders ────────────────────────────────────────────────────────────

def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _ensure_code_path():
    if CODE_ROOT not in sys.path:
        sys.path.insert(0, CODE_ROOT)


def _load_capability_registry():
    _ensure_code_path()
    return _load(
        "capability_registry",
        os.path.join(CODE_ROOT, "kernel", "capability_registry.py"),
    )


def _load_permission_registry():
    _ensure_code_path()
    return _load(
        "permission_registry",
        os.path.join(CODE_ROOT, "kernel", "permission_registry.py"),
    )


def _load_execution_authorization():
    _ensure_code_path()
    cap_mod = _load_capability_registry()
    perm_mod = _load_permission_registry()
    mod = _load(
        "execution_authorization",
        os.path.join(CODE_ROOT, "kernel", "execution_authorization.py"),
    )
    return mod, cap_mod, perm_mod


def _load_tool_registry():
    _ensure_code_path()
    return _load(
        "tool_registry",
        os.path.join(CODE_ROOT, "kernel", "tool_registry.py"),
    )


# ── CapabilityRegistry tests ──────────────────────────────────────────────────

class TestCapabilityRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        mod = _load_capability_registry()
        self.CapabilityRegistry = mod.CapabilityRegistry
        self.CapabilityConflictError = mod.CapabilityConflictError
        self.VALID_STATUSES = mod.VALID_STATUSES
        self.reg = self.CapabilityRegistry(self.tmp)

    # 1 — core capabilities seeded
    def test_core_capabilities_seeded(self):
        core_caps = self.reg.list_by_status("core")
        self.assertGreater(len(core_caps), 0)
        names = {c["name"] for c in core_caps}
        self.assertIn("engineering", names)
        self.assertIn("programming", names)
        self.assertIn("planning", names)
        self.assertIn("file_operations", names)

    # 2 — cannot register with status=core
    def test_cannot_register_with_core_status(self):
        with self.assertRaises(ValueError):
            self.reg.register(
                name="something",
                description="test",
                scope="test",
                approved_by="founder",
                status="core",
            )

    # 3 — register extended capability
    def test_register_extended_capability(self):
        cap_id = self.reg.register(
            name="github_management",
            description="Manage GitHub repos",
            scope="tooling",
            approved_by="Naseem",
            status="extended",
        )
        self.assertIsNotNone(cap_id)
        cap = self.reg.get(cap_id)
        self.assertEqual(cap["name"], "github_management")
        self.assertEqual(cap["status"], "extended")
        by_name = self.reg.get_by_name("github_management")
        self.assertEqual(by_name["capability_id"], cap_id)

    # 4 — empty name raises ValueError
    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.reg.register(
                name="",
                description="test",
                scope="test",
                approved_by="founder",
                status="experimental",
            )

    # 4b — empty description raises ValueError
    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            self.reg.register(
                name="valid_name",
                description="",
                scope="test",
                approved_by="founder",
                status="experimental",
            )

    # 5 — invalid status raises ValueError
    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            self.reg.register(
                name="test_cap",
                description="test",
                scope="test",
                approved_by="founder",
                status="invalid_status",
            )

    # 6 — transition lifecycle
    def test_transition_lifecycle(self):
        cap_id = self.reg.register(
            name="railway_deploy",
            description="Deploy on Railway",
            scope="infra",
            approved_by="Naseem",
            status="extended",
        )
        self.reg.transition(cap_id, "suspended", reason="audit")
        cap = self.reg.get(cap_id)
        self.assertEqual(cap["status"], "suspended")
        self.assertEqual(len(cap["history"]), 1)
        self.assertEqual(cap["history"][0]["from"], "extended")
        self.assertEqual(cap["history"][0]["to"], "suspended")

    # 7 — cannot transition core
    def test_cannot_transition_core(self):
        core_caps = self.reg.list_by_status("core")
        cap_id = core_caps[0]["capability_id"]
        with self.assertRaises(ValueError):
            self.reg.transition(cap_id, "suspended")

    # 8 — conflict: duplicate name
    def test_conflict_duplicate_name(self):
        self.reg.register(
            name="docker_ops",
            description="Docker operations",
            scope="infra",
            approved_by="Naseem",
            status="extended",
        )
        result = self.reg.check_conflicts("docker_ops")
        self.assertTrue(result["has_conflict"])
        types = [c["type"] for c in result["conflicts"]]
        self.assertIn("duplicate_name", types)

    # 9 — conflict: core identity override blocked
    def test_conflict_core_identity_override(self):
        result = self.reg.check_conflicts("engineering")
        self.assertTrue(result["has_conflict"])
        types = [c["type"] for c in result["conflicts"]]
        self.assertIn("core_identity_conflict", types)

    # 10 — conflict: missing dependency
    def test_conflict_missing_dependency(self):
        result = self.reg.check_conflicts("new_cap", dependencies=["nonexistent_dep"])
        self.assertTrue(result["has_conflict"])
        types = [c["type"] for c in result["conflicts"]]
        self.assertIn("missing_dependency", types)

    # 11 — conflict: inactive dependency
    def test_conflict_inactive_dependency(self):
        cap_id = self.reg.register(
            name="dep_cap",
            description="A dependency",
            scope="test",
            approved_by="founder",
            status="extended",
        )
        self.reg.transition(cap_id, "suspended")
        result = self.reg.check_conflicts("new_cap", dependencies=["dep_cap"])
        self.assertTrue(result["has_conflict"])
        types = [c["type"] for c in result["conflicts"]]
        self.assertIn("inactive_dependency", types)

    # 12 — registration blocked on conflict
    def test_registration_blocked_on_conflict(self):
        with self.assertRaises(self.CapabilityConflictError):
            self.reg.register(
                name="engineering",
                description="override core",
                scope="test",
                approved_by="founder",
                status="extended",
            )

    # 13 — persistence across reload
    def test_persistence_across_reload(self):
        cap_id = self.reg.register(
            name="cloudflare_dns",
            description="Manage Cloudflare DNS",
            scope="infra",
            approved_by="Naseem",
            status="extended",
        )
        reg2 = self.CapabilityRegistry(self.tmp)
        cap = reg2.get(cap_id)
        self.assertIsNotNone(cap)
        self.assertEqual(cap["name"], "cloudflare_dns")

    # 14 — list_active includes core, extended, experimental
    def test_list_active(self):
        self.reg.register(
            name="active_ext",
            description="Active extended",
            scope="test",
            approved_by="founder",
            status="extended",
        )
        active = self.reg.list_active()
        statuses = {c["status"] for c in active}
        self.assertIn("core", statuses)
        self.assertIn("extended", statuses)

    # 15 — snapshot counts
    def test_snapshot(self):
        snap = self.reg.snapshot()
        self.assertIn("total", snap)
        self.assertIn("by_status", snap)
        self.assertGreater(snap["by_status"]["core"], 0)


# ── PermissionRegistry tests ──────────────────────────────────────────────────

class TestPermissionRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        mod = _load_permission_registry()
        self.PermissionRegistry = mod.PermissionRegistry
        self.reg = self.PermissionRegistry(self.tmp)
        self.cap_id = "test-cap-uuid-001"

    # 16 — ensure creates not_granted
    def test_ensure_creates_not_granted(self):
        perm_id = self.reg.ensure(self.cap_id)
        card = self.reg.get_for_capability(self.cap_id)
        self.assertIsNotNone(card)
        self.assertEqual(card["permission_status"], "not_granted")
        self.assertTrue(card["owned"])
        self.assertTrue(card["enabled"])

    # 17 — grant sets status and scope
    def test_grant(self):
        self.reg.grant(self.cap_id, scope="read-only", granted_by="Naseem")
        card = self.reg.get_for_capability(self.cap_id)
        self.assertEqual(card["permission_status"], "granted")
        self.assertEqual(card["scope"], "read-only")
        self.assertEqual(card["granted_by"], "Naseem")

    # 18 — is_permitted True when granted
    def test_is_permitted_true(self):
        self.reg.grant(self.cap_id, scope="full", granted_by="Naseem")
        self.assertTrue(self.reg.is_permitted(self.cap_id))

    # 19 — is_permitted False when not_granted
    def test_is_permitted_false_not_granted(self):
        self.reg.ensure(self.cap_id)
        self.assertFalse(self.reg.is_permitted(self.cap_id))

    # 20 — revoke resets to not_granted
    def test_revoke(self):
        perm_id = self.reg.grant(self.cap_id, scope="full", granted_by="Naseem")
        self.reg.revoke(perm_id, reason="audit")
        card = self.reg.get_for_capability(self.cap_id)
        self.assertEqual(card["permission_status"], "not_granted")
        self.assertFalse(self.reg.is_permitted(self.cap_id))

    # 21 — requires_approval
    def test_set_requires_approval(self):
        self.reg.set_requires_approval(self.cap_id, scope="scoped")
        card = self.reg.get_for_capability(self.cap_id)
        self.assertEqual(card["permission_status"], "requires_approval")

    # 22 — disable / enable
    def test_disable_enable(self):
        self.reg.grant(self.cap_id, scope="full", granted_by="Naseem")
        self.reg.disable(self.cap_id)
        self.assertFalse(self.reg.is_permitted(self.cap_id))
        self.reg.enable(self.cap_id)
        self.assertTrue(self.reg.is_permitted(self.cap_id))

    # 23 — persistence across reload
    def test_persistence(self):
        self.reg.grant(self.cap_id, scope="full", granted_by="Naseem")
        reg2 = self.PermissionRegistry(self.tmp)
        self.assertTrue(reg2.is_permitted(self.cap_id))

    # 24 — snapshot
    def test_snapshot(self):
        self.reg.grant(self.cap_id, scope="full", granted_by="Naseem")
        snap = self.reg.snapshot()
        self.assertIn("total", snap)
        self.assertIn("by_status", snap)
        self.assertGreater(snap["by_status"]["granted"], 0)


# ── ExecutionAuthorization tests ──────────────────────────────────────────────

class TestExecutionAuthorization(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        mod, cap_mod, perm_mod = _load_execution_authorization()
        self.ExecutionAuthorization = mod.ExecutionAuthorization
        self.cap_reg = cap_mod.CapabilityRegistry(self.tmp)
        self.perm_reg = perm_mod.PermissionRegistry(self.tmp)
        self.auth = self.ExecutionAuthorization(self.tmp, self.cap_reg, self.perm_reg)

    def _register_extended(self, name="test_tool"):
        return self.cap_reg.register(
            name=name,
            description=f"{name} capability",
            scope="test",
            approved_by="founder",
            status="extended",
        )

    # 25 — denied when capability not registered
    def test_denied_not_registered(self):
        result = self.auth.check("nonexistent_cap", "some_action")
        self.assertEqual(result["status"], "denied")

    # 26 — denied when capability suspended
    def test_denied_suspended(self):
        cap_id = self._register_extended("suspended_cap")
        self.cap_reg.transition(cap_id, "suspended")
        result = self.auth.check("suspended_cap", "some_action")
        self.assertEqual(result["status"], "denied")

    # 27 — denied when no permission card
    def test_denied_no_permission_card(self):
        self._register_extended("cap_no_perm")
        result = self.auth.check("cap_no_perm", "some_action")
        self.assertEqual(result["status"], "denied")

    # 28 — denied when not_granted
    def test_denied_not_granted(self):
        cap_id = self._register_extended("cap_not_granted")
        self.perm_reg.ensure(cap_id)
        result = self.auth.check("cap_not_granted", "some_action")
        self.assertEqual(result["status"], "denied")

    # 29 — pending when requires_approval
    def test_pending_requires_approval(self):
        cap_id = self._register_extended("cap_req_approval")
        self.perm_reg.set_requires_approval(cap_id)
        result = self.auth.check("cap_req_approval", "some_action")
        self.assertEqual(result["status"], "pending")

    # 30 — approved when granted
    def test_approved_when_granted(self):
        cap_id = self._register_extended("cap_granted")
        self.perm_reg.grant(cap_id, scope="full", granted_by="Naseem")
        result = self.auth.check("cap_granted", "some_action")
        self.assertEqual(result["status"], "approved")

    # 31 — authorize transitions pending to approved
    def test_authorize_pending_to_approved(self):
        cap_id = self._register_extended("cap_pend_auth")
        self.perm_reg.set_requires_approval(cap_id)
        result = self.auth.check("cap_pend_auth", "action")
        self.assertEqual(result["status"], "pending")
        self.auth.authorize(result["request_id"], authorized_by="Naseem")
        req = self.auth.get_request(result["request_id"])
        self.assertEqual(req["status"], "approved")
        self.assertEqual(req["resolved_by"], "Naseem")

    # 32 — deny transitions pending to denied
    def test_deny_pending(self):
        cap_id = self._register_extended("cap_pend_deny")
        self.perm_reg.set_requires_approval(cap_id)
        result = self.auth.check("cap_pend_deny", "action")
        self.auth.deny(result["request_id"], denied_by="Naseem", reason="not now")
        req = self.auth.get_request(result["request_id"])
        self.assertEqual(req["status"], "denied")

    # 33 — record_execution logs outcome
    def test_record_execution(self):
        cap_id = self._register_extended("cap_exec_log")
        self.perm_reg.grant(cap_id, scope="full", granted_by="Naseem")
        result = self.auth.check("cap_exec_log", "deploy")
        self.assertEqual(result["status"], "approved")
        self.auth.record_execution(result["request_id"], outcome="success", detail="deployed v1.2")
        log = self.auth.execution_log()
        self.assertTrue(any(e["outcome"] == "success" for e in log))

    # 34 — persistence
    def test_persistence(self):
        cap_id = self._register_extended("cap_persist")
        self.perm_reg.set_requires_approval(cap_id)
        result = self.auth.check("cap_persist", "action")
        request_id = result["request_id"]
        mod, cap_mod, perm_mod = _load_execution_authorization()
        auth2 = mod.ExecutionAuthorization(self.tmp, self.cap_reg, self.perm_reg)
        req = auth2.get_request(request_id)
        self.assertIsNotNone(req)
        self.assertEqual(req["status"], "pending")

    # 35 — pending_requests returns only pending
    def test_pending_requests_only_pending(self):
        cap_id = self._register_extended("cap_multi")
        self.perm_reg.set_requires_approval(cap_id)
        r1 = self.auth.check("cap_multi", "action1")
        r2 = self.auth.check("cap_multi", "action2")
        self.auth.authorize(r1["request_id"])
        pending = self.auth.pending_requests()
        ids = [p["request_id"] for p in pending]
        self.assertNotIn(r1["request_id"], ids)
        self.assertIn(r2["request_id"], ids)


class TestFileOperationsContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        tool_mod = _load_tool_registry()
        auth_mod, cap_mod, perm_mod = _load_execution_authorization()
        self.tools = tool_mod.ToolRegistry()
        self.cap_reg = cap_mod.CapabilityRegistry(self.tmp)
        self.perm_reg = perm_mod.PermissionRegistry(self.tmp)
        self.auth = auth_mod.ExecutionAuthorization(self.tmp, self.cap_reg, self.perm_reg)

    def test_file_operations_capability_is_seeded(self):
        cap = self.cap_reg.get_by_name("file_operations")
        self.assertIsNotNone(cap)
        self.assertEqual(cap["status"], "core")

    def test_file_tools_contract_stays_not_granted_and_denied(self):
        read_tool = self.tools.get("file.read")
        create_tool = self.tools.get("file.create")

        self.assertEqual(read_tool.capability, "file_operations")
        self.assertEqual(read_tool.action, "read")
        self.assertEqual(create_tool.capability, "file_operations")
        self.assertEqual(create_tool.action, "write")

        cap = self.cap_reg.get_by_name("file_operations")
        self.perm_reg.ensure(cap["capability_id"])
        card = self.perm_reg.get_for_capability(cap["capability_id"])
        self.assertEqual(card["permission_status"], "not_granted")

        read_result = self.auth.check(
            capability_name=read_tool.capability,
            action=read_tool.action,
            context={"tool_name": read_tool.tool_name},
        )
        create_result = self.auth.check(
            capability_name=create_tool.capability,
            action=create_tool.action,
            context={"tool_name": create_tool.tool_name},
        )
        self.assertEqual(read_result["status"], "denied")
        self.assertEqual(create_result["status"], "denied")

    def test_file_read_scope_grant_approves_only_registry_owned_read(self):
        from kernel.execution_authorization import file_read_permission_scope

        read_tool = self.tools.get("file.read")
        cap = self.cap_reg.get_by_name("file_operations")
        self.perm_reg.grant(
            cap["capability_id"],
            scope=file_read_permission_scope(),
            granted_by="Naseem",
        )

        read_result = self.auth.check(
            capability_name=read_tool.capability,
            action=read_tool.action,
            context={
                "tool_name": read_tool.tool_name,
                "target": "09_Assets/runtime_workspace/home/index.html",
            },
        )
        create_result = self.auth.check(
            capability_name=read_tool.capability,
            action="write",
            context={
                "tool_name": "file.create",
                "target": "09_Assets/runtime_workspace/home/index.html",
            },
        )

        self.assertEqual(read_result["status"], "approved")
        self.assertEqual(create_result["status"], "denied")

    def test_file_read_scope_grant_fails_closed_without_registry_context(self):
        from kernel.execution_authorization import file_read_permission_scope

        cap = self.cap_reg.get_by_name("file_operations")
        self.perm_reg.grant(
            cap["capability_id"],
            scope=file_read_permission_scope(),
            granted_by="Naseem",
        )

        result = self.auth.check(
            capability_name="file_operations",
            action="read",
            context={"target": "01_Docs/outside.md"},
        )

        self.assertEqual(result["status"], "denied")


# ── ExecutiveKernel integration tests ─────────────────────────────────────────

class TestExecutiveKernelP06(unittest.TestCase):
    """
    Integration tests: verify that the three P0.6 components are wired
    into ExecutiveKernel's boot, before_request, and health paths.
    """

    def _make_kernel(self, tmp_dir: str):
        _ensure_code_path()
        from kernel.executive_kernel import ExecutiveKernel
        kernel = ExecutiveKernel(tmp_dir)
        # Patch all LLM/external touches to avoid network calls during tests
        with patch.object(kernel.founder, "load", return_value=None), \
             patch.object(kernel.workspace, "scan", return_value={}), \
             patch.object(kernel.workspace, "build_executive_summary", return_value=""):
            kernel.boot()
        return kernel

    # 36 — boot reports all three P0.6 components
    def test_boot_reports_p06_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = self._make_kernel(tmp)
            components = kernel._health
            self.assertIn("capability_registry", components)
            self.assertIn("permission_registry", components)
            self.assertIn("execution_authorization", components)
            self.assertEqual(components["capability_registry"], "ok")
            self.assertEqual(components["permission_registry"], "ok")
            self.assertEqual(components["execution_authorization"], "ok")

    # 37 — before_request includes capability_governance and pending_execution_requests
    def test_before_request_includes_capability_governance(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = self._make_kernel(tmp)
            ctx = kernel.before_request("test query")
            self.assertIn("capability_governance", ctx)
            self.assertIn("pending_execution_requests", ctx)
            snap = ctx["capability_governance"]
            self.assertIn("total", snap)
            self.assertIn("by_status", snap)

    # 38 — health includes active_capabilities and pending_execution_requests
    def test_health_includes_capability_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = self._make_kernel(tmp)
            h = kernel.health()
            self.assertIn("active_capabilities", h)
            self.assertIn("pending_execution_requests", h)
            self.assertIsInstance(h["active_capabilities"], dict)
            self.assertIsInstance(h["pending_execution_requests"], int)


if __name__ == "__main__":
    unittest.main()
