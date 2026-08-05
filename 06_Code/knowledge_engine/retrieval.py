from typing import List, Optional

from .interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState


class KnowledgeRetrievalEngine:
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase()

    def retrieve(self, question: str) -> List[KnowledgeRecord]:
        records = self.knowledge_base.get_visible_records()
        if not records:
            return []

        candidates = []
        for record in records:
            relevance = self._semantic_relevance(record.content, question)
            freshness = self._freshness_score(record)
            priority = self._priority_score(record)
            confidence = record.confidence_score
            score = (confidence * 0.4) + (relevance * 0.3) + (freshness * 0.15) + (priority * 0.15)
            candidates.append((score, record))

        candidates.sort(key=lambda item: item[0], reverse=True)
        ranked = [record for _, record in candidates]
        return self._sanitize_records(ranked)

    def _semantic_relevance(self, content: str, question: str) -> float:
        content_tokens = set(content.lower().split())
        question_tokens = set(question.lower().split())
        if not question_tokens:
            return 0.0
        overlap = len(content_tokens & question_tokens)
        return min(1.0, overlap / max(1, len(question_tokens)))

    def _freshness_score(self, record: KnowledgeRecord) -> float:
        if not record.import_timestamp:
            return 0.5
        return 0.8

    def _priority_score(self, record: KnowledgeRecord) -> float:
        priority = record.provenance.get("priority", "")
        if priority == "founder":
            return 1.0
        if priority == "project":
            return 0.8
        return 0.5

    def _sanitize_records(self, records: List[KnowledgeRecord]) -> List[KnowledgeRecord]:
        sanitized = []
        for record in records:
            if record.state != KnowledgeState.TRUSTED or record.approval_state != KnowledgeState.TRUSTED:
                continue
            sanitized.append(
                KnowledgeRecord(
                    source_path=record.source_path,
                    content=record.content,
                    source_type=record.source_type,
                    record_id=record.record_id,
                    state=KnowledgeState.TRUSTED,
                    approval_state=KnowledgeState.TRUSTED,
                    confidence_score=record.confidence_score,
                    import_timestamp=record.import_timestamp,
                    document_hash="",
                    provenance={
                        "source_path": record.source_path,
                        "source_type": record.source_type,
                        "priority": record.provenance.get("priority", "general"),
                    },
                    source_category=record.source_category,
                )
            )
        return sanitized
