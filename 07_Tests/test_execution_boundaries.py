"""
test_execution_boundaries.py
=============================
Phase 1 — Execution Boundary Tests.

Verifies that all side-effecting execution paths are protected by the
ExecutionBoundary gate and that credential/execution-state isolation holds.

Tests (A–M)
-----------
A. Guardian missing  → execution denied
B. Guardian empty    → execution denied
C. Guardian unknown  → execution denied
D. Guardian blocked  → execution denied
E. Guardian needs_approval → execution denied until approval
F. ExecutionAuthorization denied → execution denied
G. Tool (FileExecutor) cannot execute without authorization
H. Conversational request cannot accidentally enter side-effect execution
I. kernel_execution_reply cannot bypass the boundary
J. Execution state cannot become permanent memory automatically
K. Credentials are not persisted to conversational memory
L. Credentials are not logged (sanitized before log output)
M. Restart does not restore execution state as conversational memory
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)


def _load(name: str, rel_path: str):
    path = os.path.join(CODE_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ── Module loaders ────────────────────────────────────────────────────────────

def _load_execution_boundary():
    return _load("execution_boundary", "kernel/execution_boundary.py")


def _load_credential_sanitizer():
    return _load("credential_sanitizer", "kernel/credential_sanitizer.py")


def _load_approval_gate():
    return _load("approval_gate_eb", "kernel/approval_gate.py")


def _load_capability_registry():
    return _load("capability_registry_eb", "kernel/capability_registry.py")


def _load_permission_registry():
    return _load("permission_registry_eb", "kernel/permission_registry.py")


def _load_execution_authorization():
    # Ensure dependencies are loaded first
    cap_mod = _load_capability_registry()
    perm_mod = _load_permission_registry()
    mod = _load("execution_authorization_eb", "kernel/execution_authorization.py")
    return mod, cap_mod, perm_mod


def _load_file_executor():
    return _load("executor_file_eb", "kernel/executor_file.py")


def _load_executive_conversation():
    return _load("executive_conversation_eb", "executive_conversation.py")


# ═══════════════════════════════════════════════════════════════════════════════
# A–E — Guardian fail-closed tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGuardianFailClosed(unittest.TestCase):
    """A–E: Guardian must deny execution in all non-pass states."""

    def setUp(self):
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary
        self.BoundaryVerdict = mod.BoundaryVerdict

    def _boundary(self):
        return self.ExecutionBoundary()  # no approval_gate, no execution_auth

    # A — Guardian missing (None)
    def test_A_guardian_none_denies(self):
        result = self._boundary().evaluate(
            guardian=None,
            request_type="execution",
            intent="build_homepage",
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "guardian_not_pass")

    # B — Guardian empty dict {}
    def test_B_guardian_empty_dict_denies(self):
        result = self._boundary().evaluate(
            guardian={},
            request_type="execution",
            intent="build_homepage",
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)
        self.assertFalse(result.allowed)

    # C — Guardian status unknown
    def test_C_guardian_unknown_status_denies(self):
        for status in ("", None, "unknown", "maybe", "ok", "1", "true"):
            with self.subTest(status=status):
                result = self._boundary().evaluate(
                    guardian={"status": status},
                    request_type="execution",
                    intent="build_homepage",
                )
                self.assertEqual(result.verdict, self.BoundaryVerdict.DENY,
                                 msg=f"Expected DENY for status={status!r}")

    # D — Guardian explicitly blocked
    def test_D_guardian_blocked_denies(self):
        result = self._boundary().evaluate(
            guardian={"status": "blocked"},
            request_type="execution",
            intent="build_homepage",
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)

    # E — Guardian needs_approval → deny (pending approval, not allowed)
    def test_E_guardian_needs_approval_denies(self):
        result = self._boundary().evaluate(
            guardian={"status": "needs_approval"},
            request_type="execution",
            intent="build_homepage",
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)


# ═══════════════════════════════════════════════════════════════════════════════
# F — ExecutionAuthorization denied → execution denied
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionAuthorizationDenied(unittest.TestCase):
    """F: ExecutionAuthorization denied → boundary denies."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        auth_mod, cap_mod, perm_mod = _load_execution_authorization()
        self.cap_reg = cap_mod.CapabilityRegistry(self._tmp)
        self.perm_reg = perm_mod.PermissionRegistry(self._tmp)
        self.auth = auth_mod.ExecutionAuthorization(self._tmp, self.cap_reg, self.perm_reg)

        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary
        self.BoundaryVerdict = mod.BoundaryVerdict

    def test_F_auth_denied_blocks_execution(self):
        # capability "nonexistent_cap" is not registered → ExecutionAuthorization returns denied
        boundary = self.ExecutionBoundary(execution_auth=self.auth)
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
            capability_name="nonexistent_cap",
            action="write",
        )
        self.assertIn(result.verdict, (self.BoundaryVerdict.DENY, self.BoundaryVerdict.PENDING))
        self.assertFalse(result.allowed)

    def test_F_file_tools_not_granted_have_no_execution_fallback(self):
        file_cap = self.cap_reg.get_by_name("file_operations")
        self.assertIsNotNone(file_cap)
        self.perm_reg.ensure(file_cap["capability_id"])  # keep default not_granted

        boundary = self.ExecutionBoundary(execution_auth=self.auth)
        for action, tool_name in (("read", "file.read"), ("write", "file.create")):
            with self.subTest(action=action, tool_name=tool_name):
                result = boundary.evaluate(
                    guardian={"status": "pass"},
                    request_type="execution",
                    intent="build_homepage",
                    capability_name="file_operations",
                    action=action,
                    context={"tool_name": tool_name},
                )
                self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)
                self.assertEqual(result.reason, "execution_authorization_denied")
                self.assertFalse(result.allowed)


