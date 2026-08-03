from __future__ import annotations

from typing import Any, Dict, List


class SharedRouter:
    """Minimal shared router for module-to-module messaging via approved events."""

    def __init__(self) -> None:
        self._modules: Dict[str, object] = {}
        self.events: List[Dict[str, Any]] = []

    def register_module(self, module: object) -> None:
        name = getattr(module, "name", None)
        if not name:
            raise ValueError("module must expose a name")
        self._modules[name] = module

    def unregister_module(self, name: str) -> None:
        self._modules.pop(name, None)

    def publish(self, source: str, event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        message = {
            "source": source,
            "event": event,
            "payload": payload or {},
        }
        self.events.append(message)
        return message

    def broadcast(self, event: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [self.publish(name, event, payload) for name in list(self._modules.keys())]
