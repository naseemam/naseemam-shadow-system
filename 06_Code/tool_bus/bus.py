from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tool_bus.interfaces import ExternalTool, ToolContext


@dataclass
class ToolInvocation:
    capability: str
    payload: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ToolContext] = None


@dataclass
class ToolResult:
    tool_name: str
    capability: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ExecutiveToolBus:
    def __init__(self) -> None:
        self._tools: Dict[str, ExternalTool] = {}
        self._capability_index: Dict[str, str] = {}

    def register_tool(self, tool: ExternalTool) -> None:
        if not tool.name:
            raise ValueError("Tool must provide a name")
        self._tools[tool.name] = tool
        for capability in getattr(tool, "supports", []) or []:
            self._capability_index[capability] = tool.name

    def route(self, invocation: ToolInvocation) -> ToolResult:
        tool_name = self._capability_index.get(invocation.capability)
        if not tool_name:
            return ToolResult(tool_name="", capability=invocation.capability, success=False, error="No tool registered")
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(tool_name=tool_name, capability=invocation.capability, success=False, error="Tool not found")
        if not getattr(tool, "read_only", True):
            return ToolResult(tool_name=tool_name, capability=invocation.capability, success=False, error="Write operations are not allowed")
        try:
            data = tool.invoke(invocation.capability, invocation.payload, invocation.context)
        except Exception as exc:  # pragma: no cover - defensive path
            return ToolResult(tool_name=tool_name, capability=invocation.capability, success=False, error=str(exc))
        return ToolResult(tool_name=tool_name, capability=invocation.capability, success=True, data=data)

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def list_capabilities(self) -> List[str]:
        return sorted(self._capability_index.keys())
