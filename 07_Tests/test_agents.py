import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from agents.base import AgentContext
from agents.registry import AGENTS


class AgentTests(unittest.TestCase):
    def _base_context(self, query="سؤال"):
        return AgentContext(
            query=query,
            intent="knowledge_lookup",
            route={"intent": "knowledge_lookup", "agent": "research_agent", "confidence": 0.55},
            results=[],
            execution_plan={"goal": "اختبار", "steps": ["a", "b", "c"]},
            conversation_state={"is_follow_up": False, "plan_shifted": False},
            active_goal=None,
        )

    def test_all_registered_agents_implement_contract(self):
        for name, agent in AGENTS.items():
            with self.subTest(agent=name):
                output = agent.execute(self._base_context(query="مرحبا" if name == "greeting_agent" else "من هي نسيم؟"))
                self.assertEqual(output.agent, name)
                self.assertIsInstance(output.confidence, float)
                self.assertIsInstance(output.reply_draft, str)
                self.assertIsInstance(output.sources, list)
                self.assertIsInstance(output.actions, list)

    def test_identity_agent_returns_founder_reply(self):
        output = AGENTS["identity_agent"].execute(self._base_context(query="من هي نسيم؟"))
        self.assertEqual(output.agent, "identity_agent")
        self.assertIn("نسيم", output.reply_draft)


if __name__ == "__main__":
    unittest.main()
