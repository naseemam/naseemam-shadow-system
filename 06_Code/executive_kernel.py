"""
executive_kernel.py
===================
Transport-agnostic executive kernel for conversation and execution entry points.

This module centralizes the shared orchestration + executive brain flow so
HTTP, CLI, plugins, and future interfaces can reuse the same business logic.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List


class ExecutiveKernel:
    """Shared execution/conversation kernel used by multiple transports."""

    def __init__(
        self,
        documents: List[Dict[str, str]],
        orchestrator: Any,
        executive_brain: Any,
        task_batch_builder: Callable[[str, Any | None], Dict[str, Any]] | None = None,
    ) -> None:
        self.documents = documents
        self.orchestrator = orchestrator
        self.executive_brain = executive_brain
        self.task_batch_builder = task_batch_builder

    def analyze(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        orchestrator_result = self.orchestrator.answer(query, max_results)
        if not self.executive_brain:
            raise RuntimeError("Executive Brain is unavailable")

        guardian = orchestrator_result.get("guardian", {})
        routing = orchestrator_result.get("routing") or {}
        plan = self.executive_brain.think(
            query,
            self.documents,
            guardian_result=guardian,
            routing_hint=routing,
        )
        return {
            "orchestrator_result": orchestrator_result,
            "guardian": guardian,
            "routing": routing,
            "plan": plan,
        }

    def execute_task(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if self.task_batch_builder is None:
            raise RuntimeError("Task batch builder is unavailable")

        analysis = self.analyze(query, max_results=max_results)
        analysis["task_batch"] = self.task_batch_builder(query, plan=analysis["plan"])
        return analysis