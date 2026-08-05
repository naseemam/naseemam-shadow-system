from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import os
import re
import uuid

from knowledge_engine.interfaces import KnowledgeBase, KnowledgeRecord, KnowledgeState
from knowledge_engine.validation import KnowledgeValidationLayer

try:
    from github_connector.connector import GitHubConnector
except Exception:  # pragma: no cover - fallback when package context is missing
    GitHubConnector = None  # type: ignore[assignment]

try:
    from railway_connector.connector import RailwayConnector
except Exception:  # pragma: no cover - fallback when package context is missing
    RailwayConnector = None  # type: ignore[assignment]

try:
    from tool_bus.bus import ExecutiveToolBus, ToolInvocation
except Exception:  # pragma: no cover - fallback when package context is missing
    ExecutiveToolBus = None  # type: ignore[assignment]
    ToolInvocation = None  # type: ignore[assignment]


class DocumentApprovalStatus(str, Enum):
    PENDING = "pending"
    TRUSTED = "trusted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class DocumentCatalogEntry:
    document_id: str
    title: str
    source: str
    category: str
    language: str
    created_date: str
    imported_date: str
    approval_status: str
    confidence_score: float
    tags: List[str] = field(default_factory=list)
    content: str = ""
    source_type: str = ""


class DocumentLibraryService:
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None, validation_layer: Optional[KnowledgeValidationLayer] = None) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.validation_layer = validation_layer or KnowledgeValidationLayer()
        self._documents: Dict[str, DocumentCatalogEntry] = {}
        self._catalog: List[DocumentCatalogEntry] = []
        self._github_connector: Optional[Any] = None
        self._railway_connector: Optional[Any] = None
        self._tool_bus: Optional[Any] = None

    def register_document(
        self,
        file_path: str,
        title: Optional[str] = None,
        source: str = "local",
        category: str = "general",
        language: str = "en",
        tags: Optional[List[str]] = None,
        approval_status: str = "pending",
    ) -> DocumentCatalogEntry:
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        extension = os.path.splitext(file_path)[1].lower()
        if extension not in {".md", ".txt", ".pdf", ".docx"}:
            raise ValueError(f"Unsupported document type: {extension}")

        document_id = str(uuid.uuid4())
        created_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        imported_date = created_date
        requested_title = title or os.path.basename(file_path)
        content = self._read_content(file_path)

        entry = DocumentCatalogEntry(
            document_id=document_id,
            title=requested_title,
            source=source,
            category=category,
            language=language,
            created_date=created_date,
            imported_date=imported_date,
            approval_status=approval_status,
            confidence_score=0.0,
            tags=list(tags or []),
            content=content,
            source_type=extension,
        )

        if approval_status == "trusted":
            entry.confidence_score = 0.95
        elif approval_status == "rejected":
            entry.confidence_score = 0.1
        else:
            entry.confidence_score = 0.7

        self._documents[document_id] = entry
        self._catalog.append(entry)

        knowledge_record = KnowledgeRecord(
            source_path=file_path,
            content=content,
            source_type=self._source_type_for_extension(extension),
            state=KnowledgeState.PENDING_APPROVAL,
            approval_state=KnowledgeState.PENDING_APPROVAL,
            confidence_score=entry.confidence_score,
            import_timestamp=imported_date,
            provenance={
                "document_id": document_id,
                "title": requested_title,
                "source": source,
                "category": category,
                "tags": list(tags or []),
                "language": language,
            },
            source_category=category,
        )
        if approval_status == "trusted":
            self.validation_layer.approve(knowledge_record)
        elif approval_status == "rejected":
            self.validation_layer.reject(knowledge_record)
        self.knowledge_base.add_record(knowledge_record)
        return entry

    def list_documents(self) -> List[DocumentCatalogEntry]:
        return list(self._catalog)

    def search(self, query: str) -> List[DocumentCatalogEntry]:
        if not query:
            return self.list_documents()
        query_lower = query.lower()
        tokens = {token for token in re.split(r"[^a-z0-9]+", query_lower) if token}
        def matches(entry: DocumentCatalogEntry) -> bool:
            searchable_fields = [entry.title.lower(), entry.content.lower(), " ".join(entry.tags).lower()]
            return any(token in field for token in tokens for field in searchable_fields)

        results = [entry for entry in self._catalog if matches(entry)]
        if results:
            return results
        self._hydrate_from_github(query_lower)
        return [entry for entry in self._catalog if matches(entry)]

    def filter_documents(self, category: Optional[str] = None, source: Optional[str] = None, approval_status: Optional[str] = None, tags: Optional[List[str]] = None) -> List[DocumentCatalogEntry]:
        results = list(self._catalog)
        if category:
            results = [entry for entry in results if entry.category == category]
        if source:
            results = [entry for entry in results if entry.source == source]
        if approval_status:
            results = [entry for entry in results if entry.approval_status == approval_status]
        if tags:
            tag_set = {tag.lower() for tag in tags}
            results = [entry for entry in results if tag_set.intersection({tag.lower() for tag in entry.tags})]
        return results

    def attach_github_connector(self, connector: Any) -> None:
        self._github_connector = connector
        connector.library = self

    def attach_railway_connector(self, connector: Any) -> None:
        self._railway_connector = connector
        connector.library = self

    def attach_tool_bus(self, tool_bus: Any) -> None:
        self._tool_bus = tool_bus

    def get_trusted_documents(self) -> List[DocumentCatalogEntry]:
        if not self._catalog and self._github_connector is not None:
            self._hydrate_from_github("")
        return [entry for entry in self._catalog if entry.approval_status == "trusted"]

    def _hydrate_from_github(self, query: str) -> None:
        if self._tool_bus is not None:
            query_lower = (query or "").lower()
            if "pull request" in query_lower or "pr" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="pull_request.list", payload={"owner": "example", "repo": "repo"}))
            elif "release" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="release.list", payload={"owner": "example", "repo": "repo"}))
            elif "workflow" in query_lower or "action" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="workflow.list", payload={"owner": "example", "repo": "repo"}))
            elif "issue" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="issue.list", payload={"owner": "example", "repo": "repo"}))
            elif "branch" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="branch.list", payload={"owner": "example", "repo": "repo"}))
            elif "repository" in query_lower or "repo" in query_lower or "github" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="repository.discovery", payload={"owner": "example", "repo": "repo"}))
            elif "health" in query_lower or "service" in query_lower or "deployment" in query_lower or "log" in query_lower or "metric" in query_lower or "railway" in query_lower:
                result = self._tool_bus.route(ToolInvocation(capability="service.health", payload={"project": "acme", "service": "api", "environment": "production"}))
            else:
                result = self._tool_bus.route(ToolInvocation(capability="repository.discovery", payload={"owner": "example", "repo": "repo"}))
            if result and getattr(result, "success", False):
                for entry in result.data.get("entries", []) or []:
                    document_entry = DocumentCatalogEntry(
                        document_id=entry.get("document_id", str(uuid.uuid4())),
                        title=entry.get("title", ""),
                        source=entry.get("source", "github"),
                        category=entry.get("category", "github"),
                        language="en",
                        created_date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        imported_date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        approval_status=entry.get("approval_status", "trusted"),
                        confidence_score=0.95,
                        tags=list(entry.get("tags", [])),
                        content=entry.get("content", ""),
                        source_type="github",
                    )
                    self._documents[document_entry.document_id] = document_entry
                    self._catalog.append(document_entry)
                return

        if self._github_connector is None and self._railway_connector is None:
            return

        query_lower = (query or "").lower()
        if "pull request" in query_lower or "pr" in query_lower:
            if self._github_connector is not None:
                self._github_connector.retrieve_pull_requests()
            return
        if "release" in query_lower:
            if self._github_connector is not None:
                self._github_connector.retrieve_releases()
            return
        if "workflow" in query_lower or "action" in query_lower:
            if self._github_connector is not None:
                self._github_connector.retrieve_workflows()
            return
        if "issue" in query_lower:
            if self._github_connector is not None:
                self._github_connector.retrieve_issues()
            return
        if "branch" in query_lower:
            if self._github_connector is not None:
                self._github_connector.retrieve_branches()
            return
        if "repository" in query_lower or "repo" in query_lower or "github" in query_lower:
            if self._github_connector is not None:
                self._github_connector.discover_repository()
            return
        if any(token in query_lower for token in ["health", "deployment", "log", "metric", "railway", "service"]):
            if self._railway_connector is not None:
                if "deployment" in query_lower and "history" in query_lower:
                    self._railway_connector.retrieve_deployment_history()
                elif "deployment" in query_lower:
                    self._railway_connector.retrieve_latest_deployment()
                elif "log" in query_lower:
                    self._railway_connector.retrieve_logs()
                elif "metric" in query_lower:
                    self._railway_connector.retrieve_metrics()
                else:
                    self._railway_connector.retrieve_service_health()
            return
        if self._github_connector is not None:
            self._github_connector.discover_repository()

    def _read_content(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read()

    def _source_type_for_extension(self, extension: str) -> str:
        mapping = {".md": "markdown", ".txt": "txt", ".pdf": "pdf", ".docx": "docx"}
        return mapping.get(extension, "unknown")
