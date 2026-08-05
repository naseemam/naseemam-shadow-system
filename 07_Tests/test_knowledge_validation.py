import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from knowledge_engine.document_importer import DocumentKnowledgeImporter
from knowledge_engine.interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState
from knowledge_engine.validation import KnowledgeValidationLayer


class KnowledgeValidationTests(unittest.TestCase):
    def test_imported_document_moves_to_pending_approval_and_then_trusted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "approval.md")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("# Approval\n\nPending review.\n")

            knowledge_base = KnowledgeBase()
            importer = DocumentKnowledgeImporter()
            record = importer.import_document(file_path, knowledge_base, source_category="imported_local")

            self.assertEqual(record.approval_state, KnowledgeState.PENDING_APPROVAL)
            self.assertEqual(record.state, KnowledgeState.PENDING_APPROVAL)
            self.assertEqual(record.confidence_score, 0.9)
            self.assertEqual(knowledge_base.get_visible_records(), [])

            validator = KnowledgeValidationLayer()
            validator.approve(record)

            self.assertEqual(record.approval_state, KnowledgeState.TRUSTED)
            self.assertEqual(record.state, KnowledgeState.TRUSTED)
            self.assertEqual(knowledge_base.get_visible_records()[0].record_id, record.record_id)
            self.assertEqual(knowledge_base.get_executive_brain_visible_records()[0].record_id, record.record_id)

    def test_confidence_assignment_uses_source_category_rules(self):
        validator = KnowledgeValidationLayer()

        founder_record = KnowledgeRecord(source_path="/founder/guide.md", content="Founder's note", source_type="markdown")
        project_record = KnowledgeRecord(source_path="/project/plan.md", content="Project note", source_type="markdown")
        generated_record = KnowledgeRecord(source_path="/generated/summary.md", content="Generated note", source_type="markdown")

        validator.assign_confidence(founder_record, source_category="founder")
        validator.assign_confidence(project_record, source_category="approved_project")
        validator.assign_confidence(generated_record, source_category="generated")

        self.assertEqual(founder_record.confidence_score, 1.0)
        self.assertEqual(project_record.confidence_score, 0.95)
        self.assertEqual(generated_record.confidence_score, 0.2)

    def test_trusted_filtering_excludes_pending_rejected_and_archived_documents(self):
        trusted = KnowledgeRecord(source_path="/trusted.md", content="trusted", source_type="markdown")
        pending = KnowledgeRecord(source_path="/pending.md", content="pending", source_type="markdown")
        rejected = KnowledgeRecord(source_path="/rejected.md", content="rejected", source_type="markdown")
        archived = KnowledgeRecord(source_path="/archived.md", content="archived", source_type="markdown")

        trusted.approval_state = KnowledgeState.TRUSTED
        trusted.state = KnowledgeState.TRUSTED
        pending.approval_state = KnowledgeState.PENDING_APPROVAL
        pending.state = KnowledgeState.PENDING_APPROVAL
        rejected.approval_state = KnowledgeState.REJECTED
        rejected.state = KnowledgeState.REJECTED
        archived.approval_state = KnowledgeState.ARCHIVED
        archived.state = KnowledgeState.ARCHIVED

        knowledge_base = KnowledgeBase()
        knowledge_base.add_record(trusted)
        knowledge_base.add_record(pending)
        knowledge_base.add_record(rejected)
        knowledge_base.add_record(archived)

        self.assertEqual([record.record_id for record in knowledge_base.get_visible_records()], [trusted.record_id])
        self.assertEqual(knowledge_base.get_executive_brain_visible_records(), [trusted])


if __name__ == "__main__":
    unittest.main()
