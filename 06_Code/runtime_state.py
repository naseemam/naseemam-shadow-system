"""
runtime_state.py
================
P1.1 Runtime State store for Executive Runtime.

This module persists runtime execution state to disk and restores it on restart.
It intentionally contains no governance logic; governance remains in P0.6 layers.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_SCHEMA_VERSION = 1

_REQUIRED_FIELDS = {
    "run_id",
    "current_task_id",
    "current_step",
    "running_executors",
    "progress_percent",
    "eta_seconds",
    "paused",
    "cancelled",
    "completed",
    "last_update_at",
}


class RuntimeStateStore:
    """Persistent runtime state for P1 execution lifecycle."""

    def __init__(self, workspace_root: str | None = None, state_rel_path: str = ".ameer/runtime_state.json") -> None:
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.state_path = Path(self.workspace_root) / state_rel_path
        self._state: Dict[str, Any] = self._load_or_init()

    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _default_state(self) -> Dict[str, Any]:
        return {
            "run_id": None,
            "current_task_id": None,
            "current_step": "idle",
            "running_executors": [],
            "progress_percent": 0,
            "eta_seconds": None,
            "paused": False,
            "cancelled": False,
            "completed": False,
            "last_update_at": self._now(),
            "active_tasks": [],
            "completed_tasks": [],
            "events": [],
        }

    def _default_envelope(self) -> Dict[str, Any]:
        timestamp = self._now()
        return {
            "schema_version": _SCHEMA_VERSION,
            "created_at": timestamp,
            "updated_at": timestamp,
            "runtime": self._default_state(),
        }

    def _normalize_envelope(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        envelope = self._default_envelope()
        envelope.update(loaded or {})
        runtime_payload = loaded.get("runtime") if isinstance(loaded, dict) else None

        # Backward compatibility: accept legacy flat runtime state files.
        if runtime_payload is None and any(key in loaded for key in _REQUIRED_FIELDS):
            runtime_payload = dict(loaded)

        if not isinstance(runtime_payload, dict):
            runtime_payload = self._default_state()

        envelope["schema_version"] = int(envelope.get("schema_version") or _SCHEMA_VERSION)
        envelope["created_at"] = envelope.get("created_at") or self._now()
        envelope["updated_at"] = self._now()
        envelope["runtime"] = self._normalize_state(runtime_payload)
        return envelope

    def _normalize_state(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        state = self._default_state()
        state.update(loaded or {})

        # Ensure required contract fields always exist.
        for key in _REQUIRED_FIELDS:
            state.setdefault(key, self._default_state()[key])

        state["running_executors"] = list(state.get("running_executors") or [])
        state["active_tasks"] = list(state.get("active_tasks") or [])
        state["completed_tasks"] = list(state.get("completed_tasks") or [])
        state["events"] = list(state.get("events") or [])
        state["last_update_at"] = self._now()
        return state

    def _load_or_init(self) -> Dict[str, Any]:
        default_envelope = self._default_envelope()
        try:
            if not self.state_path.exists():
                self.state_path.parent.mkdir(parents=True, exist_ok=True)
                self.state_path.write_text(json.dumps(default_envelope, ensure_ascii=False, indent=2), encoding="utf-8")
                return default_envelope["runtime"]
            loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return default_envelope["runtime"]
            normalized = self._normalize_envelope(loaded)
            self._state = normalized["runtime"]
            self._persist()
            return normalized["runtime"]
        except Exception:
            return default_envelope["runtime"]

    def _persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        existing_created_at = None
        if self.state_path.exists():
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    existing_created_at = payload.get("created_at")
            except Exception:
                existing_created_at = None

        envelope = {
            "schema_version": _SCHEMA_VERSION,
            "created_at": existing_created_at or self._now(),
            "updated_at": self._now(),
            "runtime": self._state,
        }
        self.state_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    def _record_event(self, event: str, details: Optional[Dict[str, Any]] = None) -> None:
        self._state.setdefault("events", []).append(
            {
                "event": event,
                "details": details or {},
                "at": self._now(),
            }
        )

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(self._state)

    def envelope_snapshot(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass
        return self._default_envelope()

    def recover(self) -> Dict[str, Any]:
        runtime = self.snapshot()
        resumable = bool(runtime.get("run_id")) and not runtime.get("completed") and not runtime.get("cancelled")
        recovery_payload = {
            "resumable": resumable,
            "run_id": runtime.get("run_id"),
            "current_step": runtime.get("current_step"),
            "current_task_id": runtime.get("current_task_id"),
            "active_tasks": deepcopy(runtime.get("active_tasks", [])),
            "running_executors": list(runtime.get("running_executors", [])),
        }
        self._record_event("recovery_checked", {"resumable": resumable, "run_id": runtime.get("run_id")})
        self._persist()
        return recovery_payload

    def begin_run(self, run_id: str, initial_step: str = "parse", eta_seconds: int | None = None) -> Dict[str, Any]:
        self._state = self._default_state()
        self._state.update(
            {
                "run_id": run_id,
                "current_step": initial_step,
                "eta_seconds": eta_seconds,
                "last_update_at": self._now(),
            }
        )
        self._record_event("run_started", {"run_id": run_id, "step": initial_step})
        self._persist()
        return self.snapshot()

    def set_current_step(self, step: str) -> Dict[str, Any]:
        self._state["current_step"] = step
        self._state["last_update_at"] = self._now()
        self._record_event("step_updated", {"step": step})
        self._persist()
        return self.snapshot()

    def set_current_task(self, task_id: str | None) -> Dict[str, Any]:
        self._state["current_task_id"] = task_id
        self._state["last_update_at"] = self._now()
        self._record_event("current_task_updated", {"task_id": task_id})
        self._persist()
        return self.snapshot()

    def set_running_executors(self, executors: List[str]) -> Dict[str, Any]:
        self._state["running_executors"] = list(executors)
        self._state["last_update_at"] = self._now()
        self._record_event("executors_updated", {"running_executors": list(executors)})
        self._persist()
        return self.snapshot()

    def set_progress(self, percent: int) -> Dict[str, Any]:
        bounded = max(0, min(100, int(percent)))
        self._state["progress_percent"] = bounded
        self._state["last_update_at"] = self._now()
        self._record_event("progress_updated", {"progress_percent": bounded})
        self._persist()
        return self.snapshot()

    def set_eta(self, eta_seconds: int | None) -> Dict[str, Any]:
        self._state["eta_seconds"] = None if eta_seconds is None else max(0, int(eta_seconds))
        self._state["last_update_at"] = self._now()
        self._record_event("eta_updated", {"eta_seconds": self._state["eta_seconds"]})
        self._persist()
        return self.snapshot()

    def add_active_task(self, task_id: str, executor: str | None = None) -> Dict[str, Any]:
        active_tasks = self._state.setdefault("active_tasks", [])
        if not any(item.get("task_id") == task_id for item in active_tasks):
            active_tasks.append(
                {
                    "task_id": task_id,
                    "executor": executor,
                    "started_at": self._now(),
                }
            )
        self._state["current_task_id"] = task_id
        self._state["last_update_at"] = self._now()
        self._record_event("active_task_added", {"task_id": task_id, "executor": executor})
        self._persist()
        return self.snapshot()

    def complete_task(self, task_id: str, status: str = "succeeded") -> Dict[str, Any]:
        active_tasks = self._state.setdefault("active_tasks", [])
        completed_tasks = self._state.setdefault("completed_tasks", [])

        task_entry = None
        remaining = []
        for item in active_tasks:
            if item.get("task_id") == task_id and task_entry is None:
                task_entry = item
            else:
                remaining.append(item)

        self._state["active_tasks"] = remaining

        finished_entry = {
            "task_id": task_id,
            "executor": (task_entry or {}).get("executor"),
            "started_at": (task_entry or {}).get("started_at"),
            "finished_at": self._now(),
            "status": status,
        }
        completed_tasks.append(finished_entry)

        if self._state.get("current_task_id") == task_id:
            self._state["current_task_id"] = None

        self._state["last_update_at"] = self._now()
        self._record_event("task_completed", {"task_id": task_id, "status": status})
        self._persist()
        return self.snapshot()

    def pause(self) -> Dict[str, Any]:
        self._state["paused"] = True
        self._state["last_update_at"] = self._now()
        self._record_event("run_paused")
        self._persist()
        return self.snapshot()

    def resume(self) -> Dict[str, Any]:
        self._state["paused"] = False
        self._state["last_update_at"] = self._now()
        self._record_event("run_resumed")
        self._persist()
        return self.snapshot()

    def cancel(self) -> Dict[str, Any]:
        self._state["cancelled"] = True
        self._state["completed"] = False
        self._state["last_update_at"] = self._now()
        self._record_event("run_cancelled")
        self._persist()
        return self.snapshot()

    def complete(self) -> Dict[str, Any]:
        self._state["completed"] = True
        self._state["cancelled"] = False
        self._state["progress_percent"] = 100
        self._state["running_executors"] = []
        self._state["current_task_id"] = None
        self._state["last_update_at"] = self._now()
        self._record_event("run_completed")
        self._persist()
        return self.snapshot()