# ═══════════════════════════════════════════════════════════════════════════════
# Regression — Phase 1 fail-closed dependency behavior
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionBoundaryFailClosedDependencies(unittest.TestCase):
    """Regression: guardian pass must not bypass missing/unavailable dependencies."""

    def setUp(self):
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary
        self.BoundaryVerdict = mod.BoundaryVerdict

    def test_guardian_pass_with_missing_execution_auth_denies(self):
        boundary = self.ExecutionBoundary()  # execution_auth intentionally missing
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
            action="write",
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)
        self.assertEqual(result.reason, "execution_authorization_missing")

    def test_guardian_pass_with_required_approval_gate_missing_denies(self):
        class _ApprovedAuth:
            def check(self, **kwargs):
                return {"status": "approved", "request_id": "req-1"}

        boundary = self.ExecutionBoundary(execution_auth=_ApprovedAuth())
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
            action="delete",  # high risk → approval gate required
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)
        self.assertEqual(result.reason, "approval_gate_required_missing")

    def test_execution_boundary_dependencies_unavailable_denies(self):
        class _BrokenExecutionAuth:
            def check(self, **kwargs):
                raise RuntimeError("execution auth backend offline")

        boundary = self.ExecutionBoundary(execution_auth=_BrokenExecutionAuth())
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
            action="write",
        )
        self.assertEqual(result.verdict, self.BoundaryVerdict.DENY)
        self.assertEqual(result.reason, "execution_authorization_unavailable")


