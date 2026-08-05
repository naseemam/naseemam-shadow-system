from dataclasses import dataclass, field
from enum import Enum
from typing import List
import hashlib
import uuid


class KnowledgeState(str, Enum):
    IMPORTED = "imported"
    PARSED = "parsed"
    NORMALIZED = "normalized"
    PENDING_APPROVAL = "pending_approval"
    TRUSTED = "trusted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class KnowledgeRecord:
    source_path: str
    content: str
    source_type: str
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: KnowledgeState = KnowledgeState.IMPORTED
    approval_state: KnowledgeState = KnowledgeState.IMPORTED
    confidence_score: float = 0.0
    import_timestamp: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_hash: str = ""
    provenance: dict = field(default_factory=dict)
    source_category: str = "imported_local"

    def __post_init__(self) -> None:
        if not self.document_hash:
            self.document_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if not self.provenance:
            self.provenance = {"source_path": self.source_path, "source_type": self.source_type}


class KnowledgeBase:
    def __init__(self) -> None:
        self.records: List[KnowledgeRecord] = []
        self.long_term_memory: List[KnowledgeRecord] = []

    def add_record(self, record: KnowledgeRecord) -> KnowledgeRecord:
        self.records.append(record)
        return record

    def get_visible_records(self) -> List[KnowledgeRecord]:
        return [record for record in self.records if record.state == KnowledgeState.TRUSTED and record.approval_state == KnowledgeState.TRUSTED]

    def get_executive_brain_visible_records(self) -> List[KnowledgeRecord]:
        return self.get_visible_records()
