from __future__ import annotations

from enum import Enum
from typing import List, Optional

from knowledge_engine.interfaces import KnowledgeRecord, KnowledgeState


class FounderKnowledgeCategory(str, Enum):
    VISION = "vision"
    MISSION = "mission"
    PRINCIPLES = "principles"
    BUSINESS_RULES = "business_rules"
    LONG_TERM_GOALS = "long_term_goals"
    STRATEGIC_DECISIONS = "strategic_decisions"
    PERMANENT_PREFERENCES = "permanent_preferences"


class FounderIntelligenceLayer:
    def __init__(self, approved_records: Optional[List[KnowledgeRecord]] = None) -> None:
        self.records = list(approved_records or [])
        self.calls: List[str] = []

    def retrieve(self, query: str) -> List[KnowledgeRecord]:
        self.calls.append(query)
        results: List[KnowledgeRecord] = []
        for record in self.records:
            if not self._is_approved(record):
                continue
            if self._matches_query(record, query):
                results.append(record)
        return results

    def _is_approved(self, record: KnowledgeRecord) -> bool:
        return record.state == KnowledgeState.TRUSTED and record.approval_state == KnowledgeState.TRUSTED

    def _matches_query(self, record: KnowledgeRecord, query: str) -> bool:
        normalized_query = (query or "").lower()
        normalized_content = (record.content or "").lower()
        if not normalized_query:
            return False
        if any(token in normalized_query for token in ["vision", "mission", "principle", "priority", "strategy", "goal", "preference", "rule", "decision", "founder"]):
            return any(token in normalized_content for token in ["vision", "mission", "principle", "priority", "strategy", "goal", "preference", "rule", "decision", "founder"])
        return normalized_query in normalized_content or normalized_content in normalized_query
