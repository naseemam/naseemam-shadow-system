from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CommerceTestEnvironment:
    """Sandbox-only commerce state for Dream Al Nada.

    This class never calls a payment or shipping provider. It is intentionally
    separate from BusinessOperations and refuses to run unless test mode is
    explicitly enabled.
    """

    PROJECT_ID = "dream_al_nada_store"
    MODE = "test"

    def __init__(self, workspace_root: str | Path) -> None:
        if os.getenv("AMEER_COMMERCE_MODE", "test").strip().lower() != "test":
            raise RuntimeError("commerce_test_environment_requires_test_mode")
        root = Path(workspace_root).resolve()
        raw_data = (os.getenv("AMEER_DATA_DIR") or "").strip()
        data_dir = Path(raw_data).resolve() if raw_data else root / ".ameer"
        if data_dir.name != ".ameer":
            data_dir = data_dir / ".ameer"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "commerce_test.sqlite3"
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS test_orders (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    total REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'SAR',
                    status TEXT NOT NULL DEFAULT 'pending_payment',
                    payment_status TEXT NOT NULL DEFAULT 'pending',
                    shipment_status TEXT NOT NULL DEFAULT 'not_required',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS test_payment_events (
                    event_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES test_orders(id)
                );
                CREATE TABLE IF NOT EXISTS test_shipments (
                    id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    tracking_number TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'created',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(order_id) REFERENCES test_orders(id)
                );
                CREATE TABLE IF NOT EXISTS test_shipping_events (
                    event_id TEXT PRIMARY KEY,
                    shipment_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    FOREIGN KEY(shipment_id) REFERENCES test_shipments(id)
                );
                """
            )

    def _order(self, conn: sqlite3.Connection, order_id: str) -> Dict[str, Any]:
        row = conn.execute("SELECT * FROM test_orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise KeyError("test_order_not_found")
        return dict(row)

    def create_order(self, *, customer_name: str, total: float, currency: str = "SAR") -> Dict[str, Any]:
        order_id = "test_order_" + uuid.uuid4().hex[:12]
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO test_orders(id,project_id,customer_name,total,currency,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (order_id, self.PROJECT_ID, customer_name, float(total), currency.upper(), now, now),
            )
            return self._order(conn, order_id)

    def create_payment_session(self, order_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            order = self._order(conn, order_id)
            if order["payment_status"] not in {"pending", "failed"}:
                raise ValueError("payment_session_not_allowed_for_current_status")
            return {
                "mode": self.MODE,
                "provider": "test_gateway",
                "session_id": "test_session_" + uuid.uuid4().hex[:12],
                "order_id": order["id"],
                "amount": order["total"],
                "currency": order["currency"],
                "no_real_charge": True,
            }

    def process_payment_webhook(self, *, event_id: str, order_id: str, event_type: str, status: str, payload: Dict[str, Any], provider: str = "test_gateway") -> Dict[str, Any]:
        if status not in {"paid", "failed", "refunded"}:
            raise ValueError("unsupported_test_payment_status")
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        now = _now()
        with self._connect() as conn:
            order = self._order(conn, order_id)
            existing = conn.execute("SELECT * FROM test_payment_events WHERE event_id=?", (event_id,)).fetchone()
            if existing:
                return {"status": "duplicate_ignored", "event_id": event_id, "order": order}
            conn.execute(
                "INSERT INTO test_payment_events(event_id,order_id,provider,event_type,status,payload_hash,processed_at) VALUES(?,?,?,?,?,?,?)",
                (event_id, order_id, provider, event_type, status, payload_hash, now),
            )
            order_status = "paid" if status == "paid" else ("refunded" if status == "refunded" else "payment_failed")
            shipment_status = "pending_creation" if status == "paid" else order["shipment_status"]
            conn.execute(
                "UPDATE test_orders SET status=?, payment_status=?, shipment_status=?, updated_at=? WHERE id=?",
                (order_status, status, shipment_status, now, order_id),
            )
            return {"status": "processed", "event_id": event_id, "order": self._order(conn, order_id)}

    def create_test_shipment(self, order_id: str, *, provider: str = "test_carrier") -> Dict[str, Any]:
        with self._connect() as conn:
            order = self._order(conn, order_id)
            if order["payment_status"] != "paid":
                raise ValueError("shipment_requires_paid_test_order")
            existing = conn.execute("SELECT * FROM test_shipments WHERE order_id=?", (order_id,)).fetchone()
            if existing:
                return {"status": "existing", "shipment": dict(existing), "no_real_shipment": True}
            shipment_id = "test_ship_" + uuid.uuid4().hex[:12]
            tracking = "TEST" + uuid.uuid4().hex[:16].upper()
            now = _now()
            conn.execute(
                "INSERT INTO test_shipments(id,order_id,provider,tracking_number,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (shipment_id, order_id, provider, tracking, now, now),
            )
            conn.execute("UPDATE test_orders SET shipment_status='created', updated_at=? WHERE id=?", (now, order_id))
            row = conn.execute("SELECT * FROM test_shipments WHERE id=?", (shipment_id,)).fetchone()
            return {"status": "created", "shipment": dict(row), "no_real_shipment": True}

    def get_test_shipment(self, order_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            self._order(conn, order_id)
            row = conn.execute("SELECT * FROM test_shipments WHERE order_id=?", (order_id,)).fetchone()
            if row is None:
                raise KeyError("test_shipment_not_found")
            return {"mode": self.MODE, "no_real_shipment": True, "shipment": dict(row)}

    def process_shipping_webhook(self, *, event_id: str, shipment_id: str, status: str, payload: Dict[str, Any], provider: str = "test_carrier") -> Dict[str, Any]:
        allowed = {"created", "picked_up", "in_transit", "delivered", "returned", "cancelled"}
        if status not in allowed:
            raise ValueError("unsupported_test_shipping_status")
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        now = _now()
        with self._connect() as conn:
            shipment = conn.execute("SELECT * FROM test_shipments WHERE id=?", (shipment_id,)).fetchone()
            if shipment is None:
                raise KeyError("test_shipment_not_found")
            existing = conn.execute("SELECT * FROM test_shipping_events WHERE event_id=?", (event_id,)).fetchone()
            if existing:
                return {"status": "duplicate_ignored", "event_id": event_id, "no_real_shipment": True, "shipment": dict(shipment)}
            conn.execute(
                "INSERT INTO test_shipping_events(event_id,shipment_id,provider,status,payload_hash,processed_at) VALUES(?,?,?,?,?,?)",
                (event_id, shipment_id, provider, status, payload_hash, now),
            )
            conn.execute("UPDATE test_shipments SET status=?, updated_at=? WHERE id=?", (status, now, shipment_id))
            updated = conn.execute("SELECT * FROM test_shipments WHERE id=?", (shipment_id,)).fetchone()
            return {"status": "processed", "event_id": event_id, "no_real_shipment": True, "shipment": dict(updated)}

    def snapshot(self) -> Dict[str, Any]:
        with self._connect() as conn:
            orders = conn.execute("SELECT * FROM test_orders ORDER BY created_at DESC LIMIT 50").fetchall()
            shipments = conn.execute("SELECT * FROM test_shipments ORDER BY created_at DESC LIMIT 50").fetchall()
            events = conn.execute("SELECT * FROM test_payment_events ORDER BY processed_at DESC LIMIT 50").fetchall()
            shipping_events = conn.execute("SELECT * FROM test_shipping_events ORDER BY processed_at DESC LIMIT 50").fetchall()
        return {
            "mode": self.MODE,
            "project_id": self.PROJECT_ID,
            "no_real_money": True,
            "no_real_shipments": True,
            "orders": [dict(row) for row in orders],
            "shipments": [dict(row) for row in shipments],
            "payment_events": [dict(row) for row in events],
            "shipping_events": [dict(row) for row in shipping_events],
        }
