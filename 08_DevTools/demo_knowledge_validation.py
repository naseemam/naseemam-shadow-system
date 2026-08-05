import os
import tempfile

from knowledge_engine.document_importer import DocumentKnowledgeImporter
from knowledge_engine.interfaces import KnowledgeBase
from knowledge_engine.validation import KnowledgeValidationLayer

with tempfile.TemporaryDirectory() as temp_dir:
    doc_path = os.path.join(temp_dir, 'sample.md')
    with open(doc_path, 'w', encoding='utf-8') as handle:
        handle.write('# Demo\n\nReview this content.\n')
    knowledge_base = KnowledgeBase()
    importer = DocumentKnowledgeImporter()
    record = importer.import_document(doc_path, knowledge_base, source_category='imported_local')
    print('initial_state=' + record.approval_state.value)
    print('initial_visible=' + str(len(knowledge_base.get_visible_records())))
    validator = KnowledgeValidationLayer()
    validator.approve(record)
    print('trusted_state=' + record.approval_state.value)
    print('trusted_visible=' + str(len(knowledge_base.get_visible_records())))
    print('executive_visible=' + str(len(knowledge_base.get_executive_brain_visible_records())))
