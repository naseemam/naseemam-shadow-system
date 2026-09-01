"""Persistent goals and proactive next-task generation for Ameer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PersistentGoal:
    goal_id: str
    statement: str
    status: str = "active"
    completion_criteria: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    current_blocker: Optional[str] = None

    def complete(self) -> bool:
        return self.status == "complete"


def proactive_task_policy():
    return {
        "persistent_goal_survives_chat_turns": True,
        "persistent_goal_survives_restart_when_persisted": True,
        "goal_remains_active_until_completion_criteria_met_or_founder_cancels": True,
        "proactive_task_generator_enabled": True,
        "generator_may_propose_next_step": True,
        "generator_may_create_operational_tasks": True,
        "generator_must_preserve_original_goal": True,
        "sensitive_execution_still_uses_sovereign_gate_policy": True,
        "routine_execution_does_not_require_restatement_each_day": True,
    }
