from __future__ import annotations

from typing import Any, Dict, Optional

from tool_bus.interfaces import ExternalTool, ToolContext


class GitHubTool(ExternalTool):
    def __init__(self, connector: Any) -> None:
        super().__init__(name="github", read_only=True)
        self.connector = connector
        self.register_capability("repository.discovery")
        self.register_capability("pull_request.list")
        self.register_capability("release.list")
        self.register_capability("workflow.list")
        self.register_capability("issue.list")
        self.register_capability("branch.list")
        self.register_capability("tag.list")

    def invoke(self, capability: str, payload: Dict[str, Any], context: Optional[ToolContext] = None) -> Dict[str, Any]:
        owner = payload.get("owner") or payload.get("repo_owner")
        repo = payload.get("repo") or payload.get("repository")
        if not owner or not repo:
            raise ValueError("owner and repo are required")

        if capability == "repository.discovery":
            entry = self.connector.discover_repository()
            return {"entries": [self._serialize(entry)]}
        if capability == "pull_request.list":
            entries = self.connector.retrieve_pull_requests()
            return {"entries": [self._serialize(entry) for entry in entries]}
        if capability == "release.list":
            entries = self.connector.retrieve_releases()
            return {"entries": [self._serialize(entry) for entry in entries]}
        if capability == "workflow.list":
            entries = self.connector.retrieve_workflows()
            return {"entries": [self._serialize(entry) for entry in entries]}
        if capability == "issue.list":
            entries = self.connector.retrieve_issues()
            return {"entries": [self._serialize(entry) for entry in entries]}
        if capability == "branch.list":
            entries = self.connector.retrieve_branches()
            return {"entries": [self._serialize(entry) for entry in entries]}
        if capability == "tag.list":
            entries = self.connector.retrieve_tags()
            return {"entries": [self._serialize(entry) for entry in entries]}
        raise ValueError(f"Unsupported capability: {capability}")

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
