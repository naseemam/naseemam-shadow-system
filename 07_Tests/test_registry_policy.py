import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from agents.base import AgentOutput, BaseAgent
from agents.registry import AGENTS, AGENT_CAPABILITIES


class RegistryAdmissionPolicyTests(unittest.TestCase):
    def test_all_admitted_agents_inherit_base_agent(self):
        for name, agent in AGENTS.items():
            with self.subTest(agent=name):
                self.assertIsInstance(agent, BaseAgent)

    def test_all_admitted_agents_have_capabilities_metadata(self):
        for name in AGENTS.keys():
            with self.subTest(agent=name):
                meta = AGENT_CAPABILITIES.get(name)
                self.assertIsInstance(meta, dict)
                self.assertIn("capabilities", meta)
                self.assertIsInstance(meta["capabilities"], list)
                self.assertTrue(meta["capabilities"])

    def test_all_admitted_agents_return_agent_output(self):
        from agents.base import AgentContext

        context = AgentContext(
            query="registry runtime check",
            intent="knowledge_lookup",
            route={"intent": "knowledge_lookup", "agent": "research_agent"},
            results=[],
            execution_plan={"goal": "policy", "steps": ["validate"]},
            conversation_state={"is_follow_up": False, "plan_shifted": False},
            active_goal=None,
        )

        for name, agent in AGENTS.items():
            with self.subTest(agent=name):
                output = agent.execute(context)
                self.assertIsInstance(output, AgentOutput)


if __name__ == "__main__":
    unittest.main()
