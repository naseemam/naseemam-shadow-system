from __future__ import annotations

from typing import Any, Dict, Optional

from tool_bus.interfaces import ExternalTool, ToolContext


class RailwayTool(ExternalTool):
    def __init__(self, connector: Any) -> None:
        super().__init__(name="railway", read_only=True)
        self.connector = connector
        self.register_capability("service.health")
        self.register_capability("deployment.latest")
        self.register_capability("deployment.history")
        self.register_capability("logs.list")
        self.register_capability("metrics.list")

    def invoke(self, capability: str, payload: Dict[str, Any], context: Optional[ToolContext] = None) -> Dict[str, Any]:
        project = payload.get("project") or payload.get("repo") or payload.get("owner")
        service = payload.get("service")
        environment = payload.get("environment") or payload.get("env")
        if not project or not service or not environment:
            raise ValueError("project, service, and environment are required")

        if capability == "service.health":
            entries = self.connector.retrieve_service_health()
        elif capability == "deployment.latest":
            entries = self.connector.retrieve_latest_deployment()
        elif capability == "deployment.history":
            entries = self.connector.retrieve_deployment_history()
        elif capability == "logs.list":
            entries = self.connector.retrieve_logs()
        elif capability == "metrics.list":
            entries = self.connector.retrieve_metrics()
        else:
            raise ValueError(f"Unsupported capability: {capability}")

        return {"entries": [self._serialize(entry) for entry in entries]}

    def _serialize(self, entry: Any) -> Dict[str, Any]:
        return {
            "document_id": getattr(entry, "document_id", ""),
            "title": getattr(entry, "title", ""),
            "category": getattr(entry, "category", ""),
            "content": getattr(entry, "content", ""),
            "approval_status": getattr(entry, "approval_status", ""),
            "source": getattr(entry, "source", ""),
            "tags": getattr(entry, "tags", []),
        }
