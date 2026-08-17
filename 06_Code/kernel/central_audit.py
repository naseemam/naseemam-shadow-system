"""Central append-only execution audit for the Ameer orchestration lane."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class CentralExecutionAudit:
    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "central_execution_audit.sqlite3"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                )"""
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id)")

    def record(
        self,
        *,
        event_type: str,
        actor: str,
        subject: str,
        status: str,
        correlation_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event = {
            "event_id": uuid.uuid4().hex[:16],
            "event_type": event_type,
            "actor": actor,
            "subject": subject,
            "status": status,
            "correlation_id": correlation_id or uuid.uuid4().hex[:16],
            "payload": payload or {},
            "created_at": time.time(),
        }
        with self._connect() as db:
            db.execute(
                "INSERT INTO audit_events(event_id,event_type,actor,subject,status,correlation_id,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    event["event_id"], event["event_type"], event["actor"], event["subject"],
                    event["status"], event["correlation_id"], json.dumps(event["payload"], ensure_ascii=False), event["created_at"],
                ),
            )
        return event

    def list(self, *, correlation_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 500))
        with self._connect() as db:
            if correlation_id:
                rows = db.execute("SELECT * FROM audit_events WHERE correlation_id=? ORDER BY created_at ASC LIMIT ?", (correlation_id, limit)).fetchall()
            else:
                rows = db.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            result.append(item)
        return result if correlation_id else list(reversed(result))

    def snapshot(self) -> Dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) AS n, MAX(created_at) AS latest FROM audit_events").fetchone()
        return {"event_count": int(row["n"] or 0), "latest_at": row["latest"], "append_only": True, "owner": "ameer"}
