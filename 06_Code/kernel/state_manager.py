"""
state_manager.py
================
Executive State Manager — الحالة الدائمة لأمير.

يحتفظ بكل ما يعرفه أمير وما يفعله عبر الجلسات.
الحالة تنجو من إعادة تشغيل الخادم.
أمير لا يبدأ من صفر أبدًا.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_STATE_FILENAME = "state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ExecutiveStateManager:
    """
    الحالة التنفيذية الدائمة لأمير.

    يتتبع:
    - active_goals: الأهداف النشطة
    - active_projects: المشاريع الجارية
    - pending_approvals: قرارات تنتظر موافقة المؤسسة
    - running_tasks: مهام قيد التنفيذ
    - recent_decisions: آخر القرارات المتخذة
    - executive_assessment: تقييم أمير الحالي للأولويات
    - runtime_status: صحة النظام
    - last_session_at: آخر جلسة
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._state_path = self._root / ".ameer" / _STATE_FILENAME
        self._state: Dict[str, Any] = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    # Current schema version — bump this when the state structure changes.
    SCHEMA_VERSION = 1

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                raw = self._state_path.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    self._state, _needs_persist = self._migrate(loaded)
                    if _needs_persist:
                        self._persist()
                    return
            except Exception:
                pass
        self._state = self._default_state()
        self._persist()

    def _migrate(self, state: Dict[str, Any]) -> "tuple[Dict[str, Any], bool]":
        """Migrate state from older schema versions to the current one.

        Returns ``(state, needs_persist)`` so the caller controls when to
        write to disk.  Every missing key from the default state is
        back-filled so that code can always rely on a complete, well-formed
        state dictionary.
        """
        version = state.get("schema_version", 0)

        # v0 → v1: add schema_version (all other keys were already present)
        if version < 1:
            state["schema_version"] = self.SCHEMA_VERSION
            defaults = self._default_state()
            for key, default_value in defaults.items():
                state.setdefault(key, default_value)
            return state, True

        return state, False

    def _persist(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _default_state(self) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "active_goals": [],
            "active_projects": [],
            "pending_approvals": [],
            "running_tasks": [],
            "recent_decisions": [],
            "founder_context": {},
            "executive_assessment": "",
            "runtime_status": "initializing",
            "last_session_at": None,
            "session_count": 0,
            "workspace_summary": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def mark_session_start(self) -> None:
        self._state["last_session_at"] = _now_iso()
        self._state["session_count"] = self._state.get("session_count", 0) + 1
        self._state["runtime_status"] = "running"
        self._state["updated_at"] = _now_iso()
        self._persist()

    def set_runtime_status(self, status: str) -> None:
        self._state["runtime_status"] = status
        self._state["updated_at"] = _now_iso()
        self._persist()

    def set_active_projects(self, projects: List[str]) -> None:
        self._state["active_projects"] = projects
        self._state["updated_at"] = _now_iso()
        self._persist()

    def set_workspace_summary(self, summary: str) -> None:
        self._state["workspace_summary"] = summary
        self._state["updated_at"] = _now_iso()
        self._persist()

    def set_executive_assessment(self, assessment: str) -> None:
        self._state["executive_assessment"] = assessment
        self._state["updated_at"] = _now_iso()
        self._persist()

    def set_founder_context(self, context: Dict[str, Any]) -> None:
        self._state["founder_context"] = context
        self._state["updated_at"] = _now_iso()
        self._persist()

    def add_pending_approval(self, item: Dict[str, Any]) -> None:
        item.setdefault("id", f"approval-{_now_iso()}")
        item.setdefault("created_at", _now_iso())
        item.setdefault("status", "pending")
        approvals: List[Dict] = self._state.setdefault("pending_approvals", [])
        approvals.append(item)
        self._state["updated_at"] = _now_iso()
        self._persist()

    def resolve_approval(self, approval_id: str, resolution: str) -> bool:
        for item in self._state.get("pending_approvals", []):
            if item.get("id") == approval_id:
                item["status"] = resolution
                item["resolved_at"] = _now_iso()
                self._state["updated_at"] = _now_iso()
                self._persist()
                return True
        return False

    def record_decision(self, summary: str, context: str = "") -> None:
        decisions: List[Dict] = self._state.setdefault("recent_decisions", [])
        decisions.insert(0, {
            "summary": summary,
            "context": context,
            "at": _now_iso(),
        })
        self._state["recent_decisions"] = decisions[:20]
        self._state["updated_at"] = _now_iso()
        self._persist()

    def add_task(self, task: Dict[str, Any]) -> None:
        task.setdefault("id", f"task-{_now_iso()}")
        task.setdefault("created_at", _now_iso())
        task.setdefault("status", "pending")
        tasks: List[Dict] = self._state.setdefault("running_tasks", [])
        tasks.append(task)
        self._state["updated_at"] = _now_iso()
        self._persist()

    def update_task(self, task_id: str, status: str, result: str = "") -> bool:
        for task in self._state.get("running_tasks", []):
            if task.get("id") == task_id:
                task["status"] = status
                task["updated_at"] = _now_iso()
                if result:
                    task["result"] = result
                self._state["updated_at"] = _now_iso()
                self._persist()
                return True
        return False

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def pending_approvals(self) -> List[Dict]:
        return [a for a in self._state.get("pending_approvals", []) if a.get("status") == "pending"]

    @property
    def active_goals(self) -> List[str]:
        return self._state.get("active_goals", [])

    @property
    def active_projects(self) -> List[str]:
        return self._state.get("active_projects", [])

    @property
    def running_tasks(self) -> List[Dict]:
        return [t for t in self._state.get("running_tasks", []) if t.get("status") not in {"done", "failed"}]

    @property
    def executive_assessment(self) -> str:
        return self._state.get("executive_assessment", "")

    @property
    def workspace_summary(self) -> str:
        return self._state.get("workspace_summary", "")

    @property
    def runtime_status(self) -> str:
        return self._state.get("runtime_status", "initializing")

    @property
    def last_session_at(self) -> Optional[str]:
        return self._state.get("last_session_at")

    @property
    def session_count(self) -> int:
        return self._state.get("session_count", 0)

    @property
    def founder_context(self) -> Dict[str, Any]:
        return self._state.get("founder_context", {})

    def snapshot(self) -> Dict[str, Any]:
        """نسخة كاملة من الحالة الحالية."""
        return dict(self._state)
