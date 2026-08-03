import importlib.util
import os
import sys
import unittest

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "06_Code", "executive_brain.py")
SPEC = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["executive_brain"] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain


class ExecutiveBrainProviderTests(unittest.TestCase):
    def test_provider_reply_is_preferred_over_local_draft(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        brain._call_provider = lambda *args, **kwargs: "رد موثوق من المزود"

        plan = type(
            "Plan",
            (),
            {
                "clarification_needed": False,
                "clarification_question": None,
                "guardian_status": "pass",
                "guardian_reason": "",
                "context_summary": "سياق تجريبي",
                "selected_agent": "research_agent",
                "executive_message": "رسالة محلية",
            },
        )()

        orchestrator_result = {
            "agent_brain_payload": {"draft": "مسودة محلية"},
            "results": [],
        }

        reply, source = brain.compose_final_reply(
            "أريد إجابة جيدة",
            orchestrator_result,
            [],
            existing_plan=plan,
        )

        self.assertEqual(reply, "رد موثوق من المزود")
        self.assertEqual(source, "executive_brain_provider")

    def test_guarded_requests_use_project_focused_blocked_reply(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)

        plan = type(
            "Plan",
            (),
            {
                "clarification_needed": False,
                "clarification_question": None,
                "guardian_status": "needs_approval",
                "guardian_reason": "طلب حساس",
                "context_summary": "سياق تجريبي",
                "selected_agent": "research_agent",
                "executive_message": "رسالة محلية",
            },
        )()

        orchestrator_result = {
            "guardian": {"reason": "طلب حساس"},
            "results": [],
        }

        reply = brain._compose_local_reply("طلب حساس", plan, orchestrator_result)

        self.assertIn("لا أستطيع تنفيذ هذا الطلب بصيغته الحالية", reply)
        self.assertIn("طريقة آمنة", reply)

    def test_sanitize_provider_reply_removes_internal_prompt_leakage(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        leaked = (
            "The final answer should be a single Arabic phrase that summarizes the user's request or query. "
            "The final answer should also include a description of the agent, planning, reasoning, and execution plan to help the user understand what they need to do next."
        )

        sanitized = brain._sanitize_provider_reply(leaked)

        self.assertEqual(sanitized, "")

    def test_identity_routing_keeps_execution_inside_ameer_core(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)

        plan = brain.think(
            "من أنت؟",
            [],
            guardian_result={"status": "pass", "reason": ""},
            routing_hint={"intent": "identity", "agent": "ameer_core"},
        )

        self.assertEqual(plan.selected_agent, "ameer_core")
        self.assertIn("العقل التنفيذي", plan.executive_message)


if __name__ == "__main__":
    unittest.main()
