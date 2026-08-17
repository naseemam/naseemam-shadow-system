"""Runtime registry and dispatcher for Ameer subordinate workers.

Registration is not execution. A worker is executable only when a provider/model
adapter is registered and the runtime reports ``ready``. This prevents governance
from inventing human-resource explanations for missing bot/model capacity.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


DEFAULT_WORKERS = {
    "engineering": ("Software engineering, architecture, testing and debugging", "programming"),
    "design": ("UI/UX, visual systems and product design", "ui_design"),
    "business": ("Store, inventory, customers, bookings and employees", "business"),
    "school": ("School records, attendance, grades and follow-up", "school"),
    "communications": ("Email and calendar operations", "communications"),
    "research": ("Research, analysis and structured reporting", "research"),
    "operations": ("Operational monitoring and recurring administrative work", "operations"),
}


# Worker capabilities are broad inside the governed workspace, not unrestricted
# system authority. Ameer reviews and opens the internal execution lane; the
# founder remains the final gate for external, sensitive, irreversible actions.
WORKER_ACCESS_POLICY = {
    "read": {"enabled": True, "scope": "runtime_workspace_only"},
    "write": {"enabled": True, "scope": "runtime_workspace_only", "approval": "ameer_review"},
    "execute_internal": {"enabled": True, "scope": "runtime_workspace_only", "approval": "ameer_review"},
    "external_effect": {"enabled": False, "approval": "founder_final"},
}


def worker_access_policy(worker_id: str) -> dict:
    """Return a defensive copy of the governed worker access policy."""
    if worker_id not in DEFAULT_WORKERS:
        raise ValueError(f"unknown_worker:{worker_id}")
    return {key: dict(value) for key, value in WORKER_ACCESS_POLICY.items()}


class WorkerRuntimeRegistry:
    """Persistent worker availability and adapter registry."""

    VALID_STATUSES = {"unavailable", "configured", "ready", "busy", "failed"}

    def __init__(self, workspace_root: str | Path):
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "worker_runtime.sqlite3"
        self._handlers: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {}
        self._init_db()
        self._seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS worker_runtime (
                    worker_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    description TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    adapter TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'unavailable',
                    last_heartbeat REAL,
                    last_error TEXT NOT NULL DEFAULT '',
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS worker_runs (
                    run_id TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

    def _seed_defaults(self) -> None:
        now = time.time()
        with self._connect() as db:
            for worker_id, (description, capability) in DEFAULT_WORKERS.items():
                db.execute(
                    """INSERT OR IGNORE INTO worker_runtime
                    (worker_id, role, description, capability, status, updated_at)
                    VALUES (?, ?, ?, ?, 'unavailable', ?)""",
                    (worker_id, worker_id, description, capability, now),
                )

    def register_runtime(
        self,
        worker_id: str,
        *,
        provider: str,
        model: str,
        adapter: str,
        status: str = "configured",
    ) -> Dict[str, Any]:
        worker_id = (worker_id or "").strip().lower()
        status = (status or "configured").strip().lower()
        if worker_id not in DEFAULT_WORKERS:
            raise ValueError(f"unknown_worker:{worker_id}")
        if status not in self.VALID_STATUSES:
            raise ValueError(f"invalid_worker_status:{status}")
        now = time.time()
        with self._connect() as db:
            db.execute(
                """UPDATE worker_runtime
                SET provider=?, model=?, adapter=?, status=?, last_error='', updated_at=?
                WHERE worker_id=?""",
                (provider.strip(), model.strip(), adapter.strip(), status, now, worker_id),
            )
        return self.get(worker_id)

    def register_handler(self, worker_id: str, handler: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> None:
        if worker_id not in DEFAULT_WORKERS:
            raise ValueError(f"unknown_worker:{worker_id}")
        self._handlers[worker_id] = handler

    def heartbeat(self, worker_id: str, *, status: str = "ready", error: str = "") -> Dict[str, Any]:
        status = status.strip().lower()
        if status not in self.VALID_STATUSES:
            raise ValueError(f"invalid_worker_status:{status}")
        now = time.time()
        with self._connect() as db:
            db.execute(
                """UPDATE worker_runtime SET status=?, last_heartbeat=?, last_error=?, updated_at=?
                WHERE worker_id=?""",
                (status, now, error, now, worker_id),
            )
        return self.get(worker_id)

    def get(self, worker_id: str) -> Dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM worker_runtime WHERE worker_id=?", (worker_id,)).fetchone()
        if not row:
            return {"worker_id": worker_id, "status": "unavailable", "reason": "worker_not_registered"}
        result = dict(row)
        result["access_policy"] = worker_access_policy(worker_id)
        result["available"] = result["status"] == "ready" and bool(result.get("adapter")) and bool(result.get("model"))
        if not result["available"]:
            result["reason"] = "worker_runtime_not_ready"
        return result

    def snapshot(self) -> Dict[str, Any]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM worker_runtime ORDER BY worker_id").fetchall()
        workers = []
        for row in rows:
            item = dict(row)
            item["access_policy"] = worker_access_policy(item["worker_id"])
            item["available"] = item["status"] == "ready" and bool(item.get("adapter")) and bool(item.get("model"))
            if not item["available"]:
                item["reason"] = "worker_runtime_not_ready"
            workers.append(item)
        return {
            "workers": workers,
            "ready_count": sum(1 for worker in workers if worker["available"]),
            "total_count": len(workers),
        }

    def dispatch(self, worker_id: str, objective: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        worker = self.get(worker_id)
        if not worker.get("available"):
            return {
                "status": "unavailable",
                "worker_id": worker_id,
                "reason": worker.get("reason", "worker_runtime_not_ready"),
                "provider": worker.get("provider", ""),
                "model": worker.get("model", ""),
                "adapter": worker.get("adapter", ""),
            }
        handler = self._handlers.get(worker_id)
        if handler is None:
            return {"status": "unavailable", "worker_id": worker_id, "reason": "worker_adapter_not_bound"}
        run_id = uuid.uuid4().hex[:16]
        now = time.time()
        with self._connect() as db:
            db.execute(
                "INSERT INTO worker_runs(run_id, worker_id, objective, status, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                (run_id, worker_id, objective, "running", now, now),
            )
        self.heartbeat(worker_id, status="busy")
        try:
            dispatch_context = dict(context or {})
            dispatch_context.setdefault("worker_id", worker_id)
            dispatch_context.setdefault("delegated_by", "ameer")
            dispatch_context.setdefault("access_policy", worker_access_policy(worker_id))
            result = handler(objective, dispatch_context) or {}
            status = str(result.get("status", "completed"))
            if status not in {"completed", "failed"}:
                status = "completed"
            with self._connect() as db:
                db.execute(
                    "UPDATE worker_runs SET status=?, result_json=?, updated_at=? WHERE run_id=?",
                    (status, json.dumps(result, ensure_ascii=False), time.time(), run_id),
                )
            self.heartbeat(worker_id, status="ready")
            return {"status": status, "run_id": run_id, "worker_id": worker_id, "result": result}
        except Exception as exc:
            with self._connect() as db:
                db.execute(
                    "UPDATE worker_runs SET status='failed', error=?, updated_at=? WHERE run_id=?",
                    (str(exc), time.time(), run_id),
                )
            self.heartbeat(worker_id, status="failed", error=str(exc))
            return {"status": "failed", "run_id": run_id, "worker_id": worker_id, "reason": "worker_execution_failed", "error": str(exc)}