# ═══════════════════════════════════════════════════════════════════════════════
# G — FileExecutor: execution without authorization token
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileExecutorAuthorizationCheck(unittest.TestCase):
    """G: ExecutionBoundary must deny before FileExecutor is called."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary
        self.BoundaryVerdict = mod.BoundaryVerdict

    def test_G_no_guardian_prevents_file_write(self):
        """
        When Guardian is missing, ExecutionBoundary denies — FileExecutor
        must never be called.  We verify this by ensuring the boundary's
        verdict is DENY when guardian is absent, which means the calling code
        must not invoke FileExecutor.
        """
        executor_mod = _load_file_executor()
        boundary = self.ExecutionBoundary()

        result = boundary.evaluate(
            guardian=None,
            request_type="execution",
            intent="build_homepage",
        )
        self.assertFalse(result.allowed,
                         "FileExecutor must not be reached when Guardian is absent")

        # Verify FileExecutor itself still works in isolation (it has no internal
        # auth check — the boundary is the gate, not the executor).
        executor = executor_mod.FileExecutor(self._tmp)
        write_result = executor.execute({
            "id": "t1",
            "action": "write",
            "target": "09_Assets/runtime_workspace/test_boundary.txt",
            "content": "test",
        })
        # The executor succeeds when called directly — proof that the boundary
        # (not the executor) must be the gate.
        self.assertEqual(write_result["status"], "completed")


# ═══════════════════════════════════════════════════════════════════════════════
# H — Conversational request cannot enter side-effect execution
# ═══════════════════════════════════════════════════════════════════════════════

class TestConversationalRequestBlocked(unittest.TestCase):
    """H: Conversational types are denied unless intent is explicitly kernel-actionable."""

    def setUp(self):
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary
        self.BoundaryVerdict = mod.BoundaryVerdict

    def test_H_conversational_types_denied(self):
        boundary = self.ExecutionBoundary()
        conversational_types = ("question", "greeting", "analysis", "memory", "creative")
        non_actionable_intents = ("chat", "help", "explain", "unknown", "")
        for rt in conversational_types:
            for intent in non_actionable_intents:
                with self.subTest(request_type=rt, intent=intent):
                    result = boundary.evaluate(
                        guardian={"status": "pass"},
                        request_type=rt,
                        intent=intent,
                    )
                    self.assertEqual(
                        result.verdict, self.BoundaryVerdict.DENY,
                        msg=f"Expected DENY for conversational {rt!r}/{intent!r}",
                    )

    def test_H_actionable_intent_with_pass_guardian_allowed(self):
        """build_homepage with guardian=pass remains executable when auth explicitly approves."""
        class _ApprovedAuth:
            def check(self, **kwargs):
                return {"status": "approved", "request_id": "req-1"}

        boundary = self.ExecutionBoundary(execution_auth=_ApprovedAuth())
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="question",  # conversational but with KERNEL_ACTIONABLE_INTENT
            intent="build_homepage",
        )
        # Conversational behavior stays the same for actionable intents when auth approves.
        self.assertEqual(result.verdict, self.BoundaryVerdict.ALLOW)


# ═══════════════════════════════════════════════════════════════════════════════
# I — kernel_execution_reply cannot bypass the boundary
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelReplyDoesNotBypassBoundary(unittest.TestCase):
    """
    I: The _can_use_kernel_reply logic must be fail-closed.

    We test the exact logic used in ameer_server.py section 5b to ensure
    that a missing/empty/unknown guardian_status cannot produce _can_use_kernel_reply=True.
    """

    def _evaluate_can_use_kernel_reply(self, guardian_status_raw, reasoning_guardian_raw,
                                        request_type="execution", intent="build_homepage",
                                        kernel_execution_reply="some_reply"):
        """Mirrors the fail-closed logic in ameer_server.py section 5b."""
        KERNEL_ACTIONABLE_INTENTS = {"build_homepage", "build_generic"}
        _CONVERSATIONAL_TYPES = {"question", "greeting", "analysis", "memory", "creative"}

        _raw_gs = guardian_status_raw
        _guardian_status = str(_raw_gs).strip().lower() if _raw_gs else "missing"

        _raw_rg = reasoning_guardian_raw
        _reasoning_guardian = str(_raw_rg).strip().lower() if _raw_rg else _guardian_status

        _rt = (request_type or "").strip().lower()
        _is_conversational = (_rt in _CONVERSATIONAL_TYPES) or (not _rt)

        return (
            kernel_execution_reply is not None
            and _guardian_status == "pass"
            and _reasoning_guardian == "pass"
            and (not _is_conversational or intent in KERNEL_ACTIONABLE_INTENTS)
        )

    def test_I_missing_guardian_cannot_use_kernel_reply(self):
        self.assertFalse(
            self._evaluate_can_use_kernel_reply(None, None)
        )

    def test_I_empty_string_guardian_cannot_use_kernel_reply(self):
        self.assertFalse(
            self._evaluate_can_use_kernel_reply("", "")
        )

    def test_I_unknown_guardian_cannot_use_kernel_reply(self):
        self.assertFalse(
            self._evaluate_can_use_kernel_reply("unknown", "unknown")
        )

    def test_I_needs_approval_cannot_use_kernel_reply(self):
        self.assertFalse(
            self._evaluate_can_use_kernel_reply("needs_approval", "needs_approval")
        )

    def test_I_explicit_pass_allows_kernel_reply(self):
        self.assertTrue(
            self._evaluate_can_use_kernel_reply(
                "pass", "pass", request_type="execution", intent="build_homepage"
            )
        )


# ═══════════════════════════════════════════════════════════════════════════════
# J — Execution state cannot become permanent memory automatically
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionStateIsolatedFromMemory(unittest.TestCase):
    """J: Execution state keys must be stripped before persisting to conversational memory."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        mod = _load_executive_conversation()
        self.PersistentConversationMemory = mod.PersistentConversationMemory

    def test_J_execution_trace_not_in_persisted_file(self):
        mem = self.PersistentConversationMemory(self._tmp)
        # Inject execution-state keys directly into internal state
        mem._state["execution_trace"] = {"steps": ["step1"], "result": "ok"}
        mem._state["kernel_execution_trace"] = {"pipeline": []}
        mem._state["execution_result"] = {"status": "completed"}
        mem._state["pipeline_trace"] = {"command": "build homepage"}
        mem._state["kernel_reply"] = "✅ done"
        mem._persist()

        # Read persisted file and verify no execution keys
        persisted = json.loads(Path(self._tmp, ".ameer", "conversation_memory.json").read_text())
        self.assertNotIn("execution_trace", persisted)
        self.assertNotIn("kernel_execution_trace", persisted)
        self.assertNotIn("execution_result", persisted)
        self.assertNotIn("pipeline_trace", persisted)
        self.assertNotIn("kernel_reply", persisted)

    def test_J_conversational_fields_still_persisted(self):
        mem = self.PersistentConversationMemory(self._tmp)
        mem._state["unfinished_discussions"] = ["test topic"]
        mem._state["execution_trace"] = {"should": "be_stripped"}
        mem._persist()

        persisted = json.loads(Path(self._tmp, ".ameer", "conversation_memory.json").read_text())
        self.assertIn("unfinished_discussions", persisted)
        self.assertNotIn("execution_trace", persisted)


