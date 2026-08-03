import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from agents.base import AgentContext
from agents.registry import AGENTS


class LifecycleContractRegressionTests(unittest.TestCase):
    def test_all_agents_expose_lifecycle_api(self):
        for name, agent in AGENTS.items():
            with self.subTest(agent=name):
                agent.init()
                self.assertTrue(getattr(agent, "initialized", False))
                self.assertIsInstance(agent.namespace, dict)

                context = AgentContext(
                    query="lifecycle check",
                    intent="knowledge_lookup",
                    route={"intent": "knowledge_lookup", "agent": name},
                    results=[],
                    execution_plan={"goal": "contract regression"},
                    conversation_state={"has_context": False},
                    active_goal=None,
                )

                output = agent.render(context)
                self.assertTrue(hasattr(output, "agent"))
                self.assertTrue(hasattr(output, "message"))

                agent.destroy()
                self.assertFalse(getattr(agent, "initialized", True))
                self.assertEqual(agent.namespace, {})


REQUIRED_FIELDS = [
    "agent",
    "confidence",
    "reply_draft",
    "sources",
    "actions",
    "message",
]


class AgentContractRegressionTests(unittest.TestCase):
    def _build_context(self) -> AgentContext:
        return AgentContext(
            query="اختبار عقد الوكيل",
            intent="knowledge_lookup",
            route={"intent": "knowledge_lookup", "agent": "research_agent"},
            results=[],
            execution_plan={"goal": "contract regression"},
            conversation_state={"has_context": False, "active_goal": None},
            active_goal=None,
        )

    def test_all_agents_follow_contract(self):
        context = self._build_context()

        for name, agent in AGENTS.items():
            with self.subTest(agent=name):
                result = agent.execute(context)

                for field in REQUIRED_FIELDS:
                    self.assertTrue(hasattr(result, field), f"{name} missing field: {field}")

                self.assertIsInstance(result.agent, str)
                self.assertIsInstance(result.confidence, float)
                self.assertIsInstance(result.reply_draft, str)
                self.assertIsInstance(result.sources, list)
                self.assertIsInstance(result.actions, list)
                self.assertIsInstance(result.message, str)


if __name__ == "__main__":
    unittest.main()
