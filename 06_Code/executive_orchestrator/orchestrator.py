from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExecutiveContext:
    route: str
    source: str
    capability: Optional[str] = None
    excerpts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutiveOrchestrator:
    def __init__(
        self,
        founder_intelligence: Optional[Any] = None,
        knowledge_gateway: Optional[Any] = None,
        document_library: Optional[Any] = None,
        tool_bus: Optional[Any] = None,
    ) -> None:
        self._founder_intelligence = founder_intelligence
        self._knowledge_gateway = knowledge_gateway
        self._document_library = document_library
        self._tool_bus = tool_bus

    def orchestrate(self, request: str, context: Optional[Dict[str, Any]] = None) -> ExecutiveContext:
        normalized = (request or "").lower()
        context = context or {}

        if self._is_founder_query(normalized):
            excerpts = []
            if self._founder_intelligence is not None:
                try:
                    records = self._founder_intelligence.retrieve(request)
                    excerpts = []
                    for item in records or []:
                        if isinstance(item, dict):
                            content = item.get("content")
                            if content:
                                excerpts.append(str(content))
                        else:
                            content = getattr(item, "content", None)
                            if content:
                                excerpts.append(str(content))
                except Exception:
                    excerpts = []
            return ExecutiveContext(route="founder_intelligence", source="founder_intelligence", excerpts=excerpts, metadata={"request": request, "context": context})

        if self._is_project_knowledge_query(normalized):
            excerpts = []
            if self._knowledge_gateway is not None:
                try:
                    records = self._knowledge_gateway.retrieve(request)
                    excerpts = [str(item.get("content", "")) for item in records if isinstance(item, dict) and item.get("content")]
                except Exception:
                    excerpts = []
            return ExecutiveContext(route="knowledge_engine", source="knowledge_engine", excerpts=excerpts, metadata={"request": request, "context": context})

        if self._is_document_query(normalized):
            excerpts = []
            if self._document_library is not None:
                try:
                    results = self._document_library.search(request)
                    excerpts = [f"{getattr(item, 'title', '')}: {getattr(item, 'content', '')}" for item in results if getattr(item, 'title', None)]
                except Exception:
                    excerpts = []
            return ExecutiveContext(route="document_library", source="document_library", excerpts=excerpts, metadata={"request": request, "context": context})

        if self._is_github_query(normalized):
            if self._tool_bus is not None:
                invocation = self._build_invocation("github", request)
                result = self._tool_bus.route(invocation)
                return ExecutiveContext(route="github_tool", source="github_tool", capability=invocation.capability, excerpts=[item.get("title", "") for item in (getattr(result, "data", {}).get("entries", []) or []) if isinstance(item, dict)], metadata={"request": request, "context": context})
            return ExecutiveContext(route="github_tool", source="github_tool", capability="pull_request.list", metadata={"request": request, "context": context})

        if self._is_railway_query(normalized):
            if self._tool_bus is not None:
                invocation = self._build_invocation("railway", request)
                result = self._tool_bus.route(invocation)
                return ExecutiveContext(route="railway_tool", source="railway_tool", capability=invocation.capability, excerpts=[item.get("title", "") for item in (getattr(result, "data", {}).get("entries", []) or []) if isinstance(item, dict)], metadata={"request": request, "context": context})
            return ExecutiveContext(route="railway_tool", source="railway_tool", capability="service.health", metadata={"request": request, "context": context})

        return ExecutiveContext(route="fallback", source="fallback", metadata={"request": request, "context": context})

    def _is_founder_query(self, normalized: str) -> bool:
        return self._contains_any(normalized, ["founder", "vision", "mission", "principle", "strategy", "goal", "preference", "decision", "founder's", "founder’s"])

    def _is_project_knowledge_query(self, normalized: str) -> bool:
        return self._contains_any(normalized, ["project", "knowledge", "launch", "roadmap", "architecture", "requirement", "plan", "project knowledge"])

    def _is_document_query(self, normalized: str) -> bool:
        return self._contains_any(normalized, ["document", "documents", "library", "catalog", "trusted", "approval", "approved", "file", "files", "what documents"])

    def _is_github_query(self, normalized: str) -> bool:
        return self._contains_any(normalized, ["pull request", "release", "workflow", "issue", "branch", "repository", "repo", "github", "pr #"])

    def _is_railway_query(self, normalized: str) -> bool:
        return self._contains_any(normalized, ["railway", "service", "health", "deployment", "deploy", "log", "logs", "metric", "metrics", "production service"])

    def _contains_any(self, normalized: str, tokens: List[str]) -> bool:
        normalized = (normalized or "").lower()
        for token in tokens:
            if (token or "").strip().lower() in normalized:
                return True
        return False

    def _build_invocation(self, provider: str, request: str):
        from tool_bus.bus import ToolInvocation

        normalized = (request or "").lower()
        if provider == "github":
            if "pull request" in normalized or "pr" in normalized:
                capability = "pull_request.list"
            elif "release" in normalized:
                capability = "release.list"
            elif "workflow" in normalized or "action" in normalized:
                capability = "workflow.list"
            elif "issue" in normalized:
                capability = "issue.list"
            elif "branch" in normalized:
                capability = "branch.list"
            else:
                capability = "repository.discovery"
            return ToolInvocation(capability=capability, payload={"owner": "example", "repo": "repo"})

        if "health" in normalized or "service" in normalized:
            capability = "service.health"
        elif "deployment" in normalized:
            capability = "deployment.latest"
        elif "log" in normalized or "logs" in normalized:
            capability = "logs.list"
        elif "metric" in normalized or "metrics" in normalized:
            capability = "metrics.list"
        else:
            capability = "service.health"

        return ToolInvocation(capability=capability, payload={"project": "acme", "service": "api", "environment": "production"})