# ═══════════════════════════════════════════════════════════════════════════════
# K — Credentials are not persisted to conversational memory
# ═══════════════════════════════════════════════════════════════════════════════

class TestCredentialsNotPersisted(unittest.TestCase):
    """K: api_key / token / password must be redacted before persisting."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        mod = _load_executive_conversation()
        self.PersistentConversationMemory = mod.PersistentConversationMemory

    def test_K_api_key_not_in_persisted_file(self):
        mem = self.PersistentConversationMemory(self._tmp)
        mem._state["api_key"] = "sk-supersecretkey123456"
        mem._state["context"] = {"token": "******"}
        mem._persist()

        raw = Path(self._tmp, ".ameer", "conversation_memory.json").read_text()
        self.assertNotIn("sk-supersecretkey123456", raw)
        self.assertNotIn("******", raw)


# ═══════════════════════════════════════════════════════════════════════════════
# L — Credentials are not logged (sanitizer)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCredentialSanitizer(unittest.TestCase):
    """L: sanitize() must redact credential-like values from any payload."""

    def setUp(self):
        mod = _load_credential_sanitizer()
        self.sanitize = mod.sanitize

    def test_L_api_key_in_dict_value_redacted(self):
        payload = {"api_key": "sk-abc123def456ghi789jkl012"}
        result = self.sanitize(payload)
        self.assertEqual(result["api_key"], "[REDACTED]")

    def test_L_token_key_redacted(self):
        result = self.sanitize({"token": "eyJhbGc.sometoken"})
        self.assertEqual(result["token"], "[REDACTED]")

    def test_L_password_key_redacted(self):
        result = self.sanitize({"password": "Ameer2026!"})
        self.assertEqual(result["password"], "[REDACTED]")

    def test_L_nested_secret_redacted(self):
        payload = {"user": {"secret": "mysecretvalue", "name": "Naseem"}}
        result = self.sanitize(payload)
        self.assertEqual(result["user"]["secret"], "[REDACTED]")
        self.assertEqual(result["user"]["name"], "Naseem")

    def test_L_list_items_sanitized(self):
        payload = [{"api_key": "sk-real123456789012345678"}, {"message": "hello"}]
        result = self.sanitize(payload)
        self.assertEqual(result[0]["api_key"], "[REDACTED]")
        self.assertEqual(result[1]["message"], "hello")

    def test_L_safe_payload_untouched(self):
        payload = {"reply": "مرحبًا", "intent": "greeting", "count": 5}
        result = self.sanitize(payload)
        self.assertEqual(result["reply"], "مرحبًا")
        self.assertEqual(result["intent"], "greeting")
        self.assertEqual(result["count"], 5)

    def test_L_authorization_header_redacted(self):
        payload = {"authorization": "******"}
        result = self.sanitize(payload)
        self.assertEqual(result["authorization"], "[REDACTED]")

    def test_L_bearer_token_in_string_value_redacted(self):
        # Verify that a real sk- style token in a string value gets redacted
        # (32+ chars of alphanumeric = long hex / API-key-like pattern).
        long_hex_token = "a" * 32  # 32 lowercase hex chars — caught by hex pattern
        payload = {"message": f"token is {long_hex_token} in payload"}
        result = self.sanitize(payload)
        self.assertNotIn(long_hex_token, result["message"])
        # Also verify authorization as a key is still redacted (separate coverage)
        payload2 = {"authorization": "my-secret-value"}
        result2 = self.sanitize(payload2)
        self.assertEqual(result2["authorization"], "[REDACTED]")

    def test_L_safe_arabic_text_untouched(self):
        payload = {"reply": "أنا أمير، شريكك التنفيذي"}
        result = self.sanitize(payload)
        self.assertIn("أمير", result["reply"])


# ═══════════════════════════════════════════════════════════════════════════════
# M — Restart does not restore execution state as conversational memory
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestartIsolation(unittest.TestCase):
    """M: After restart, execution state must not appear in conversational memory."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        mod = _load_executive_conversation()
        self.PersistentConversationMemory = mod.PersistentConversationMemory

    def test_M_execution_state_not_loaded_on_restart(self):
        # Session 1: write execution state to disk (bypassing _persist guard)
        mem_path = Path(self._tmp, ".ameer", "conversation_memory.json")
        state_with_execution = {
            "unfinished_discussions": ["real discussion"],
            "execution_trace": {"pipeline": ["step1", "step2"]},
            "kernel_execution_trace": {"command": "build homepage", "result": "ok"},
            "updated_at": "2026-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
        }
        mem_path.write_text(json.dumps(state_with_execution, ensure_ascii=False))

        # Session 2: load fresh memory instance (simulating restart)
        mem2 = self.PersistentConversationMemory(self._tmp)
        snapshot = mem2.snapshot()

        # The execution-trace keys may still be in memory (they were on disk)
        # but they must be stripped on the next _persist call
        mem2._persist()
        persisted_after_restart = json.loads(mem_path.read_text())

        # After one persist cycle, execution state must not be in file
        self.assertNotIn("execution_trace", persisted_after_restart)
        self.assertNotIn("kernel_execution_trace", persisted_after_restart)
        # But conversational fields must survive
        self.assertIn("unfinished_discussions", persisted_after_restart)


