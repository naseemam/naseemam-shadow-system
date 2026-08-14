"""
goal_state_store.py
===================
Persistent Goal State Store — دائمة الحالة لأهداف الوكيل الذاتي.

يحفظ حالة كل هدف على القرص بصيغة JSON حتى يمكن استئناف التنفيذ
بعد انتهاء الجلسة أو بعد موافقة المؤسس (Founder approval).

الحالات المدعومة:
    PLANNING              — الوكيل يخطط
    EXECUTING             — الوكيل ينفذ
    VERIFYING             — الوكيل يتحقق من الإنجاز
    WAITING_FOR_APPROVAL  — في انتظار موافقة المؤسس
    COMPLETED             — اكتمل بنجاح
    FAILED                — فشل نهائي
    NEEDS_FOUNDER_ATTENTION — يحتاج تدخلًا يدويًا

الاستخدام:
    store = GoalStateStore(workspace_root)
    goal_id = store.create(goal="...", plan={...})
    store.update(goal_id, status=GoalStatus.EXECUTING, current_task="task-1")
    state = store.get(goal_id)
    store.resume_goal(goal_id, approval_id="appr-abc")
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class GoalStatus(str, Enum):
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_FOUNDER_ATTENTION = "NEEDS_FOUNDER_ATTENTION"


class GoalStateStore:
    """
    Persistent store for autonomous agent goal state.

    Each goal is stored as a JSON file under:
        <workspace_root>/.ameer/goals/<goal_id>.json

    Thread-safe: all mutations use a per-instance lock.
    """

    _GOALS_SUBDIR = Path(".ameer") / "goals"

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._goals_dir = self._root / self._GOALS_SUBDIR
        self._goals_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def create(
        self,
        goal: str,
        plan: Optional[Dict[str, Any]] = None,
        goal_id: Optional[str] = None,
    ) -> str:
        """
        Create a new goal state record.

        Returns the new goal_id.
        """
        gid = goal_id or str(uuid.uuid4())
        now = _now_iso()
        state: Dict[str, Any] = {
            "goal_id": gid,
            "goal": goal,
            "plan": plan or {},
            "completed_tasks": [],
            "failed_tasks": [],
            "current_task": None,
            "observations": [],
            "retries": {},
            "pending_external_action": None,
            "approval_id": None,
            "status": GoalStatus.PLANNING,
            "created_at": now,
            "updated_at": now,
        }
        self._write(gid, state)
        return gid

    def get(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Return the goal state dict, or None if not found."""
        path = self._goal_path(goal_id)
        if not path.exists():
            return None
        try:
            with self._lock:
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def update(self, goal_id: str, **fields: Any) -> bool:
        """
        Update one or more fields of an existing goal state.

        Allowed fields match the schema keys.  ``status`` accepts either a
        :class:`GoalStatus` value or a plain string (validated against the enum).
        Returns True on success, False if the goal does not exist.
        """
        with self._lock:
            path = self._goal_path(goal_id)
            if not path.exists():
                return False
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return False

            # Coerce status to its string value
            if "status" in fields:
                raw_status = fields["status"]
                if isinstance(raw_status, GoalStatus):
                    fields["status"] = raw_status.value
                else:
                    # Validate it is a known status
                    try:
                        fields["status"] = GoalStatus(str(raw_status)).value
                    except ValueError:
                        pass  # keep unknown string as-is

            state.update(fields)
            state["updated_at"] = _now_iso()
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            return True

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all goal states sorted by created_at descending."""
        states = []
        with self._lock:
            for p in sorted(self._goals_dir.glob("*.json"), key=lambda x: x.name):
                try:
                    states.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception:
                    continue
        states.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        return states

    def resume_goal(
        self,
        goal_id: str,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resume execution of a goal after Founder approval.

        Behaviour:
        - Loads the current goal state.
        - If approval_id is provided, stores it and clears pending_external_action.
        - Transitions status from WAITING_FOR_APPROVAL → EXECUTING.
        - Does NOT reset completed_tasks or re-plan from scratch.
        - Returns the updated state dict (or an error dict on failure).
        """
        state = self.get(goal_id)
        if state is None:
            return {"error": "goal_not_found", "goal_id": goal_id}

        updates: Dict[str, Any] = {
            "status": GoalStatus.EXECUTING,
        }

        if approval_id is not None:
            updates["approval_id"] = approval_id
            updates["pending_external_action"] = None

        elif state.get("status") == GoalStatus.WAITING_FOR_APPROVAL:
            # Resume without explicit approval_id — allow if already approved elsewhere
            pass

        self.update(goal_id, **updates)
        updated_state = self.get(goal_id)
        return updated_state or {}

    def mark_waiting_for_approval(
        self,
        goal_id: str,
        pending_action: Optional[Dict[str, Any]] = None,
        approval_id: Optional[str] = None,
    ) -> bool:
        """Transition goal to WAITING_FOR_APPROVAL and record the pending action."""
        return self.update(
            goal_id,
            status=GoalStatus.WAITING_FOR_APPROVAL,
            pending_external_action=pending_action,
            approval_id=approval_id,
        )

    def mark_completed(self, goal_id: str, summary: str = "") -> bool:
        """Mark goal as COMPLETED."""
        return self.update(goal_id, status=GoalStatus.COMPLETED, observations=[summary] if summary else [])

    def mark_failed(self, goal_id: str, reason: str = "") -> bool:
        """Mark goal as FAILED."""
        return self.update(goal_id, status=GoalStatus.FAILED, observations=[reason] if reason else [])

    # ── Internal ──────────────────────────────────────────────────────────────

    def _goal_path(self, goal_id: str) -> Path:
        # Sanitise goal_id to prevent path traversal
        safe = "".join(c for c in goal_id if c.isalnum() or c in "-_")
        return self._goals_dir / f"{safe}.json"

    def _write(self, goal_id: str, state: Dict[str, Any]) -> None:
        with self._lock:
            path = self._goal_path(goal_id)
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
