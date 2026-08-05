import importlib.util
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from knowledge_engine.interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState

sys.path.insert(0, os.path.join(CODE_ROOT, "founder_intelligence"))
from founder_intelligence import FounderIntelligenceLayer, FounderKnowledgeCategory

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


class FounderLayerSpy:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def retrieve(self, query):
        self.calls.append(query)
        return self.records


class FounderIntelligenceTests(unittest.TestCase):
    def test_founder_intelligence_overrides_general_knowledge_for_strategy_queries(self):
        founder_record = KnowledgeRecord(source_path="/founder/vision.md", content="Our vision is to build a calm executive companion.", source_type="markdown")
        founder_record.state = KnowledgeState.TRUSTED
        founder_record.approval_state = KnowledgeState.TRUSTED
        founder_record.confidence_score = 0.99
        founder_record.provenance["priority"] = "founder"
        founder_record.provenance["founder_category"] = FounderKnowledgeCategory.VISION.value

        founder_layer = FounderIntelligenceLayer([founder_record])
        general_gateway = GatewaySpy([type("General", (), {"content": "General knowledge"})()])
        brain = ExecutiveBrain(normalize_fn=lambda x: x, knowledge_gateway=general_gateway, founder_intelligence=founder_layer)

        plan = brain.think("What is our vision for this product?", [], guardian_result={"status": "pass", "reason": ""})

        self.assertEqual(founder_layer.calls, ["What is our vision for this product?"])
        self.assertEqual(general_gateway.calls, [])
        self.assertIn("calm executive companion", plan.context_summary)

    def test_non_founder_questions_continue_using_the_knowledge_engine(self):
        founder_record = KnowledgeRecord(source_path="/founder/vision.md", content="Our vision is to build a calm executive companion.", source_type="markdown")
        founder_record.state = KnowledgeState.TRUSTED
        founder_record.approval_state = KnowledgeState.TRUSTED
        founder_record.confidence_score = 0.99
        founder_record.provenance["priority"] = "founder"
        founder_record.provenance["founder_category"] = FounderKnowledgeCategory.VISION.value

        founder_layer = FounderIntelligenceLayer([founder_record])
        general_gateway = GatewaySpy([type("General", (), {"content": "General knowledge"})()])
        brain = ExecutiveBrain(normalize_fn=lambda x: x, knowledge_gateway=general_gateway, founder_intelligence=founder_layer)

        brain.think("What is the weather today?", [], guardian_result={"status": "pass", "reason": ""})

        self.assertEqual(founder_layer.calls, [])
        self.assertEqual(general_gateway.calls, ["What is the weather today?"])

    def test_greeting_behavior_remains_unchanged(self):
        founder_layer = FounderLayerSpy([])
        general_gateway = GatewaySpy([type("General", (), {"content": "General knowledge"})()])
        brain = ExecutiveBrain(normalize_fn=lambda x: x, knowledge_gateway=general_gateway, founder_intelligence=founder_layer)

        reply, source = brain.compose_final_reply(
            "مرحبا",
            {"intent": "greeting", "results": []},
            [],
            existing_plan=brain.think("مرحبا", [], guardian_result={"status": "pass", "reason": ""}),
        )

        self.assertEqual(reply, "مرحباً! كيف أساعدك؟")
        self.assertEqual(source, "executive_brain_local")
        self.assertEqual(founder_layer.calls, [])
        self.assertEqual(general_gateway.calls, [])


if __name__ == "__main__":
    unittest.main()
