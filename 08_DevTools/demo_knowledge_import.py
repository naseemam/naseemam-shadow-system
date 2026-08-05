import os
import tempfile

from knowledge_engine.document_importer import DocumentKnowledgeImporter
from knowledge_engine.interfaces import KnowledgeBase

with tempfile.TemporaryDirectory() as temp_dir:
    doc_path = os.path.join(temp_dir, 'sample.md')
    with open(doc_path, 'w', encoding='utf-8') as handle:
        handle.write('# Demo Note\n\nThis document was imported successfully.\n')
    knowledge_base = KnowledgeBase()
    importer = DocumentKnowledgeImporter()
    record = importer.import_document(doc_path, knowledge_base)
    print('record_id=' + record.record_id)
    print('source_type=' + record.source_type)
    print('content=' + record.content)
    print('stored_records=' + str(len(knowledge_base.records)))
    print('long_term_memory=' + str(len(knowledge_base.long_term_memory)))
