import importlib.util
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "reasoning_orchestrator.py")

spec = importlib.util.spec_from_file_location("reasoning_orchestrator", MODULE_PATH)
reasoning_orchestrator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reasoning_orchestrator
spec.loader.exec_module(reasoning_orchestrator)


class AmeerOrchestratorIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def normalize(text: str) -> str:
            return text.lower().strip()

        cls.orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=normalize,
        )

    def test_arabic_identity_terms_are_classified_as_identity(self):
        for query in ["من انت", "مين أنت", "عرف بنفسك", "حدثني عن نفسك", "وش أنت", "من هو أمير"]:
            with self.subTest(query=query):
                self.assertEqual(self.orchestrator.classify_intent(query), "identity")

    def test_no_result_fallback_is_not_the_generic_identity_reply(self):
        result = self.orchestrator.answer("ما الذي لا أملكه في هذا الموضوع", max_results=3)
        self.assertEqual(result["intent"], "knowledge_lookup")
        self.assertEqual(result["selected_agent"], "research_agent")
        self.assertEqual(result["reply"], "لا توجد نتائج كافية، يلزم توليد رد توضيحي من Executive Brain.")
        self.assertIn("agent_result", result)

    def test_result_path_uses_a_result_based_reply(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[
                {"path": "01_docs/vision.md", "text": "المؤسسة هي نسيم وتحتاج إلى خطة واضحة."},
                {"path": "04_memory/projects.md", "text": "هذه الملفات تتعلق بمشاريع مختلفة."},
            ],
            score_fn=lambda query, text: 1 if "نسيم" in text or "ملفات" in text else 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        result = orchestrator.answer("من هي نسيم", max_results=3)
        self.assertEqual(result["intent"], "identity")
        self.assertEqual(result["selected_agent"], "identity_agent")
        self.assertIn("نسيم", result["reply"])
        self.assertIn("execution_plan", result)
        self.assertEqual(result["execution_plan"]["planner"], "identity_layer")
        self.assertIn("agent_result", result)

    def test_low_specificity_questions_return_no_results_reply(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[{"path": "01_docs/vision.md", "text": "السؤال هو ما يهم في هذا السياق."}],
            score_fn=lambda query, text: 1 if "سؤال" in text else 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        result = orchestrator.answer("سؤال غير موجود تماما 123456", max_results=3)
        self.assertEqual(result["intent"], "knowledge_lookup")
        self.assertTrue(result["reply"].startswith("الخطة:") or "لا توجد نتائج كافية" in result["reply"])

    def test_follow_up_questions_reuse_previous_context_and_detect_plan_shift(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        first = orchestrator.answer("أريد افتتاح مشروع جديد", session_id="demo-session")
        self.assertTrue(first["conversation_state"]["has_context"])
        self.assertEqual(first["conversation_state"]["active_goal"], "افتتاح مشروع جديد")

        follow_up = orchestrator.answer("ما أول خطوة تنصحني بها؟", session_id="demo-session")
        self.assertTrue(follow_up["conversation_state"]["is_follow_up"])
        self.assertIn("سياق الجلسة", follow_up["reply"])

        changed = orchestrator.answer("لا، غيرت رأيي، سأشتري شركة جاهزة", session_id="demo-session")
        self.assertTrue(changed["conversation_state"]["plan_shifted"])
        self.assertEqual(changed["conversation_state"]["active_goal"], "شراء شركة جاهزة")

    def test_personal_information_requests_route_to_onboarding_memory_path(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        result = orchestrator.answer("أريد أن أخبرك عني وأحب أن تتذكر أنني أفضل العمل في الليل", max_results=3)
        self.assertEqual(result["intent"], "onboarding")
        self.assertEqual(result["selected_agent"], "memory_agent")
        self.assertEqual(result["routing"]["intent"], "onboarding")

    def test_personal_information_requests_persist_memory_to_workspace_files(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        result = orchestrator.answer("أريد أن أخبرك عني وأحب أن تتذكر أنني أفضل العمل في الليل", max_results=3)
        self.assertTrue(result["memory_update"]["saved"])
        self.assertEqual(result["memory_update"]["file"], "04_Memory/Preferences.md")

        memory_path = os.path.join(ROOT, "04_Memory", "Preferences.md")
        with open(memory_path, "r", encoding="utf-8") as handle:
            stored = handle.read()
        self.assertIn("أفضل العمل في الليل", stored)

    def test_execution_requests_with_common_arabic_variants_route_to_execution(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        result = orchestrator.route_query("انشي ملفا باسم test_from_browser.txt يحتوي على مرحبا")

        self.assertEqual(result["intent"], "execution")
        self.assertEqual(result["reason"], "matched execution request")


if __name__ == "__main__":
    unittest.main()
