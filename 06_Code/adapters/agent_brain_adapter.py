from __future__ import annotations

from typing import Any, Dict


class AgentBrainAdapter:
    """Normalizes agent outputs into a stable payload for the Executive Brain."""

    def _read(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def prepare(self, agent_result: Any) -> Dict[str, Any]:
        return {
            "agent": self._read(agent_result, "agent", "unknown_agent"),
            "confidence": float(self._read(agent_result, "confidence", 0.0) or 0.0),
            "draft": self._read(agent_result, "reply_draft", "") or "",
            "sources": list(self._read(agent_result, "sources", []) or []),
            "actions": list(self._read(agent_result, "actions", []) or []),
            "message": self._read(agent_result, "message", "") or "",
        }
