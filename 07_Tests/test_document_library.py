import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from document_library.service import DocumentLibraryService
from knowledge_engine.interfaces import KnowledgeBase

MODULE_PATH = os.path.join(CODE_ROOT, "executive_brain.py")
SPEC = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["executive_brain"] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain


class DocumentLibraryTests(unittest.TestCase):
    def test_register_and_list_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_path = os.path.join(temp_dir, "guide.md")
            with open(doc_path, "w", encoding="utf-8") as handle:
                handle.write("# Guide\n\nThis is a trusted guide.\n")

            library = DocumentLibraryService(knowledge_base=KnowledgeBase())
            entry = library.register_document(doc_path, title="Guide", source="project", category="vision", language="en", tags=["product", "strategy"], approval_status="trusted")

            self.assertEqual(entry.title, "Guide")
            self.assertEqual(len(library.list_documents()), 1)
            self.assertEqual(library.list_documents()[0].document_id, entry.document_id)

    def test_filtering_and_search_are_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_path = os.path.join(temp_dir, "note.txt")
            with open(doc_path, "w", encoding="utf-8") as handle:
                handle.write("A note about priorities.\n")

            library = DocumentLibraryService(knowledge_base=KnowledgeBase())
            library.register_document(doc_path, title="Note", source="founder", category="principles", language="en", tags=["priority"], approval_status="trusted")

            filtered = library.filter_documents(category="principles", source="founder", approval_status="trusted", tags=["priority"])
            searched = library.search("priorities")

            self.assertEqual(len(filtered), 1)
            self.assertEqual(searched[0].title, "Note")

    def test_trusted_documents_are_visible_and_brain_uses_library_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_path = os.path.join(temp_dir, "doc.md")
            with open(doc_path, "w", encoding="utf-8") as handle:
                handle.write("Executive content.\n")

            library = DocumentLibraryService(knowledge_base=KnowledgeBase())
            library.register_document(doc_path, title="Doc", source="project", category="mission", language="en", tags=["executive"], approval_status="trusted")

            brain = ExecutiveBrain(normalize_fn=lambda x: x, document_library=library)
            plan = brain.think("What documents are trusted?", [], guardian_result={"status": "pass", "reason": ""})

            self.assertIn("Doc", plan.context_summary)
            self.assertEqual(len(library.get_trusted_documents()), 1)


if __name__ == "__main__":
    unittest.main()
