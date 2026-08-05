import os
from datetime import datetime, timezone
from typing import Optional

from .interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState
from .validation import KnowledgeValidationLayer


class DocumentKnowledgeImporter:
    def __init__(self) -> None:
        self.supported_extensions = {".md": "markdown", ".txt": "txt"}
        self.validation_layer = KnowledgeValidationLayer()

    def import_document(
        self,
        file_path: str,
        knowledge_base: Optional[KnowledgeBase] = None,
        source_category: str = "imported_local",
    ) -> KnowledgeRecord:
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        extension = os.path.splitext(file_path)[1].lower()
        source_type = self.supported_extensions.get(extension)
        if source_type is None:
            raise ValueError(f"Unsupported document type: {extension}")

        with open(file_path, "r", encoding="utf-8") as handle:
            raw_content = handle.read()

        normalized_content = self._normalize_content(raw_content)
        record = KnowledgeRecord(
            source_path=file_path,
            content=normalized_content,
            source_type=source_type,
            state=KnowledgeState.IMPORTED,
            approval_state=KnowledgeState.IMPORTED,
            source_category=source_category,
            provenance={
                "source_path": file_path,
                "source_type": source_type,
                "imported_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        record.state = KnowledgeState.PARSED
        record.approval_state = KnowledgeState.PENDING_APPROVAL
        record.state = KnowledgeState.NORMALIZED
        record.state = KnowledgeState.PENDING_APPROVAL
        record.import_timestamp = record.provenance["imported_at"]
        self.validation_layer.assign_confidence(record, source_category=source_category)
        self.validation_layer.mark_pending_approval(record)

        if knowledge_base is not None:
            knowledge_base.add_record(record)

        return record

    def _normalize_content(self, content: str) -> str:
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in normalized.split("\n")]

        while lines and lines[0].strip() == "":
            lines.pop(0)
        while lines and lines[-1].strip() == "":
            lines.pop()

        cleaned_lines = []
        for line in lines:
            if line.strip() != "":
                cleaned_lines.append(line)

        if len(cleaned_lines) > 1:
            if cleaned_lines[0].startswith("#"):
                return "\n".join(cleaned_lines[:1] + [""] + cleaned_lines[1:])
            return "\n".join(cleaned_lines)
        return "\n".join(cleaned_lines)
