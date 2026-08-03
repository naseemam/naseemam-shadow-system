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


class FallbackContractTests(unittest.TestCase):
    def test_agent_execute_failure_triggers_recovery_agent(self):
        orchestrator = reasoning_orchestrator.AmeerOrchestrator(
            documents=[],
            score_fn=lambda query, text: 0,
            normalize_fn=lambda text: text.lower().strip(),
        )

        failing_agent = orchestrator.agents["research_agent"]
        original_execute = failing_agent.execute

        def broken_execute(_context):
            raise RuntimeError("forced failure")

        failing_agent.execute = broken_execute
        try:
            result = orchestrator.answer("سؤال عام")
        finally:
            failing_agent.execute = original_execute

        self.assertIn("fallback", result)
        self.assertTrue(result["fallback"]["used"])
        self.assertEqual(result["selected_agent"], "recovery_agent")
        self.assertIn("agent_brain_payload", result)
        self.assertIn("reply", result)
        self.assertTrue(result["reply"].strip())


if __name__ == "__main__":
    unittest.main()