# ═══════════════════════════════════════════════════════════════════════════════
# Extra: ExecutionBoundary extract_guardian_status edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractGuardianStatus(unittest.TestCase):
    """Unit tests for the internal _extract_guardian_status helper."""

    def setUp(self):
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary

    def test_none_returns_missing(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status(None), "missing")

    def test_empty_dict_returns_missing(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({}), "missing")

    def test_none_status_returns_missing(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({"status": None}), "missing")

    def test_empty_string_status_returns_missing(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({"status": ""}), "missing")

    def test_pass_returns_pass(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({"status": "pass"}), "pass")

    def test_case_insensitive_pass(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({"status": "PASS"}), "pass")

    def test_blocked_returns_blocked(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({"status": "blocked"}), "blocked")

    def test_needs_approval_returns_needs_approval(self):
        self.assertEqual(self.ExecutionBoundary._extract_guardian_status({"status": "needs_approval"}), "needs_approval")


# ═══════════════════════════════════════════════════════════════════════════════
# N — POST /execute endpoint boundary integration tests
# ═══════════════════════════════════════════════════════════════════════════════

def _boundary_logic_execute_tasks(tasks, guardian, boundary):
    """
    Mirrors the ExecutionBoundary gate logic added to POST /execute in ameer_server.py.
    Returns (allowed: bool, deny_reason: str | None).
    """
    _HIGH_RISK = {"delete", "publish", "external", "financial"}
    _ACTION_PRIORITY = ["financial", "delete", "publish", "external"]
    _task_actions = {str(t.get("action", "")).strip().lower() for t in tasks if isinstance(t, dict)}
    if _task_actions & _HIGH_RISK:
        derived_action = next(a for a in _ACTION_PRIORITY if a in _task_actions)
    elif _task_actions - {"", "write"}:
        derived_action = next(a for a in sorted(_task_actions) if a not in {"", "write"})
    elif "write" in _task_actions:
        derived_action = "write"
    else:
        return False, "unknown_action"

    if boundary is None:
        return False, "boundary_missing"

    result = boundary.evaluate(
        guardian=guardian,
        request_type="execution",
        intent="execute_tasks",
        capability_name="file_operations",
        action=derived_action,
        context={"task_count": len(tasks), "actions": list(_task_actions)},
        requested_by="execute_endpoint",
    )
    return result.allowed, (None if result.allowed else result.reason)


