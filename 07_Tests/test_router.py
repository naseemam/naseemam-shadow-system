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


class RouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

    def test_identity_route(self):
        result = self.orchestrator.answer("من هي نسيم؟")
        self.assertEqual(result["routing"]["intent"], "identity")
        self.assertEqual(result["selected_agent"], "identity_agent")

    def test_project_route(self):
        result = self.orchestrator.answer("ما هو هدف المشروع؟")
        self.assertEqual(result["routing"]["intent"], "project")
        self.assertEqual(result["selected_agent"], "project_agent")

    def test_greeting_route(self):
        result = self.orchestrator.answer("مرحبا")
        self.assertEqual(result["routing"]["intent"], "greeting")
        self.assertEqual(result["selected_agent"], "greeting_agent")

    def test_execution_request_is_not_routed_to_greeting(self):
        result = self.orchestrator.answer("أنشئ ملفًا باسم notes.md يحتوي على مرحبا")
        self.assertNotEqual(result["routing"]["intent"], "greeting")
        self.assertEqual(result["routing"]["intent"], "execution")
        self.assertEqual(result["selected_agent"], "project_agent")

    def test_project_creation_request_routes_to_project_agent(self):
        result = self.orchestrator.answer("ابن موقع جديد")
        self.assertEqual(result["routing"]["intent"], "project")
        self.assertEqual(result["selected_agent"], "project_agent")


if __name__ == "__main__":
    unittest.main()
