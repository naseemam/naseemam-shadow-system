"""Persistent governed message bus for Ameer, workers, and the founder."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.worker_runtime import DEFAULT_WORKERS


ACTORS = {"user", "founder", "ameer", *DEFAULT_WORKERS.keys()}


class AgentMessageBus:
    """Small durable inbox/outbox with a strict reporting chain.

    Allowed directions are user/founder -> ameer, ameer -> worker, and worker -> ameer.
    Workers cannot message the founder directly; all worker reports return to Ameer.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "agent_messages.sqlite3"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    body TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                )"""
            )

    @staticmethod
    def _direction_allowed(sender: str, recipient: str) -> bool:
        if sender in {"user", "founder"}:
            return recipient == "ameer"
        if sender == "ameer":
            return recipient in DEFAULT_WORKERS or recipient in {"user", "founder"}
        return sender in DEFAULT_WORKERS and recipient == "ameer"

    def send(
        self,
        *,
        sender: str,
        recipient: str,
        body: str,
        kind: str = "message",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sender = str(sender or "").strip().lower()
        recipient = str(recipient or "").strip().lower()
        body = str(body or "").strip()
        if sender not in ACTORS or recipient not in ACTORS:
            raise ValueError("unknown_actor")
        if not body:
            raise ValueError("message_body_required")
        if not self._direction_allowed(sender, recipient):
            raise PermissionError("worker_reporting_chain_violation")
        message = {
            "message_id": uuid.uuid4().hex[:16],
            "sender": sender,
            "recipient": recipient,
            "kind": str(kind or "message"),
            "body": body,
            "metadata": metadata or {},
            "created_at": time.time(),
        }
        with self._connect() as db:
            db.execute(
                "INSERT INTO messages(message_id,sender,recipient,kind,body,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    message["message_id"],
                    sender,
                    recipient,
                    message["kind"],
                    body,
                    json.dumps(message["metadata"], ensure_ascii=False),
                    message["created_at"],
                ),
            )
        return message

    def list(self, *, actor: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 500))
        with self._connect() as db:
            if actor:
                rows = db.execute(
                    "SELECT * FROM messages WHERE sender=? OR recipient=? ORDER BY created_at DESC LIMIT ?",
                    (actor, actor, limit),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            result.append(item)
        return list(reversed(result))

    def snapshot(self) -> Dict[str, Any]:
        with self._connect() as db:
            count = db.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
        return {
            "message_count": int(count),
            "reporting_chain": "user/founder -> ameer -> workers -> ameer -> user/founder",
            "worker_direct_founder_contact": False,
        }
