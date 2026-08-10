"""
Declarative registry of the tools exposed by Ameer.

This module describes tools only.  It does not import, construct, or invoke
executors, and it does not grant permissions.  Capability and permission
decisions remain owned by the existing kernel governance components.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


_PROTECTED_FIELDS = frozenset({"capability", "action", "risk_level"})
_VALID_RISKS = frozenset({"low", "medium", "high"})
_VALID_STATUSES = frozenset({"enabled", "disabled", "experimental"})


def _immutable_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{field_name} must be a non-empty mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable metadata for one registered tool."""

    tool_name: str
    capability: str
    action: str
    risk_level: str
    input_policy: Mapping[str, Any]
    output_policy: Mapping[str, Any]
    status: str = "enabled"

    def __post_init__(self) -> None:
        for field_name in ("tool_name", "capability", "action"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.risk_level not in _VALID_RISKS:
            raise ValueError(f"risk_level must be one of {sorted(_VALID_RISKS)}")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(_VALID_STATUSES)}")
        object.__setattr__(
            self, "input_policy", _immutable_mapping(self.input_policy, "input_policy")
        )
        object.__setattr__(
            self, "output_policy", _immutable_mapping(self.output_policy, "output_policy")
        )


class ToolRegistry:
    """Closed-source, declarative registry for the initial tool set."""

    _DEFINITIONS = MappingProxyType({
        "file.read": ToolDefinition(
            tool_name="file.read",
            capability="file_operations",
            action="read",
            risk_level="low",
            input_policy={"required": ("target",), "additional": False},
            output_policy={"content": "sanitized", "metadata": "relative_path_only"},
        ),
        "file.create": ToolDefinition(
            tool_name="file.create",
            capability="file_operations",
            action="write",
            risk_level="medium",
            input_policy={"required": ("target", "content"), "additional": False},
            output_policy={"content": "metadata_only", "metadata": "relative_path_only"},
        ),
    })

    def __init__(self) -> None:
        self._definitions = MappingProxyType(dict(self._DEFINITIONS))

    def get(self, tool_name: str) -> ToolDefinition:
        """Return a registered definition or reject an unknown tool."""
        if not isinstance(tool_name, str) or tool_name not in self._definitions:
            raise KeyError(f"Tool '{tool_name}' is not registered")
        return self._definitions[tool_name]

    def resolve(self, tool_name: str, request: Mapping[str, Any] | None = None) -> ToolDefinition:
        """Resolve a tool without allowing request data to override its metadata."""
        if request is not None:
            forbidden = _PROTECTED_FIELDS.intersection(request)
            if forbidden:
                fields = ", ".join(sorted(forbidden))
                raise ValueError(f"tool metadata is registry-owned: {fields}")
        return self.get(tool_name)

    def list_tools(self) -> tuple[str, ...]:
        """Return the closed registry's tool names."""
        return tuple(self._definitions)
