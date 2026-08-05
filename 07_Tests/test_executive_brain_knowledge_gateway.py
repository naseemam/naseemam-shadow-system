import importlib.util
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from knowledge_engine.interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState
from knowledge_engine.retrieval import KnowledgeRetrievalEngine

MODULE_PATH = os.path.join(CODE_ROOT, "executive_brain.py")
SPEC = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["executive_brain"] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain


class GatewaySpy:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def retrieve(self, query):
        self.calls.append(query)
        return self.records


class ExecutiveBrainKnowledgeGatewayTests(unittest.TestCase):
    def test_brain_uses_gateway_for_knowledge_requests(self):
        gateway = GatewaySpy([
            type("Retrieved", (), {"content": "Gateway content"})(),
        ])
        brain = ExecutiveBrain(normalize_fn=lambda x: x, knowledge_gateway=gateway)

        plan = brain.think("ما هي المعلومات الموثوقة؟", [], guardian_result={"status": "pass", "reason": ""})

        self.assertEqual(gateway.calls, ["ما هي المعلومات الموثوقة؟"])
        self.assertIn("Gateway content", plan.context_summary)

    def test_only_trusted_records_are_visible(self):
        knowledge_base = KnowledgeBase()

        trusted = KnowledgeRecord(source_path="/trusted.md", content="Trusted knowledge", source_type="markdown")
        trusted.state = KnowledgeState.TRUSTED
        trusted.approval_state = KnowledgeState.TRUSTED
        trusted.confidence_score = 0.95

        pending = KnowledgeRecord(source_path="/pending.md", content="Pending knowledge", source_type="markdown")
        pending.state = KnowledgeState.PENDING_APPROVAL
        pending.approval_state = KnowledgeState.PENDING_APPROVAL

        knowledge_base.add_record(trusted)
        knowledge_base.add_record(pending)

        gateway = KnowledgeRetrievalEngine(knowledge_base)
        brain = ExecutiveBrain(normalize_fn=lambda x: x, knowledge_gateway=gateway)

        plan = brain.think("ما الذي يمكنني معرفته؟", [], guardian_result={"status": "pass", "reason": ""})

        self.assertIn("Trusted knowledge", plan.context_summary)
        self.assertNotIn("Pending knowledge", plan.context_summary)

    def test_greeting_behavior_remains_unchanged(self):
        gateway = GatewaySpy([type("Retrieved", (), {"content": "Should not be used"})()])
        brain = ExecutiveBrain(normalize_fn=lambda x: x, knowledge_gateway=gateway)

        reply, source = brain.compose_final_reply(
            "مرحبا",
            {"intent": "greeting", "results": []},
            [],
            existing_plan=brain.think("مرحبا", [], guardian_result={"status": "pass", "reason": ""}),
        )

        self.assertEqual(reply, "مرحباً! كيف أساعدك؟")
        self.assertEqual(source, "executive_brain_local")
        self.assertEqual(gateway.calls, [])


if __name__ == "__main__":
    unittest.main()
