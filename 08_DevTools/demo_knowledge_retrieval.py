import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from knowledge_engine.interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState
from knowledge_engine.retrieval import KnowledgeRetrievalEngine


if __name__ == "__main__":
    knowledge_base = KnowledgeBase()
    retrieval_engine = KnowledgeRetrievalEngine(knowledge_base)

    founder = KnowledgeRecord(source_path="/founder.md", content="Founder priorities: keep the product focused and pragmatic.", source_type="markdown")
    founder.state = KnowledgeState.TRUSTED
    founder.approval_state = KnowledgeState.TRUSTED
    founder.confidence_score = 0.92
    founder.provenance["priority"] = "founder"

    project = KnowledgeRecord(source_path="/project.md", content="Project context: the executive brain should stay grounded in trusted knowledge.", source_type="markdown")
    project.state = KnowledgeState.TRUSTED
    project.approval_state = KnowledgeState.TRUSTED
    project.confidence_score = 0.86
    project.provenance["priority"] = "project"

    knowledge_base.add_record(founder)
    knowledge_base.add_record(project)

    results = retrieval_engine.retrieve("trusted knowledge")
    for index, record in enumerate(results, start=1):
        print(f"{index}. {record.content}")
