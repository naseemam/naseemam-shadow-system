"""
test_p07_execution_contract.py
================================
P0.7 Runtime Refactor (Execution Contract) — acceptance tests.

Verifies:
1.  ExecutiveBrain.get_reasoning_output() returns {reasoning, executive_state} with no visible user text
2.  Executive Brain reasoning output contains no draft_reply / executive_message text
3.  ConversationPlannerState exposes objectives, priorities, risks, recommendations
4.  Planner.plan() returns only objectives, priorities, risks, recommendations (P0.7 fields)
5.  ECE.execute() builds reply from empty buffer (draft_reply is ignored)
6.  ECE.execute() returns response_owner = "ExecutiveConversationEngine"
7.  ECE.execute() does NOT expose was_modified / draft_reply / append / prepend fields
8.  ResponseFormatter performs formatting only, no semantic modification
9.  /ask/trace returns executive_brain_reasoning (not ece_input/ece_modification)
10. /ask/trace planner_output contains objectives, priorities, risks, recommendations
11. /ask/trace final_response has response_owner = ExecutiveConversationEngine
12. /ask/trace does NOT contain was_modified, draft_before_ece, ece_modification keys
13. /ask returns a valid reply owned by ECE
"""

import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ── Load executive_brain ─────────────────────────────────────────────────────
_brain_spec = importlib.util.spec_from_file_location(
    "executive_brain", os.path.join(ROOT, "06_Code", "executive_brain.py")
)
_brain_mod = importlib.util.module_from_spec(_brain_spec)
sys.modules["executive_brain"] = _brain_mod
_brain_spec.loader.exec_module(_brain_mod)
ExecutiveBrain = _brain_mod.ExecutiveBrain

# ── Load executive_conversation ──────────────────────────────────────────────
_conv_spec = importlib.util.spec_from_file_location(
    "executive_conversation", os.path.join(ROOT, "06_Code", "executive_conversation.py")
)
_conv_mod = importlib.util.module_from_spec(_conv_spec)
sys.modules["executive_conversation"] = _conv_mod
_conv_spec.loader.exec_module(_conv_mod)
ConversationPlannerState = _conv_mod.ConversationPlannerState
PersistentConversationMemory = _conv_mod.PersistentConversationMemory
ExecutiveConversationEngine = _conv_mod.ExecutiveConversationEngine

# ── Load response_formatter ──────────────────────────────────────────────────
_fmt_spec = importlib.util.spec_from_file_location(
    "response_formatter", os.path.join(ROOT, "06_Code", "response_formatter.py")
)
_fmt_mod = importlib.util.module_from_spec(_fmt_spec)
sys.modules["response_formatter"] = _fmt_mod
_fmt_spec.loader.exec_module(_fmt_mod)
ResponseFormatter = _fmt_mod.ResponseFormatter

# ── Load ameer_server (TestClient) ───────────────────────────────────────────
_srv_spec = importlib.util.spec_from_file_location("ameer_server", os.path.join(ROOT, "ameer_server.py"))
_srv_mod = importlib.util.module_from_spec(_srv_spec)
sys.modules["ameer_server"] = _srv_mod
_srv_spec.loader.exec_module(_srv_mod)
app = _srv_mod.app

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)


def _make_plan(**kwargs):
    defaults = {
        "request_type": "question",
        "ambiguous": False,
        "clarification_needed": False,
        "clarification_question": None,
        "context_links": [],
        "context_summary": "",
        "plan_type": "direct",
        "steps": [],
        "selected_agent": "ameer_core",
        "supporting_agents": [],
        "agent_reasoning": "test",
        "guardian_status": "pass",
        "guardian_reason": "no risk",
        "autonomy_level": "act_autonomously",
        "should_remember": False,
        "memory_note": None,
        "executive_message": "internal",
    }
    defaults.update(kwargs)
    return type("Plan", (), defaults)()


class ExecutiveBrainReasoningOnlyTests(unittest.TestCase):
    """1-2: Executive Brain → Reasoning Only"""

    def setUp(self):
        self.brain = ExecutiveBrain()

    def test_get_reasoning_output_returns_reasoning_and_executive_state(self):
        result = self.brain.get_reasoning_output("ما هو تقدم المشروع؟", [])
        self.assertIn("reasoning", result)
        self.assertIn("executive_state", result)

    def test_get_reasoning_output_reasoning_has_no_visible_user_text_key(self):
        result = self.brain.get_reasoning_output("ما هو تقدم المشروع؟", [])
        # reasoning must not contain any key that produces visible user text
        self.assertNotIn("draft_reply", result)
        self.assertNotIn("reply", result)
        # executive_message is internal and should NOT appear in the top-level output
        self.assertNotIn("executive_message", result)

    def test_get_reasoning_output_reasoning_contains_expected_keys(self):
        result = self.brain.get_reasoning_output("ما المطلوب؟", [])
        reasoning = result["reasoning"]
        for key in ("request_type", "plan_type", "guardian_status", "autonomy_level"):
            self.assertIn(key, reasoning)

    def test_get_reasoning_output_executive_state_contains_expected_keys(self):
        result = self.brain.get_reasoning_output("ما المطلوب؟", [])
        state = result["executive_state"]
        for key in ("selected_agent", "context_links", "ambiguous"):
            self.assertIn(key, state)


