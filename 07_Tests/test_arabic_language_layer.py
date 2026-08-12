import importlib.util
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from language import arabic_language_layer


class ArabicLanguageLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = arabic_language_layer.ArabicLanguageLayer()

    def test_saudi_colloquial_opinion_is_direct_opinion(self):
        evidence = self.layer.analyze("أمير، وش رأيك في Manus؟")
        self.assertEqual(evidence.category, "direct_opinion")
        self.assertEqual(evidence.preferred_agent, "ameer_core")

    def test_modern_standard_arabic_opinion_is_direct_opinion(self):
        evidence = self.layer.analyze("أمير، ما رأيك في Manus؟")
        self.assertEqual(evidence.category, "direct_opinion")
        self.assertEqual(evidence.preferred_agent, "ameer_core")

    def test_spelling_variants_normalize_to_same_signal(self):
        self.assertEqual(self.layer.normalize("أمير، وش رايك في Manus؟"), self.layer.normalize("امير وش رايك في Manus"))

    def test_direct_question_routes_to_core(self):
        evidence = self.layer.analyze("أمير، ماذا ترى في Manus؟")
        self.assertEqual(evidence.category, "direct_question")
        self.assertEqual(evidence.preferred_agent, "ameer_core")

    def test_research_request_is_detected_as_research(self):
        evidence = self.layer.analyze("أمير، ابحث لي عن Manus")
        self.assertEqual(evidence.category, "research_request")
        self.assertEqual(evidence.preferred_agent, "research_agent")

    def test_execution_request_requires_action_language(self):
        evidence = self.layer.analyze("أمير، أنشئ ملف")
        self.assertEqual(evidence.category, "execution_request")
        self.assertEqual(evidence.preferred_agent, "project_agent")

    def test_memory_request_is_detected(self):
        evidence = self.layer.analyze("أمير، تذكر أنني أفضل العمل في الليل")
        self.assertEqual(evidence.category, "memory_request")
        self.assertEqual(evidence.preferred_intent, "onboarding")

    def test_greeting_is_detected(self):
        evidence = self.layer.analyze("مرحبا أمير")
        self.assertEqual(evidence.category, "greeting")
        self.assertEqual(evidence.preferred_agent, "greeting_agent")

    def test_ambiguous_question_with_nouns_is_not_execution(self):
        evidence = self.layer.analyze("كيف أتعامل مع ملف المشروع؟")
        self.assertNotEqual(evidence.category, "execution_request")


if __name__ == "__main__":
    unittest.main()