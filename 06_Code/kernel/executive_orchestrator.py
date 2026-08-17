from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.worker_runtime import WorkerRuntimeRegistry


class ExecutiveOrchestrator:
    """Ameer is the executive manager above subordinate bots/assistants.

    Workers may execute delegated work, but they do not own Founder approval,
    production deployment, main-branch merge, credentials, or irreversible
    business decisions. Those remain centralized in Ameer's governance lane.
    """

    DEFAULT_WORKERS = {
        "engineering": "Software engineering, architecture, testing and debugging",
        "design": "UI/UX, visual systems and product design",
        "business": "Store, inventory, customers, bookings and employees",
        "school": "School records, attendance, grades and follow-up",
        "communications": "Email and calendar operations",
        "research": "Research, analysis and structured reporting",
        "operations": "Operational monitoring and recurring administrative work",
    }

    RESERVED_ACTIONS = {
        "merge_main",
        "production_deploy",
        "rollback",
        "credential_grant",
        "credential_rotate",
        "irreversible_delete",
        "activate_external_skill",
    }

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(os.getenv("AMEER_DATA_DIR") or workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "executive_orchestrator.sqlite3"
        self.runtime = WorkerRuntimeRegistry(root)
        self._init_db()
        self._seed_workers()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS workers (
              worker_id TEXT PRIMARY KEY,
              role TEXT NOT NULL,
              description TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS delegations (
              delegation_id TEXT PRIMARY KEY,
              worker_id TEXT NOT NULL,
              objective TEXT NOT NULL,
              context_json TEXT NOT NULL,
              status TEXT NOT NULL,
              result_json TEXT NOT NULL DEFAULT '{}',
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL
            );
            """)

    def _seed_workers(self) -> None:
        now = time.time()
        with self._connect() as db:
            for worker_id, description in self.DEFAULT_WORKERS.items():
                db.execute(
                    "INSERT OR IGNORE INTO workers(worker_id, role, description, enabled, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                    (worker_id, worker_id, description, 1, now, now),
                )

    def workers(self) -> List[Dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM workers ORDER BY worker_id").fetchall()
        items = [dict(row) for row in rows]
        runtime = {item["worker_id"]: item for item in self.runtime.snapshot()["workers"]}
        for item in items:
            item["runtime"] = runtime.get(item["worker_id"], {"status": "unavailable", "reason": "worker_runtime_not_registered"})
        return items

    def runtime_snapshot(self) -> Dict[str, Any]:
        return self.runtime.snapshot()

    def register_worker_runtime(self, worker_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self.runtime.register_runtime(worker_id, **kwargs)

    def worker_heartbeat(self, worker_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self.runtime.heartbeat(worker_id, **kwargs)

    def dispatch_to_worker(self, worker_id: str, objective: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.runtime.dispatch(worker_id, objective, context)

    def register_worker(self, worker_id: str, role: str, description: str) -> Dict[str, Any]:
        worker_id = worker_id.strip().lower().replace(" ", "_")
        if not worker_id:
            raise ValueError("worker_id is required")
        now = time.time()
        with self._connect() as db:
            db.execute(
                "INSERT INTO workers(worker_id, role, description, enabled, created_at, updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(worker_id) DO UPDATE SET role=excluded.role, description=excluded.description, enabled=1, updated_at=excluded.updated_at",
                (worker_id, role, description, 1, now, now),
            )
        return {"status": "registered", "worker_id": worker_id, "role": role}

    def delegate(self, worker_id: str, objective: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        worker_id = worker_id.strip().lower()
        with self._connect() as db:
            worker = db.execute("SELECT * FROM workers WHERE worker_id=? AND enabled=1", (worker_id,)).fetchone()
            if not worker:
                raise ValueError(f"Unknown or disabled worker: {worker_id}")
            delegation_id = uuid.uuid4().hex[:16]
            now = time.time()
            db.execute(
                "INSERT INTO delegations(delegation_id, worker_id, objective, context_json, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                (delegation_id, worker_id, objective, json.dumps(context or {}, ensure_ascii=False), "assigned", now, now),
            )
        return {
            "status": "assigned",
            "delegation_id": delegation_id,
            "worker_id": worker_id,
            "objective": objective,
            "authority": "delegated_by_ameer",
        }

    def complete(self, delegation_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._connect() as db:
            row = db.execute("SELECT * FROM delegations WHERE delegation_id=?", (delegation_id,)).fetchone()
            if not row:
                raise ValueError("delegation not found")
            db.execute(
                "UPDATE delegations SET status='completed', result_json=?, updated_at=? WHERE delegation_id=?",
                (json.dumps(result or {}, ensure_ascii=False), now, delegation_id),
            )
        return {"status": "completed", "delegation_id": delegation_id, "reported_to": "ameer"}

    def pending(self) -> List[Dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM delegations WHERE status!='completed' ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def authority(self) -> Dict[str, Any]:
        return {
            "executive": "ameer",
            "founder": "final_authority",
            "subordinate_workers": list(self.DEFAULT_WORKERS),
            "worker_runtime": self.runtime.snapshot(),
            "worker_can_delegate_subtasks": True,
            "worker_can_merge_main": False,
            "worker_can_deploy_production": False,
            "worker_can_grant_credentials": False,
            "worker_can_bypass_final_gate": False,
            "reserved_actions": sorted(self.RESERVED_ACTIONS),
            "reporting_chain": "worker -> Ameer -> Founder(final gate only)",
        }