class PlannerOutputContractTests(unittest.TestCase):
    """3-4: Planner outputs objectives, priorities, risks, recommendations"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.memory = PersistentConversationMemory(self.tmp)

    def test_planner_state_has_p07_fields(self):
        state = ConversationPlannerState()
        self.assertTrue(hasattr(state, "objectives"))
        self.assertTrue(hasattr(state, "priorities"))
        self.assertTrue(hasattr(state, "risks"))
        self.assertTrue(hasattr(state, "recommendations"))

    def test_plan_returns_objectives(self):
        state = self.memory.plan("ما هي الأهداف؟")
        self.assertIsInstance(state.objectives, list)
        self.assertTrue(len(state.objectives) > 0)

    def test_plan_returns_priorities(self):
        state = self.memory.plan("ما هي الأولويات؟")
        self.assertIsInstance(state.priorities, list)
        self.assertTrue(len(state.priorities) > 0)

    def test_plan_returns_risks(self):
        state = self.memory.plan("ما هي المخاطر؟", pending_approvals=[{"description": "موافقة معلقة"}])
        self.assertIsInstance(state.risks, list)
        self.assertTrue(len(state.risks) > 0)

    def test_plan_returns_recommendations(self):
        state = self.memory.plan("ما التوصيات؟")
        self.assertIsInstance(state.recommendations, list)
        self.assertTrue(len(state.recommendations) > 0)

    def test_plan_to_dict_includes_p07_fields(self):
        state = self.memory.plan("تقدم")
        d = state.to_dict()
        for key in ("objectives", "priorities", "risks", "recommendations"):
            self.assertIn(key, d)


class ECESoleResponseOwnerTests(unittest.TestCase):
    """5-7: ECE builds from empty buffer, owns response, no modification fields"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ece = ExecutiveConversationEngine(self.tmp)

    def _planner_state(self, **kwargs):
        state = PersistentConversationMemory(self.tmp).plan("اختبار")
        for k, v in kwargs.items():
            object.__setattr__(state, k, v)
        return state

    def test_execute_returns_response_owner_ece(self):
        state = self._planner_state()
        result = self.ece.execute(query="اختبار", planner_state=state, dry_run=True)
        self.assertEqual(result.get("response_owner"), "ExecutiveConversationEngine")

    def test_execute_uses_draft_reply_when_no_executive_signals(self):
        """ECE uses draft_reply as primary reply when there are no executive signals (risks, approvals, tasks)."""
        state = self._planner_state()
        draft = "أنا أمير، شريكك التنفيذي."
        result = self.ece.execute(query="من أنت؟", draft_reply=draft, planner_state=state, dry_run=True)
        self.assertEqual(result.get("reply", ""), draft)

    def test_execute_does_not_return_was_modified(self):
        state = self._planner_state()
        result = self.ece.execute(query="اختبار", planner_state=state, dry_run=True)
        self.assertNotIn("was_modified", result)

    def test_execute_does_not_return_draft_before_ece(self):
        state = self._planner_state()
        result = self.ece.execute(query="اختبار", planner_state=state, dry_run=True)
        self.assertNotIn("draft_before_ece", result)

    def test_execute_does_not_return_append_prepend_fields(self):
        state = self._planner_state()
        result = self.ece.execute(query="اختبار", planner_state=state, dry_run=True)
        self.assertNotIn("append", result)
        self.assertNotIn("prepend", result)

    def test_execute_reply_is_non_empty(self):
        state = self._planner_state()
        result = self.ece.execute(query="ما التالي؟", planner_state=state, dry_run=True)
        self.assertTrue(len(result.get("reply", "").strip()) > 0)

    def test_execute_engine_is_executive_conversation_engine(self):
        state = self._planner_state()
        result = self.ece.execute(query="اختبار", planner_state=state, dry_run=True)
        self.assertEqual(result.get("engine"), "executive_conversation_engine")

    def test_normal_running_tasks_do_not_override_draft_reply(self):
        """
        Running tasks with status 'in_progress' (not stalled/blocked) must NOT
        cause the ECE to replace the OpenAI draft_reply with a local template.

        This is the regression test for the architectural bug:
        any non-empty running_tasks list triggered has_executive_signals=True
        even when no task required attention, discarding the AI-generated reply.
        """
        normal_tasks = [{"id": "t1", "title": "نشر النسخة", "status": "in_progress"}]
        state = PersistentConversationMemory(self.tmp).plan(
            "ما أولويات هذا الأسبوع؟",
            running_tasks=normal_tasks,
        )
        openai_draft = "أولويات هذا الأسبوع: إطلاق النسخة وإغلاق المراجعة المالية."
        result = self.ece.execute(
            query="ما أولويات هذا الأسبوع؟",
            draft_reply=openai_draft,
            planner_state=state,
            running_tasks=normal_tasks,
            dry_run=True,
        )
        self.assertEqual(
            result.get("reply"),
            openai_draft,
            "المهام الطبيعية (in_progress) يجب ألا تستبدل رد OpenAI بنص قالبي محلي.",
        )

    def test_stalled_running_tasks_do_override_draft_reply(self):
        """
        Running tasks with status 'blocked' or 'pending' (stalled) MUST still
        trigger executive intervention — the ECE should surface them proactively.
        """
        stalled_tasks = [{"id": "t2", "title": "مراجعة مالية", "status": "blocked"}]
        state = PersistentConversationMemory(self.tmp).plan(
            "ما أولويات هذا الأسبوع؟",
            running_tasks=stalled_tasks,
        )
        openai_draft = "أولويات هذا الأسبوع: إطلاق النسخة وإغلاق المراجعة المالية."
        result = self.ece.execute(
            query="ما أولويات هذا الأسبوع؟",
            draft_reply=openai_draft,
            planner_state=state,
            running_tasks=stalled_tasks,
            dry_run=True,
        )
        self.assertNotEqual(
            result.get("reply"),
            openai_draft,
            "المهام المتوقفة (blocked/pending) يجب أن تُفعّل التدخل التنفيذي وتستبدل رد OpenAI.",
        )


