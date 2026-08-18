"""Central API usage and cost ledger for Ameer.

Usage comes from provider responses. Monetary cost is calculated only when
AMEER_MODEL_PRICING_JSON is configured; no prices are fabricated.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


class CostLedger:
    def __init__(self, workspace_root: str | Path):
        root = Path(workspace_root).resolve()
        raw = (os.getenv("AMEER_DATA_DIR") or "").strip()
        data_dir = Path(raw).resolve() if raw else root / ".ameer"
        if data_dir.name != ".ameer":
            data_dir = data_dir / ".ameer"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "api_cost_ledger.sqlite3"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS api_usage (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    input_cost_usd REAL,
                    output_cost_usd REAL,
                    estimated_cost_usd REAL,
                    actual_cost_usd REAL,
                    pricing_status TEXT NOT NULL DEFAULT 'unpriced',
                    latency_ms REAL,
                    status TEXT NOT NULL,
                    quality_signal REAL,
                    fallback_reason TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_api_usage_agent ON api_usage(agent_id);
                CREATE INDEX IF NOT EXISTS idx_api_usage_task ON api_usage(task_id);
                CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at);
                """
            )

    @staticmethod
    def _pricing(model: str) -> Optional[Dict[str, float]]:
        raw = (os.getenv("AMEER_MODEL_PRICING_JSON") or "").strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
            item = data.get(model) or data.get("*")
            if not item:
                return None
            return {"input_per_1m": float(item["input_per_1m"]), "output_per_1m": float(item["output_per_1m"])}
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def record(self, *, task_id: str, run_id: str, agent_id: str, provider: str, model: str, usage: Optional[Dict[str, Any]], status: str, latency_ms: Optional[float] = None, actual_cost_usd: Optional[float] = None, quality_signal: Optional[float] = None, fallback_reason: str = "") -> Dict[str, Any]:
        usage = usage or {}
        input_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
        output_tokens = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
        total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)
        pricing = self._pricing(model)
        input_cost = output_cost = estimated = None
        pricing_status = "unpriced"
        if pricing:
            input_cost = input_tokens / 1_000_000 * pricing["input_per_1m"]
            output_cost = output_tokens / 1_000_000 * pricing["output_per_1m"]
            estimated = input_cost + output_cost
            pricing_status = "configured"
        elif actual_cost_usd is not None:
            pricing_status = "provider_reported"
        event = {
            "event_id": uuid.uuid4().hex,
            "task_id": task_id,
            "run_id": run_id,
            "agent_id": agent_id,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "estimated_cost_usd": estimated,
            "actual_cost_usd": actual_cost_usd,
            "pricing_status": pricing_status,
            "latency_ms": latency_ms,
            "status": status,
            "quality_signal": quality_signal,
            "fallback_reason": fallback_reason,
            "created_at": time.time(),
        }
        with self._connect() as db:
            db.execute("INSERT INTO api_usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(event.values()))
        return event

    def list(self, *, agent_id: Optional[str] = None, task_id: Optional[str] = None, limit: int = 100) -> list[Dict[str, Any]]:
        query, args, filters = "SELECT * FROM api_usage", [], []
        if agent_id:
            filters.append("agent_id=?"); args.append(agent_id)
        if task_id:
            filters.append("task_id=?"); args.append(task_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC LIMIT ?"; args.append(int(limit))
        with self._connect() as db:
            return [dict(row) for row in db.execute(query, tuple(args)).fetchall()]

    def summary(self) -> Dict[str, Any]:
        with self._connect() as db:
            totals = db.execute("SELECT COUNT(*) runs, COALESCE(SUM(total_tokens),0) tokens, COALESCE(SUM(estimated_cost_usd),0) estimated_cost_usd, COALESCE(SUM(actual_cost_usd),0) actual_cost_usd FROM api_usage").fetchone()
            rows = db.execute("SELECT agent_id, COUNT(*) runs, COALESCE(SUM(total_tokens),0) tokens, COALESCE(SUM(estimated_cost_usd),0) estimated_cost_usd, COALESCE(SUM(actual_cost_usd),0) actual_cost_usd FROM api_usage GROUP BY agent_id ORDER BY estimated_cost_usd DESC").fetchall()
        return {"status": "ok", "pricing_source": "AMEER_MODEL_PRICING_JSON", "totals": dict(totals), "by_agent": [dict(row) for row in rows]}

    def snapshot(self, **filters: Any) -> Dict[str, Any]:
        return {"status": "ok", "summary": self.summary(), "events": self.list(**filters)}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "pricing_configured": bool(os.getenv("AMEER_MODEL_PRICING_JSON")), "db_path": str(self.db_path)}

    def reset(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM api_usage")

    def __len__(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM api_usage").fetchone()[0])
