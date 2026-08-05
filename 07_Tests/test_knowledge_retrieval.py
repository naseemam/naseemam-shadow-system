import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from knowledge_engine.interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState
from knowledge_engine.retrieval import KnowledgeRetrievalEngine


class KnowledgeRetrievalTests(unittest.TestCase):
    def test_trusted_filtering_and_empty_knowledge_base(self):
        knowledge_base = KnowledgeBase()
        engine = KnowledgeRetrievalEngine(knowledge_base)
        self.assertEqual(engine.retrieve("test"), [])

        trusted = KnowledgeRecord(source_path="/trusted.md", content="trusted content", source_type="markdown")
        trusted.state = KnowledgeState.TRUSTED
        trusted.approval_state = KnowledgeState.TRUSTED
        trusted.confidence_score = 0.95
        trusted.provenance["priority"] = "project"

        pending = KnowledgeRecord(source_path="/pending.md", content="pending content", source_type="markdown")
        pending.state = KnowledgeState.PENDING_APPROVAL
        pending.approval_state = KnowledgeState.PENDING_APPROVAL

        knowledge_base.add_record(trusted)
        knowledge_base.add_record(pending)

        results = engine.retrieve("trusted")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "trusted content")

    def test_confidence_and_multiple_document_ranking(self):
        knowledge_base = KnowledgeBase()
        engine = KnowledgeRetrievalEngine(knowledge_base)

        low_confidence = KnowledgeRecord(source_path="/low.md", content="low confidence", source_type="markdown")
        low_confidence.state = KnowledgeState.TRUSTED
        low_confidence.approval_state = KnowledgeState.TRUSTED
        low_confidence.confidence_score = 0.2

        high_confidence = KnowledgeRecord(source_path="/high.md", content="high confidence", source_type="markdown")
        high_confidence.state = KnowledgeState.TRUSTED
        high_confidence.approval_state = KnowledgeState.TRUSTED
        high_confidence.confidence_score = 0.95

        knowledge_base.add_record(low_confidence)
        knowledge_base.add_record(high_confidence)

        results = engine.retrieve("confidence")
        self.assertEqual(results[0].record_id, high_confidence.record_id)
        self.assertGreater(results[0].confidence_score, results[-1].confidence_score)

    def test_founder_and_project_priority_are_respected(self):
        knowledge_base = KnowledgeBase()
        engine = KnowledgeRetrievalEngine(knowledge_base)

        project_doc = KnowledgeRecord(source_path="/project.md", content="project context", source_type="markdown")
        project_doc.state = KnowledgeState.TRUSTED
        project_doc.approval_state = KnowledgeState.TRUSTED
        project_doc.confidence_score = 0.8
        project_doc.provenance["priority"] = "project"

        founder_doc = KnowledgeRecord(source_path="/founder.md", content="founder context", source_type="markdown")
        founder_doc.state = KnowledgeState.TRUSTED
        founder_doc.approval_state = KnowledgeState.TRUSTED
        founder_doc.confidence_score = 0.8
        founder_doc.provenance["priority"] = "founder"

        knowledge_base.add_record(project_doc)
        knowledge_base.add_record(founder_doc)

        results = engine.retrieve("context")
        self.assertEqual(results[0].record_id, founder_doc.record_id)
        self.assertEqual(results[1].record_id, project_doc.record_id)


if __name__ == "__main__":
    unittest.main()
