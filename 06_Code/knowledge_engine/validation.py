from typing import Optional

from .interfaces import KnowledgeRecord, KnowledgeState


class KnowledgeValidationLayer:
    def __init__(self) -> None:
        self.confidence_rules = {
            "founder": 1.0,
            "approved_project": 0.95,
            "imported_local": 0.9,
            "external_verified": 0.85,
            "generated": 0.2,
        }

    def assign_confidence(self, record: KnowledgeRecord, source_category: Optional[str] = None) -> float:
        category = source_category or record.source_category or "imported_local"
        score = self.confidence_rules.get(category, self.confidence_rules["imported_local"])
        record.confidence_score = score
        record.provenance["confidence_source"] = category
        return score

    def mark_pending_approval(self, record: KnowledgeRecord) -> KnowledgeRecord:
        record.state = KnowledgeState.PENDING_APPROVAL
        record.approval_state = KnowledgeState.PENDING_APPROVAL
        return record

    def approve(self, record: KnowledgeRecord) -> KnowledgeRecord:
        record.state = KnowledgeState.TRUSTED
        record.approval_state = KnowledgeState.TRUSTED
        return record

    def reject(self, record: KnowledgeRecord) -> KnowledgeRecord:
        record.state = KnowledgeState.REJECTED
        record.approval_state = KnowledgeState.REJECTED
        return record

    def archive(self, record: KnowledgeRecord) -> KnowledgeRecord:
        record.state = KnowledgeState.ARCHIVED
        record.approval_state = KnowledgeState.ARCHIVED
        return record
