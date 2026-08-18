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

from kernel.cost_ledger import CostLedger


DEFAULT_WORKERS = {
    "engineering": ("Software engineering, architecture, testing and debugging", "programming"),
    "design": ("UI/UX, visual systems and product design", "ui_design"),
    "business": ("Store, inventory, customers, bookings and employees", "business"),
    "school": ("School records, attendance, grades and follow-up", "school"),
    "communications": ("Email and calendar operations", "communications"),
    "research": ("Research, analysis and structured reporting", "research"),
    "operations": ("Operational monitoring and recurring administrative work", "operations"),
    "store": ("Dream Al Nada Center store, inventory, staff, bookings and orders", "store_management"),
}


# Every worker has an independent capability envelope. The common governance
# contract is preserved, but paths and capabilities are not shared implicitly.
_WORKER_SCOPES = {
    "engineering": {"paths": ["06_Code", "07_Tests", "09_Assets/web"], "capabilities": ["code.read", "code.write", "tests.execute"]},
    "design": {"paths": ["09_Assets/web", "09_Assets/design"], "capabilities": ["design.read", "design.write", "preview.execute"]},
    "business": {"paths": ["04_Memory/business", "09_Assets/business"], "capabilities": ["business.read", "business.write", "analysis.execute"]},
    "school": {"paths": ["04_Memory/school", "09_Assets/school"], "capabilities": ["school.read", "school.write", "report.execute"]},
    "communications": {"paths": ["04_Memory/communications", "09_Assets/communications"], "capabilities": ["communications.read", "communications.write", "draft.execute"]},
    "research": {"paths": ["04_Memory/research", "09_Assets/research"], "capabilities": ["research.read", "research.write", "analysis.execute"]},
    "operations": {"paths": ["04_Memory/operations", "09_Assets/operations"], "capabilities": ["operations.read", "operations.write", "monitor.execute"]},
    "store": {"paths": ["04_Memory/dream_al_nada", "09_Assets/dream_al_nada"], "capabilities": ["store.read", "inventory.write", "staff.write", "bookings.write", "store_reports.execute"]},
}


def worker_access_policy(worker_id: str) -> dict:
    """Return an independent, defensive capability envelope for one worker."""
    if worker_id not in DEFAULT_WORKERS:
        raise ValueError(f"unknown_worker:{worker_id}")
    scope = _WORKER_SCOPES[worker_id]
    return {
        "worker_id": worker_id,
        "read": {"enabled": True, "scope": "worker_workspace_only", "allowed_paths": list(scope["paths"])},
        "write": {"enabled": True, "scope": "worker_workspace_only", "authority": "ameer", "approval": "ameer_review", "user_approval_required": False, "allowed_paths": list(scope["paths"])},
        "execute_internal": {"enabled": True, "scope": "worker_workspace_only", "authority": "ameer", "approval": "ameer_review", "user_approval_required": False, "capabilities": list(scope["capabilities"])},
        "external_effect": {"enabled": False, "authority": "founder", "approval": "founder_final", "allowed": []},
        "cross_worker_access": False,
        "can_kill_other_processes": False,
        "can_modify_governance": False,
    }


class WorkerRuntimeRegistry:
    """Persistent worker availability and adapter registry."""

    VALID_STATUSES = {"unavailable", "configured", "ready", "busy", "failed"}

    def __init__(self, workspace_root: str | Path, *, audit=None, cost_ledger=None):
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "worker_runtime.sqlite3"
        self.audit = audit
        self.cost_ledger = cost_ledger or CostLedger(root)
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
        if self.audit:
            self.audit.record(event_type="worker_dispatch_requested", actor="ameer", subject=worker_id, status="requested", payload={"objective": objective, "access_policy": worker_access_policy(worker_id)})
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
        if self.audit:
            self.audit.record(event_type="worker_run_started", actor="ameer", subject=worker_id, status="running", correlation_id=run_id, payload={"run_id": run_id, "objective": objective, "delegated_by": "ameer"})
        started_perf = time.perf_counter()
        try:
            dispatch_context = dict(context or {})
            dispatch_context.setdefault("worker_id", worker_id)
            dispatch_context.setdefault("delegated_by", "ameer")
            dispatch_context.setdefault("access_policy", worker_access_policy(worker_id))
            result = handler(objective, dispatch_context) or {}
            status = str(result.get("status", "completed"))
            if status not in {"completed", "failed"}:
                status = "completed"
            usage = result.get("usage") or {}
            cost_event = self.cost_ledger.record(
                task_id=str(dispatch_context.get("task_id") or run_id),
                run_id=run_id,
                agent_id=worker_id,
                provider=str(worker.get("provider") or ""),
                model=str(worker.get("model") or result.get("model") or ""),
                usage=usage,
                status=status,
                latency_ms=round((time.perf_counter() - started_perf) * 1000, 2),
                actual_cost_usd=result.get("cost_usd"),
                quality_signal=result.get("quality_signal"),
                fallback_reason=str(result.get("fallback_reason") or ""),
            )
            result = dict(result)
            result["cost"] = {"event_id": cost_event["event_id"], "total_tokens": cost_event["total_tokens"], "estimated_cost_usd": cost_event["estimated_cost_usd"], "actual_cost_usd": cost_event["actual_cost_usd"], "pricing_status": cost_event["pricing_status"]}
            with self._connect() as db:
                db.execute(
                    "UPDATE worker_runs SET status=?, result_json=?, updated_at=? WHERE run_id=?",
                    (status, json.dumps(result, ensure_ascii=False), time.time(), run_id),
                )
            self.heartbeat(worker_id, status="ready")
            if self.audit:
                self.audit.record(event_type="worker_run_completed", actor=worker_id, subject="ameer", status=status, correlation_id=run_id, payload={"run_id": run_id, "worker_id": worker_id})
            return {"status": status, "run_id": run_id, "worker_id": worker_id, "result": result}
        except Exception as exc:
            with self._connect() as db:
                db.execute(
                    "UPDATE worker_runs SET status='failed', error=?, updated_at=? WHERE run_id=?",
                    (str(exc), time.time(), run_id),
                )
            try:
                self.cost_ledger.record(task_id=str((context or {}).get("task_id") or run_id), run_id=run_id, agent_id=worker_id, provider=str(worker.get("provider") or ""), model=str(worker.get("model") or ""), usage={}, status="failed", latency_ms=round((time.perf_counter() - started_perf) * 1000, 2))
            except Exception:
                pass
            self.heartbeat(worker_id, status="failed", error=str(exc))
            if self.audit:
                self.audit.record(event_type="worker_run_failed", actor=worker_id, subject="ameer", status="failed", correlation_id=run_id, payload={"run_id": run_id, "worker_id": worker_id, "error": str(exc)})
            return {"status": "failed", "run_id": run_id, "worker_id": worker_id, "reason": "worker_execution_failed", "error": str(exc)}