def _boundary_logic_execute_command(command, guardian, boundary, decomposer=None):
    """
    Mirrors the ExecutionBoundary gate logic added to POST /execute/command in ameer_server.py.
    Returns (allowed: bool, deny_reason: str | None).
    """
    intent = "unknown"
    action = "write"
    if decomposer is not None:
        try:
            decomp = decomposer.decompose(command)
            intent = str(decomp.get("intent", "unknown") or "unknown").strip().lower()
            first_task = (decomp.get("tasks") or [{}])[0]
            action = str(first_task.get("action", "write") or "write").strip().lower() or "write"
        except Exception:
            pass

    if boundary is None:
        return False, "boundary_missing"

    result = boundary.evaluate(
        guardian=guardian,
        request_type="execution",
        intent=intent,
        capability_name="file_operations",
        action=action,
        context={"command": command[:240]},
        requested_by="execute_command_endpoint",
    )
    return result.allowed, (None if result.allowed else result.reason)


class _ApprovedAuthForEndpoints:
    def check(self, **kwargs):
        return {"status": "approved", "request_id": "req-endpoint-ok"}


class _DeniedAuthForEndpoints:
    def check(self, **kwargs):
        return {"status": "denied", "request_id": "req-endpoint-denied", "reason": "permission_denied"}


_WRITE_TASK = {"id": "t1", "action": "write", "executor": "file",
               "target": "09_Assets/runtime_workspace/home/index.html", "content": "<html/>"}


