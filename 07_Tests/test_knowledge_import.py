import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from knowledge_engine.document_importer import DocumentKnowledgeImporter
from knowledge_engine.interfaces import KnowledgeBase


class KnowledgeImportTests(unittest.TestCase):
    def test_markdown_import_is_normalized_and_stored_in_knowledge_base(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "notes.md")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("# Hello\r\n\r\nThis is a markdown note.\n")

            knowledge_base = KnowledgeBase()
            importer = DocumentKnowledgeImporter()
            record = importer.import_document(file_path, knowledge_base)

            self.assertEqual(record.source_type, "markdown")
            self.assertEqual(record.content, "# Hello\n\nThis is a markdown note.")
            self.assertEqual(record.source_path, file_path)
            self.assertEqual(len(knowledge_base.records), 1)
            self.assertEqual(len(knowledge_base.long_term_memory), 0)
            self.assertEqual(knowledge_base.records[0].record_id, record.record_id)

    def test_txt_import_is_normalized_and_stored_in_knowledge_base(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "notes.txt")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("Plain text note\r\nSecond line\n")

            knowledge_base = KnowledgeBase()
            importer = DocumentKnowledgeImporter()
            record = importer.import_document(file_path, knowledge_base)

            self.assertEqual(record.source_type, "txt")
            self.assertEqual(record.content, "Plain text note\nSecond line")
            self.assertEqual(len(knowledge_base.records), 1)
            self.assertEqual(len(knowledge_base.long_term_memory), 0)


if __name__ == "__main__":
    unittest.main()
