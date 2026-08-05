from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolContext:
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExternalTool:
    name: str = ""
    read_only: bool = True
    supports: List[str] = field(default_factory=list)  # type: ignore[assignment]

    def __init__(self, name: str, read_only: bool = True) -> None:
        self.name = name
        self.read_only = read_only
        self.supports = []

    def register_capability(self, capability: str) -> None:
        if capability not in self.supports:
            self.supports.append(capability)

    def can_handle(self, capability: str) -> bool:
        return capability in self.supports

    def invoke(self, capability: str, payload: Dict[str, Any], context: Optional[ToolContext] = None) -> Dict[str, Any]:
        raise NotImplementedError