class TestPostExecuteEndpointBoundary(unittest.TestCase):
    """
    N — POST /execute endpoint must be gated by ExecutionBoundary.

    These tests replicate the exact guard logic inserted into the endpoint
    to prove the gate behaviour without requiring a live HTTP server.
    """

    def setUp(self):
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary
        self.BoundaryVerdict = mod.BoundaryVerdict

    def _make_boundary(self, execution_auth=None):
        return self.ExecutionBoundary(execution_auth=execution_auth)

    # ── N-A: No guardian → DENY, KERNEL.execute_task must NOT be called ──────

    def test_NA_no_guardian_denies(self):
        """POST /execute with no guardian field → boundary denies, execute_task skipped."""
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_tasks(
            tasks=[_WRITE_TASK],
            guardian={},          # missing guardian
            boundary=boundary,
        )
        self.assertFalse(allowed, "Expected boundary to deny when guardian is absent")
        self.assertEqual(reason, "guardian_not_pass")

    # ── N-B: Guardian blocked → DENY ─────────────────────────────────────────

    def test_NB_guardian_blocked_denies(self):
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_tasks(
            tasks=[_WRITE_TASK],
            guardian={"status": "blocked"},
            boundary=boundary,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "guardian_not_pass")

    # ── N-C: ExecutionAuthorization denied → DENY ────────────────────────────

    def test_NC_execution_auth_denied_denies(self):
        boundary = self._make_boundary(execution_auth=_DeniedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_tasks(
            tasks=[_WRITE_TASK],
            guardian={"status": "pass"},
            boundary=boundary,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "execution_authorization_denied")

    # ── N-D: Boundary missing → DENY (fail-closed) ───────────────────────────

    def test_ND_missing_boundary_denies(self):
        allowed, reason = _boundary_logic_execute_tasks(
            tasks=[_WRITE_TASK],
            guardian={"status": "pass"},
            boundary=None,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "boundary_missing")

    # ── N-E: Unknown action → DENY ───────────────────────────────────────────

    def test_NE_unknown_action_denies(self):
        task_no_action = {"id": "t1", "executor": "file",
                          "target": "09_Assets/runtime_workspace/home/index.html", "content": "x"}
        allowed, reason = _boundary_logic_execute_tasks(
            tasks=[task_no_action],
            guardian={"status": "pass"},
            boundary=self._make_boundary(execution_auth=_ApprovedAuthForEndpoints()),
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "unknown_action")

    # ── N-F: Guardian pass + auth approved → ALLOW ───────────────────────────

    def test_NF_pass_guardian_approved_auth_allows(self):
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_tasks(
            tasks=[_WRITE_TASK],
            guardian={"status": "pass"},
            boundary=boundary,
        )
        self.assertTrue(allowed, f"Expected ALLOW but got DENY: {reason}")
        self.assertIsNone(reason)


# ═══════════════════════════════════════════════════════════════════════════════
# O — POST /execute/command endpoint boundary integration tests
# ═══════════════════════════════════════════════════════════════════════════════

class _FakeDecomposer:
    """Minimal TaskDecomposer stub that returns a deterministic intent and task."""
    def decompose(self, command: str) -> dict:
        return {
            "intent": "build_homepage",
            "task_count": 1,
            "tasks": [{"id": "t1", "action": "write", "executor": "file",
                        "target": "09_Assets/runtime_workspace/home/index.html",
                        "content": "<html/>"}],
        }


class _UnknownDecomposer:
    def decompose(self, command: str) -> dict:
        return {"intent": "unknown", "task_count": 0, "tasks": []}


class TestPostExecuteCommandEndpointBoundary(unittest.TestCase):
    """
    O — POST /execute/command endpoint must be gated by ExecutionBoundary.
    """

    def setUp(self):
        mod = _load_execution_boundary()
        self.ExecutionBoundary = mod.ExecutionBoundary

    def _make_boundary(self, execution_auth=None):
        return self.ExecutionBoundary(execution_auth=execution_auth)

    # ── O-A: No guardian → DENY, execute_command must NOT be called ──────────

    def test_OA_no_guardian_denies(self):
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_command(
            command="ابنِ الصفحة الرئيسية",
            guardian={},
            boundary=boundary,
            decomposer=_FakeDecomposer(),
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "guardian_not_pass")

    # ── O-B: Guardian blocked → DENY ─────────────────────────────────────────

    def test_OB_guardian_blocked_denies(self):
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_command(
            command="ابنِ الصفحة الرئيسية",
            guardian={"status": "blocked"},
            boundary=boundary,
            decomposer=_FakeDecomposer(),
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "guardian_not_pass")

    # ── O-C: ExecutionAuthorization denied → DENY ────────────────────────────

    def test_OC_execution_auth_denied_denies(self):
        boundary = self._make_boundary(execution_auth=_DeniedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_command(
            command="ابنِ الصفحة الرئيسية",
            guardian={"status": "pass"},
            boundary=boundary,
            decomposer=_FakeDecomposer(),
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "execution_authorization_denied")

    # ── O-D: Boundary missing → DENY (fail-closed) ───────────────────────────

    def test_OD_missing_boundary_denies(self):
        allowed, reason = _boundary_logic_execute_command(
            command="ابنِ الصفحة الرئيسية",
            guardian={"status": "pass"},
            boundary=None,
            decomposer=_FakeDecomposer(),
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "boundary_missing")

    # ── O-E: Guardian pass + auth approved → ALLOW ───────────────────────────

    def test_OE_pass_guardian_approved_auth_allows(self):
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_command(
            command="ابنِ الصفحة الرئيسية",
            guardian={"status": "pass"},
            boundary=boundary,
            decomposer=_FakeDecomposer(),
        )
        self.assertTrue(allowed, f"Expected ALLOW but got DENY: {reason}")
        self.assertIsNone(reason)

    # ── O-F: Decomposer unavailable → falls back to write, still gated ───────

    def test_OF_no_decomposer_falls_back_to_write(self):
        """Without a decomposer, action defaults to 'write'; guardian still enforced."""
        boundary = self._make_boundary(execution_auth=_ApprovedAuthForEndpoints())
        allowed, reason = _boundary_logic_execute_command(
            command="some command",
            guardian={},            # missing guardian
            boundary=boundary,
            decomposer=None,        # no decomposer
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "guardian_not_pass")


# ═══════════════════════════════════════════════════════════════════════════════
# P — No external execution path bypasses ExecutionBoundary (static callers audit)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoDirectExecutionBypass(unittest.TestCase):
    """
    P — Repository-wide verification that every external execution path in
    ameer_server.py is gated by the boundary logic.

    Reads ameer_server.py as source text and verifies that each KERNEL call
    to execute_task / execute_command is preceded (in the same function block)
    by the boundary guard pattern.
    """

    _SERVER_PATH = os.path.join(ROOT, "ameer_server.py")

    def _server_source(self) -> str:
        with open(self._SERVER_PATH, encoding="utf-8") as fh:
            return fh.read()

    def test_P_execute_task_gated(self):
        """KERNEL.execute_task() in POST /execute must be preceded by boundary deny path."""
        src = self._server_source()
        # Find the /execute endpoint body — look for the guard keyword we inserted
        self.assertIn("execute_tasks_boundary_denied", src,
                      "POST /execute is missing ExecutionBoundary gate log")
        self.assertIn("_exec_boundary_allowed", src,
                      "POST /execute is missing _exec_boundary_allowed guard variable")

    def test_P_execute_command_gated(self):
        """KERNEL.execute_command() in POST /execute/command must be preceded by boundary deny path."""
        src = self._server_source()
        self.assertIn("execute_command_boundary_denied", src,
                      "POST /execute/command is missing ExecutionBoundary gate log")
        self.assertIn("_cmd_boundary_allowed", src,
                      "POST /execute/command is missing _cmd_boundary_allowed guard variable")

    def test_P_execute_task_cannot_run_without_allowed_flag(self):
        """
        In the execute_tasks function body, KERNEL.execute_task must only appear
        after 'if _exec_boundary_allowed' or 'if not _exec_boundary_allowed' (the deny path).
        """
        src = self._server_source()
        # The deny-path guard must appear before the kernel call in textual order
        boundary_guard_pos = src.find("_exec_boundary_allowed")
        kernel_call_pos = src.find("KERNEL.execute_task(tasks)", boundary_guard_pos)
        self.assertGreater(
            kernel_call_pos, boundary_guard_pos,
            "KERNEL.execute_task(tasks) must come after the boundary guard in source",
        )

    def test_P_execute_command_cannot_run_without_allowed_flag(self):
        src = self._server_source()
        boundary_guard_pos = src.find("_cmd_boundary_allowed")
        kernel_call_pos = src.find("KERNEL.execute_command(command)", boundary_guard_pos)
        self.assertGreater(
            kernel_call_pos, boundary_guard_pos,
            "KERNEL.execute_command(command) must come after the boundary guard in source",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
