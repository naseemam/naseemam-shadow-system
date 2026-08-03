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


class RuntimeFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs = [
            {"path": "01_Docs/Master_Plan.md", "text": "The project goal is building Ameer."},
            {"path": "04_Memory/Founder.md", "text": "Naseem is the founder."},
        ]
        cls.orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=docs,
            score_fn=lambda query, text: 1 if "project" in text.lower() or "founder" in text.lower() else 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

    def test_agent_result_schema_is_present(self):
        result = self.orchestrator.answer("من هي نسيم؟")
        self.assertIn("agent_result", result)
        schema = result["agent_result"]
        self.assertIn("agent", schema)
        self.assertIn("confidence", schema)
        self.assertIn("reply_draft", schema)
        self.assertIn("sources", schema)
        self.assertIn("actions", schema)

    def test_runtime_selected_agent_matches_routing(self):
        result = self.orchestrator.answer("ما هو هدف المشروع؟")
        self.assertEqual(result["routing"]["agent"], result["selected_agent"])


if __name__ == "__main__":
    unittest.main()
