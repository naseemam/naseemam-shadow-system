from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from document_library.service import DocumentCatalogEntry, DocumentLibraryService


@dataclass
class RailwayConnector:
    client: Any
    project: str
    service: str
    environment: str
    library: Optional[DocumentLibraryService] = None
    read_only: bool = True

    def __post_init__(self) -> None:
        if self.library is None:
            self.library = DocumentLibraryService()

    def retrieve_service_health(self) -> List[DocumentCatalogEntry]:
        payload = self.client.get_service_health(self.project, self.service, self.environment)
        entry = self._normalize_to_entry(
            title=f"Railway health: {self.service}",
            content=self._format_health_content(payload),
            category="service_health",
            source="railway",
            source_type="service_health",
            timestamp=payload.get("timestamp") or self._now(),
            approval_status="trusted",
            tags=["railway", "health", self.environment],
        )
        self._register_entry(entry)
        return [entry]

    def retrieve_latest_deployment(self) -> List[DocumentCatalogEntry]:
        payload = self.client.get_latest_deployment(self.project, self.service, self.environment)
        entry = self._normalize_to_entry(
            title=f"Railway deployment: {payload.get('version', 'unknown')}",
            content=self._format_deployment_content(payload),
            category="deployment",
            source="railway",
            source_type="deployment",
            timestamp=payload.get("timestamp") or self._now(),
            approval_status="trusted",
            tags=["railway", "deployment", self.environment],
        )
        self._register_entry(entry)
        return [entry]

    def retrieve_deployment_history(self) -> List[DocumentCatalogEntry]:
        payload = self.client.get_deployment_history(self.project, self.service, self.environment)
        entries: List[DocumentCatalogEntry] = []
        for item in payload or []:
            entry = self._normalize_to_entry(
                title=f"Railway deployment history: {item.get('version', 'unknown')}",
                content=self._format_deployment_content(item),
                category="deployment_history",
                source="railway",
                source_type="deployment_history",
                timestamp=item.get("timestamp") or self._now(),
                approval_status="trusted",
                tags=["railway", "deployment_history", self.environment],
            )
            self._register_entry(entry)
            entries.append(entry)
        return entries

    def retrieve_logs(self) -> List[DocumentCatalogEntry]:
        payload = self.client.get_logs(self.project, self.service, self.environment)
        entries: List[DocumentCatalogEntry] = []
        for item in payload or []:
            entry = self._normalize_to_entry(
                title="Railway log",
                content=self._format_log_content(item),
                category="logs",
                source="railway",
                source_type="logs",
                timestamp=item.get("timestamp") or self._now(),
                approval_status="trusted",
                tags=["railway", "logs", self.environment],
            )
            self._register_entry(entry)
            entries.append(entry)
        return entries

    def retrieve_metrics(self) -> List[DocumentCatalogEntry]:
        payload = self.client.get_metrics(self.project, self.service, self.environment)
        entries: List[DocumentCatalogEntry] = []
        metric_items = [
            ("CPU usage", payload.get("cpu_usage")),
            ("Memory usage", payload.get("memory_usage")),
            ("Error rate", payload.get("error_rate")),
            ("Response time", payload.get("response_time_ms")),
        ]
        for title, value in metric_items:
            if value is None:
                continue
            entry = self._normalize_to_entry(
                title=f"Railway metric: {title}",
                content=f"{title}: {value}",
                category="metrics",
                source="railway",
                source_type="metrics",
                timestamp=payload.get("timestamp") or self._now(),
                approval_status="trusted",
                tags=["railway", "metrics", self.environment],
            )
            self._register_entry(entry)
            entries.append(entry)
        return entries

    def _normalize_to_entry(
        self,
        title: str,
        content: str,
        category: str,
        source: str,
        source_type: str,
        timestamp: str,
        approval_status: str,
        tags: List[str],
    ) -> DocumentCatalogEntry:
        return DocumentCatalogEntry(
            document_id=f"railway:{self.project}:{self.service}:{self.environment}:{category}:{title}",
            title=title,
            source=source,
            category=category,
            language="en",
            created_date=timestamp,
            imported_date=timestamp,
            approval_status=approval_status,
            confidence_score=0.95,
            tags=tags,
            content=self._decorate_with_provenance(content),
            source_type=source_type,
        )

    def _decorate_with_provenance(self, content: str) -> str:
        provenance = [
            f"Project: {self.project}",
            f"Service: {self.service}",
            f"Environment: {self.environment}",
            f"Timestamp: {self._now()}",
        ]
        return f"{content}\n\nProvenance: {' | '.join(provenance)}"

    def _register_entry(self, entry: DocumentCatalogEntry) -> None:
        if self.library is None:
            return
        self.library._catalog.append(entry)
        self.library._documents[entry.document_id] = entry

    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _format_health_content(self, payload: Dict[str, Any]) -> str:
        return f"Status: {payload.get('status', 'unknown')} | Health score: {payload.get('health_score', 'unknown')}"

    def _format_deployment_content(self, payload: Dict[str, Any]) -> str:
        return f"Version: {payload.get('version', 'unknown')} | Status: {payload.get('status', 'unknown')}"

    def _format_log_content(self, payload: Dict[str, Any]) -> str:
        return f"Log: {payload.get('message', 'unknown')}"
