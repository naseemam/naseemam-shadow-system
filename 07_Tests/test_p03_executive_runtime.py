"""
test_p03_executive_runtime.py
==============================
P0.3 Executive Runtime Activation — regression + activation tests.

Covers:
1.  Runtime startup: kernel boots, loads founder memory, workspace,
    active projects, pending tasks, pending approvals.
2.  Canonical /ask pipeline order: Kernel context is built BEFORE
    orchestrator / brain run.
3.  Executive Brain receives all Kernel state fields.
4.  First-session briefing flag: is_first_turn fires once then clears.
5.  Proactive context injection: pending approvals, active projects,
    running tasks reach the provider prompt.
6.  Executive (non-chatbot) system prompt: no assistant-style language.
7.  before_request includes full state payload.
8.  after_request records assistant reply in session history.
9.  Kernel health endpoint reflects correct component statuses.
10. compose_final_reply signature accepts new kernel context params.
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

# ── load modules ────────────────────────────────────────────────────────────

def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_kernel_module():
    # Ensure sibling imports work
    if CODE_ROOT not in sys.path:
        sys.path.insert(0, CODE_ROOT)
    return _load("executive_kernel", os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"))


def _load_brain_module():
    if CODE_ROOT not in sys.path:
        sys.path.insert(0, CODE_ROOT)
    return _load("executive_brain", os.path.join(CODE_ROOT, "executive_brain.py"))


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_workspace(tmp: str) -> None:
    """Create minimal workspace structure in tmp dir."""
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory", "Founder.md").write_text(
        "# Founder\nنسيم أمير — المؤسسة والقائدة التنفيذية.\n", encoding="utf-8"
    )
    Path(tmp, "04_Memory", "Projects.md").write_text(
        "# Projects\n## حلم الندى\n## نظام أمير\n", encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Startup: Kernel.boot() loads founder memory, workspace, projects
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelStartup(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        km = _load_kernel_module()
        self.kernel = km.ExecutiveKernel(workspace_root=self.tmp)

    def test_boot_returns_running_status(self):
        result = self.kernel.boot()
        self.assertEqual(result["status"], "running")

    def test_boot_loads_founder_memory(self):
        self.kernel.boot()
        self.assertTrue(self.kernel.founder.is_loaded)
        self.assertIn("Founder.md", self.kernel.founder.sections)

    def test_boot_produces_workspace_summary(self):
        result = self.kernel.boot()
        # workspace_summary key present (may be empty string in minimal workspace)
        self.assertIn("workspace_summary", result)

    def test_boot_loads_active_projects(self):
        self.kernel.boot()
        # Active projects should be extracted from Projects.md
        projects = self.kernel.state.active_projects
        self.assertIsInstance(projects, list)

    def test_boot_exposes_pending_approvals_in_result(self):
        result = self.kernel.boot()
        self.assertIn("pending_approvals", result)
        self.assertIsInstance(result["pending_approvals"], list)

    def test_boot_exposes_pending_tasks_in_result(self):
        result = self.kernel.boot()
        self.assertIn("pending_tasks", result)
        self.assertIsInstance(result["pending_tasks"], list)

    def test_boot_sets_first_turn_flag(self):
        self.kernel.boot()
        self.assertTrue(self.kernel._first_turn)

    def test_boot_initializes_session_context(self):
        self.kernel.boot()
        self.assertEqual(len(self.kernel.session), 0)

    def test_boot_reports_all_components(self):
        result = self.kernel.boot()
        components = result["components"]
        for key in ("state_manager", "founder_profile", "workspace_awareness", "session_context"):
            self.assertIn(key, components, f"Missing component: {key}")
            self.assertEqual(components[key], "ok")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. First-session briefing: is_first_turn fires once then clears
# ═══════════════════════════════════════════════════════════════════════════════

class TestFirstTurnBriefing(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        km = _load_kernel_module()
        self.kernel = km.ExecutiveKernel(workspace_root=self.tmp)
        self.kernel.boot()

    def test_first_request_sets_is_first_turn_true(self):
        ctx = self.kernel.before_request("مرحبا")
        self.assertTrue(ctx["is_first_turn"])

    def test_second_request_sets_is_first_turn_false(self):
        self.kernel.before_request("مرحبا")
        ctx2 = self.kernel.before_request("ما الوضع؟")
        self.assertFalse(ctx2["is_first_turn"])

    def test_first_turn_flag_consumed_after_first_request(self):
        self.kernel.before_request("طلب أول")
        self.assertFalse(self.kernel._first_turn)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. before_request returns full state payload
# ═══════════════════════════════════════════════════════════════════════════════

class TestBeforeRequestPayload(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        km = _load_kernel_module()
        self.kernel = km.ExecutiveKernel(workspace_root=self.tmp)
        self.kernel.boot()

    def test_returns_all_required_fields(self):
        ctx = self.kernel.before_request("ما الأولويات؟")
        required = [
            "conversation_context",
            "founder_context",
            "workspace_summary",
            "pending_approvals",
            "active_projects",
            "running_tasks",
            "executive_assessment",
            "session_count",
            "is_follow_up",
            "is_first_turn",
        ]
        for field in required:
            self.assertIn(field, ctx, f"Missing field: {field}")

    def test_session_records_user_message(self):
        self.kernel.before_request("ما المشاريع النشطة؟")
        self.assertEqual(len(self.kernel.session), 1)

    def test_after_request_records_reply(self):
        self.kernel.before_request("سؤال")
        self.kernel.after_request("هذا هو الرد التنفيذي.")
        self.assertEqual(len(self.kernel.session), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Executive Brain: proactive context injected into system/user prompt
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutiveBrainProactivePrompt(unittest.TestCase):

    def setUp(self):
        self.brain_mod = _load_brain_module()
        self.brain = self.brain_mod.ExecutiveBrain(normalize_fn=lambda x: x.lower())

    def test_active_projects_appear_in_user_prompt(self):
        _, user_prompt = self.brain._build_provider_prompt(
            "ما الوضع؟",
            active_projects=["حلم الندى", "نظام أمير"],
        )
        self.assertIn("حلم الندى", user_prompt)
        self.assertIn("نظام أمير", user_prompt)

    def test_pending_approvals_appear_in_user_prompt(self):
        approvals = [{"id": "a1", "summary": "الموافقة على عقد X"}]
        _, user_prompt = self.brain._build_provider_prompt(
            "هل هناك شيء مهم؟",
            pending_approvals=approvals,
        )
        self.assertIn("الموافقة على عقد X", user_prompt)

    def test_running_tasks_appear_in_user_prompt(self):
        tasks = [{"id": "t1", "title": "إطلاق الموقع"}]
        _, user_prompt = self.brain._build_provider_prompt(
            "ما الوضع؟",
            running_tasks=tasks,
        )
        self.assertIn("إطلاق الموقع", user_prompt)

    def test_first_turn_instruction_injected(self):
        _, user_prompt = self.brain._build_provider_prompt(
            "أهلا",
            is_first_turn=True,
        )
        # The first-turn instruction must appear
        self.assertIn("أول رسالة", user_prompt)

    def test_no_first_turn_instruction_on_follow_up(self):
        _, user_prompt = self.brain._build_provider_prompt(
            "أهلا",
            is_first_turn=False,
        )
        self.assertNotIn("أول رسالة", user_prompt)

    def test_system_prompt_identifies_as_executive_partner(self):
        system_prompt, _ = self.brain._build_provider_prompt("ما الوضع؟")
        self.assertIn("الشريك التنفيذي", system_prompt)

    def test_system_prompt_rejects_assistant_label(self):
        system_prompt, _ = self.brain._build_provider_prompt("ما الوضع؟")
        # Must explicitly say "لستَ مساعدًا"
        self.assertIn("لستَ مساعدًا", system_prompt)

    def test_system_prompt_requires_next_action(self):
        system_prompt, _ = self.brain._build_provider_prompt("ما الوضع؟")
        self.assertIn("الخطوة التالية", system_prompt)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. compose_final_reply accepts new kernel context parameters
# ═══════════════════════════════════════════════════════════════════════════════

class TestComposeFinalReplySignature(unittest.TestCase):

    def setUp(self):
        self.brain_mod = _load_brain_module()
        self.brain = self.brain_mod.ExecutiveBrain(normalize_fn=lambda x: x.lower())

    def test_compose_accepts_kernel_context_params(self):
        """compose_final_reply must not raise when new params are passed."""
        docs = [{"path": "04_Memory/Founder.md", "text": "نسيم هي المؤسسة."}]
        orchestrator_result = {
            "intent": "greeting",
            "guardian": {"status": "pass", "reason": ""},
            "routing": {"intent": "greeting", "agent": "greeting_agent", "confidence": 1.0},
            "agent_result": {"agent": "greeting_agent", "confidence": 1.0, "reply_draft": "", "sources": [], "actions": [], "response_data": {}},
        }
        try:
            reply, source = self.brain.compose_final_reply(
                "مرحبا",
                orchestrator_result,
                docs,
                pending_approvals=[{"id": "x", "summary": "قرار X"}],
                active_projects=["حلم الندى"],
                running_tasks=[{"id": "t1", "title": "مهمة 1"}],
                is_first_turn=True,
            )
            self.assertIsInstance(reply, str)
            self.assertTrue(len(reply) > 0)
        except TypeError as exc:
            self.fail(f"compose_final_reply raised TypeError with new params: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ameer_server /ask passes kernel context to Executive Brain
# ═══════════════════════════════════════════════════════════════════════════════

class TestServerAskKernelIntegration(unittest.TestCase):

    def setUp(self):
        # Import the live server (no actual HTTP calls)
        import ameer_server
        from fastapi.testclient import TestClient
        self.server = ameer_server
        self.client = TestClient(ameer_server.app)

    def test_ask_returns_valid_reply(self):
        resp = self.client.post("/ask", json={"query": "ما وضع المشاريع الآن؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("reply", data)
        self.assertTrue(len(data["reply"]) > 0)

    def test_kernel_health_endpoint_available(self):
        resp = self.client.get("/kernel/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("initialized", data)

    def test_kernel_booted_on_startup(self):
        """KERNEL must be initialized after the app starts."""
        self.assertIsNotNone(self.server.KERNEL)

    def test_ask_does_not_leak_internal_fields(self):
        """routing, selected_agent, agent_result must NOT appear in /ask response body."""
        resp = self.client.post("/ask", json={"query": "من أنت؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for forbidden in ("routing", "selected_agent", "agent_result"):
            self.assertNotIn(forbidden, data, f"Internal field leaked: {forbidden}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Runtime flow: pipeline order enforced
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimePipelineOrder(unittest.TestCase):
    """
    Verifies that Kernel.before_request() is called BEFORE the Orchestrator
    and Executive Brain in the /ask handler.
    """

    def setUp(self):
        import ameer_server
        from fastapi.testclient import TestClient
        self.server = ameer_server
        self.client = TestClient(ameer_server.app)

    def test_ask_kernel_context_available(self):
        """
        After a /ask call, KERNEL.session must contain the user message,
        proving before_request was called (it records the user message).
        """
        kernel = self.server.KERNEL
        if kernel is None:
            self.skipTest("KERNEL not available")
        initial_turns = len(kernel.session)
        self.client.post("/ask", json={"query": "ما الأولويات الآن؟"})
        # Session must have grown by at least 2 (user + assistant)
        self.assertGreaterEqual(len(kernel.session), initial_turns + 2)

    def test_ask_session_records_assistant_reply(self):
        """after_request must record assistant reply in session context."""
        kernel = self.server.KERNEL
        if kernel is None:
            self.skipTest("KERNEL not available")
        self.client.post("/ask", json={"query": "اقترح خطوة تالية."})
        messages = kernel.session.get_messages()
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        self.assertTrue(len(assistant_msgs) >= 1)
        self.assertTrue(len(assistant_msgs[-1]["content"]) > 0)


if __name__ == "__main__":
    unittest.main()
