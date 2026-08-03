from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AgentContext:
    query: str
    intent: str
    route: Dict
    results: List[Dict[str, str | int]]
    execution_plan: Dict
    conversation_state: Dict
    active_goal: str | None


@dataclass
class AgentOutput:
    agent: str
    confidence: float
    reply_draft: str
    sources: List[str]
    actions: List[str]
    message: str


class BaseAgent:
    name = "base_agent"
    capabilities: List[str] = []
    primary_sources: List[str] = []

    def execute(self, context: AgentContext) -> AgentOutput:
        raise NotImplementedError

    def _top_result(self, results: List[Dict[str, str | int]], excerpt_chars: int = 220) -> tuple[str, str]:
        if not results:
            return "", ""
        top = results[0]
        path = str(top.get("path", "مصدر غير محدد"))
        excerpt = top.get("excerpt", "")
        excerpt_text = excerpt.strip() if isinstance(excerpt, str) else ""
        return path, excerpt_text[:excerpt_chars]
