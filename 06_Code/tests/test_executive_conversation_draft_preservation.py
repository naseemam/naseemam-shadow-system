"""
Regression tests for ExecutiveConversationEngine.execute().

Bug: For conversational request types (question, analysis, memory, creative),
a valid draft_reply produced by the OpenAI provider was discarded whenever
has_executive_signals evaluated to False was reached via the wrong branch
ordering, causing the engine to fall back to _build_from_buffer() and return
stale planner-state text instead of the fresh AI-generated reply.

Fix: Conversational requests with a non-empty draft_reply now return that
draft immediately, before any has_executive_signals gating or
_build_from_buffer() fallback is evaluated.
"""

import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_reasoning_output(request_type: str) -> dict:
    return {"reasoning": {"request_type": request_type, "guardian_status": "pass"}}


class ExecutiveConversationDraftPreservationTests(unittest.TestCase):
    def _load_ece(self):
        return _load("executive_conversation", os.path.join(CODE_ROOT, "executive_conversation.py"))

    def test_conversational_question_preserves_draft_reply(self):
        """
        A 'question' request type is conversational. When the OpenAI provider
        returns a valid draft_reply, execute() must return it unchanged instead
        of reconstructing a reply from stale planner/task state.
        """
        mod = self._load_ece()
        with tempfile.TemporaryDirectory() as tmp:
            ece = mod.ExecutiveConversationEngine(tmp)
            planner_state = ece.memory.plan("ما هو أفضل نموذج تسعير للمنتج؟")
            draft = "أفضل نموذج تسعير هنا هو الاشتراك الشهري مع خطة مجانية محدودة."
            result = ece.execute(
                query="ما هو أفضل نموذج تسعير للمنتج؟",
                draft_reply=draft,
                planner_state=planner_state,
                reasoning_output=_make_reasoning_output("question"),
                dry_run=True,
            )
            self.assertEqual(
                result["reply"],
                draft,
                "Valid provider draft_reply must be preserved unchanged for 'question' requests",
            )

    def test_conversational_analysis_preserves_draft_reply(self):
        """
        An 'analysis' request type ('explain/why') is conversational. A valid
        draft_reply from the provider must be used directly.
        """
        mod = self._load_ece()
        with tempfile.TemporaryDirectory() as tmp:
            ece = mod.ExecutiveConversationEngine(tmp)
            planner_state = ece.memory.plan(
                "لماذا فشل المشروع؟",
                running_tasks=[{"id": "t1", "title": "مهمة قديمة", "status": "pending"}],
            )
            draft = "السبب الرئيسي هو نقص الموارد في المرحلة الثانية من المشروع."
            result = ece.execute(
                query="لماذا فشل المشروع؟",
                draft_reply=draft,
                planner_state=planner_state,
                running_tasks=[{"id": "t1", "title": "مهمة قديمة", "status": "pending"}],
                reasoning_output=_make_reasoning_output("analysis"),
                dry_run=True,
            )
            self.assertEqual(
                result["reply"],
                draft,
                "Valid provider draft_reply must be preserved unchanged for 'analysis' requests",
            )

    def test_stale_planner_fallback_detection(self):
        """
        Sanity check that _build_from_buffer() produces planner/task-derived
        text that is distinct from a provider draft. This proves that, absent
        the fix, a conversational request with stalled tasks would fall
        through to _build_from_buffer() and leak stale architecture-status
        text instead of the fresh AI-generated draft.
        """
        mod = self._load_ece()
        with tempfile.TemporaryDirectory() as tmp:
            ece = mod.ExecutiveConversationEngine(tmp)
            stalled_tasks = [{"id": "t1", "title": "مهمة قديمة", "status": "pending"}]
            planner_state = ece.memory.plan("هل أنت جاهز؟", running_tasks=stalled_tasks)

            stale_fallback = ece._build_from_buffer(
                query="هل أنت جاهز؟",
                planner_state=planner_state,
                pending_approvals=None,
                running_tasks=stalled_tasks,
                active_projects=None,
                is_first_turn=True,
                reasoning_output=_make_reasoning_output("question"),
                dry_run=True,
            )

            draft = "نعم، أنا جاهز تمامًا للمتابعة."
            result = ece.execute(
                query="هل أنت جاهز؟",
                draft_reply=draft,
                planner_state=planner_state,
                running_tasks=stalled_tasks,
                is_first_turn=True,
                reasoning_output=_make_reasoning_output("question"),
                dry_run=True,
            )

            self.assertNotEqual(
                stale_fallback,
                draft,
                "Fallback buffer text and provider draft must be distinguishable for this test to be meaningful",
            )
            self.assertEqual(
                result["reply"],
                draft,
                "execute() must return the provider draft, not the stale _build_from_buffer() fallback",
            )
            self.assertNotEqual(
                result["reply"],
                stale_fallback,
                "execute() must not fall through to the stale planner-state fallback for conversational requests",
            )


if __name__ == "__main__":
    unittest.main()