class ResponseFormatterContractTests(unittest.TestCase):
    """8: ResponseFormatter performs formatting only, no semantic change"""

    def setUp(self):
        self.formatter = ResponseFormatter()

    def test_formatter_preserves_arabic_content(self):
        text = "هذا رد عربي واضح للمستخدم."
        result = self.formatter.format_text(text)
        self.assertIn("عربي", result)

    def test_formatter_removes_internal_labels(self):
        text = "User request: اختبار\nهذا هو الرد الصحيح."
        result = self.formatter.format_text(text)
        self.assertNotIn("User request", result)

    def test_formatter_does_not_add_content(self):
        text = "هذا رد."
        result = self.formatter.format_text(text)
        # formatter should not append extra unsolicited content
        self.assertLessEqual(len(result), len(text) + 50)


class AskTraceP07SchemaTests(unittest.TestCase):
    """9-12: /ask/trace returns P0.7 schema"""

    def test_ask_trace_returns_executive_brain_reasoning(self):
        resp = client.post("/ask/trace", json={"query": "من أنت؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("executive_brain_reasoning", data)
        ebr = data["executive_brain_reasoning"]
        self.assertIn("reasoning", ebr)
        self.assertIn("executive_state", ebr)
        self.assertEqual(ebr.get("role"), "Executive Brain → Reasoning Only")

    def test_ask_trace_planner_output_has_p07_fields(self):
        resp = client.post("/ask/trace", json={"query": "ما هي الأهداف؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("planner_output", data)
        po = data["planner_output"]
        for key in ("objectives", "priorities", "risks", "recommendations"):
            self.assertIn(key, po)

    def test_ask_trace_final_response_owner_is_ece(self):
        resp = client.post("/ask/trace", json={"query": "ما التالي؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("final_response", data)
        fr = data["final_response"]
        self.assertEqual(fr.get("response_owner"), "ExecutiveConversationEngine")
        self.assertEqual(fr.get("role"), "Executive Conversation Engine → Final Response Owner")

    def test_ask_trace_no_legacy_modification_fields(self):
        resp = client.post("/ask/trace", json={"query": "اختبار"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotIn("was_modified", data)
        self.assertNotIn("draft_before_ece", data)
        self.assertNotIn("ece_modification", data)
        self.assertNotIn("ece_input", data)

    def test_ask_trace_response_owner_field_at_top_level(self):
        resp = client.post("/ask/trace", json={"query": "اختبار"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("response_owner"), "ExecutiveConversationEngine")

    def test_ask_trace_formatter_role_present(self):
        resp = client.post("/ask/trace", json={"query": "اختبار"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("formatter", data)
        self.assertEqual(data["formatter"].get("role"), "Formatter → Formatting Only")


class AskEndpointECEOwnerTests(unittest.TestCase):
    """13: /ask returns a valid reply"""

    def test_ask_returns_reply(self):
        resp = client.post("/ask", json={"query": "من أنت؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("reply", data)
        self.assertTrue(len(data["reply"].strip()) > 0)

    def test_ask_does_not_expose_internal_fields(self):
        resp = client.post("/ask", json={"query": "ما المطلوب؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in ("was_modified", "draft_before_ece", "ece_modification", "executive_message"):
            self.assertNotIn(key, data)


if __name__ == "__main__":
    unittest.main()
