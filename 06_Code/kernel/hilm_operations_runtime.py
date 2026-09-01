"""Persistent operational runtime for Hilm Alnada.

This is executable stateful runtime, not a policy-only contract. It supports
service completion, stock consumption, commissions, ratings, incidents,
maintenance, and offline sync queues with idempotent transactions.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HilmOperationsRuntime:
    def __init__(self, state_path: str | Path) -> None:
        self.path = Path(state_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.state: Dict[str, Any] = self._load()

    @staticmethod
    def empty_state() -> Dict[str, Any]:
        return {
            "stock": {},
            "service_recipes": {},
            "transactions": {},
            "ratings": [],
            "incidents": [],
            "maintenance": [],
            "offline_sync_queue": [],
            "audit": [],
        }

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self.empty_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            base = self.empty_state()
            if isinstance(data, dict):
                base.update(data)
            return base
        except Exception:
            return self.empty_state()

    def _save(self) -> None:
        payload = json.dumps(self.state, ensure_ascii=False, indent=2, sort_keys=True)
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name, dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _audit(self, event: str, payload: Mapping[str, Any]) -> None:
        self.state["audit"].append({"at": _utc_now(), "event": event, "payload": dict(payload)})

    def upsert_stock_item(self, item_id: str, *, name: str, quantity: float, unit: str, reorder_level: float = 0.0) -> Dict[str, Any]:
        if quantity < 0 or reorder_level < 0:
            raise ValueError("quantity and reorder_level cannot be negative")
        with self._lock:
            item = {"item_id": item_id, "name": name, "quantity": float(quantity), "unit": unit, "reorder_level": float(reorder_level), "updated_at": _utc_now()}
            self.state["stock"][item_id] = item
            self._audit("stock_upserted", {"item_id": item_id, "quantity": quantity})
            self._save()
            return dict(item)

    def set_service_recipe(self, service_id: str, consumables: Mapping[str, float]) -> Dict[str, float]:
        normalized = {str(item): float(qty) for item, qty in consumables.items()}
        if any(qty < 0 for qty in normalized.values()):
            raise ValueError("recipe quantity cannot be negative")
        with self._lock:
            self.state["service_recipes"][service_id] = normalized
            self._audit("service_recipe_updated", {"service_id": service_id, "items": list(normalized)})
            self._save()
            return dict(normalized)

    def complete_service(self, *, transaction_id: str, booking_id: str, customer_id: str, service_id: str, employee_id: str, sale_amount: float, commission_rate: float = 0.0, source: str = "web", online: bool = True) -> Dict[str, Any]:
        if sale_amount < 0 or not 0 <= commission_rate <= 1:
            raise ValueError("invalid financial values")
        with self._lock:
            existing = self.state["transactions"].get(transaction_id)
            if existing:
                return dict(existing)
            recipe = dict(self.state["service_recipes"].get(service_id) or {})
            shortages = []
            for item_id, qty in recipe.items():
                item = self.state["stock"].get(item_id)
                available = float((item or {}).get("quantity", 0.0))
                if available < qty:
                    shortages.append({"item_id": item_id, "required": qty, "available": available})
            if shortages:
                raise ValueError(f"insufficient_stock:{shortages}")
            consumed = []
            for item_id, qty in recipe.items():
                item = self.state["stock"][item_id]
                item["quantity"] = float(item["quantity"]) - qty
                item["updated_at"] = _utc_now()
                consumed.append({"item_id": item_id, "quantity": qty, "unit": item.get("unit")})
            transaction = {
                "transaction_id": transaction_id,
                "booking_id": booking_id,
                "customer_id": customer_id,
                "service_id": service_id,
                "employee_id": employee_id,
                "sale_amount": float(sale_amount),
                "commission_rate": float(commission_rate),
                "commission_amount": round(float(sale_amount) * float(commission_rate), 2),
                "consumed": consumed,
                "source": source,
                "sync_status": "synced" if online else "queued",
                "completed_at": _utc_now(),
            }
            self.state["transactions"][transaction_id] = transaction
            if not online:
                self.state["offline_sync_queue"].append({"kind": "service_transaction", "id": transaction_id, "queued_at": _utc_now()})
            self._audit("service_completed", {"transaction_id": transaction_id, "service_id": service_id, "employee_id": employee_id})
            self._save()
            return dict(transaction)

    def add_rating(self, *, transaction_id: str, employee_id: str, score: int, comment: str = "") -> Dict[str, Any]:
        if score not in {1, 2, 3, 4, 5}:
            raise ValueError("score must be 1..5")
        with self._lock:
            if transaction_id not in self.state["transactions"]:
                raise KeyError("transaction_not_found")
            existing = next((r for r in self.state["ratings"] if r["transaction_id"] == transaction_id), None)
            if existing:
                return dict(existing)
            rating = {"transaction_id": transaction_id, "employee_id": employee_id, "score": score, "comment": comment, "created_at": _utc_now()}
            self.state["ratings"].append(rating)
            self._audit("rating_recorded", rating)
            self._save()
            return dict(rating)

    def record_incident(self, *, incident_id: str, kind: str, item_id: str = "", quantity: float = 0.0, employee_id: str = "", department_id: str = "", verified: bool = False, evidence_ref: str = "", notes: str = "") -> Dict[str, Any]:
        allowed = {"damage", "waste", "loss", "misuse", "verified_vandalism", "maintenance"}
        if kind not in allowed:
            raise ValueError("unsupported_incident_kind")
        if kind == "verified_vandalism" and not verified:
            raise ValueError("vandalism_requires_verification")
        with self._lock:
            existing = next((i for i in self.state["incidents"] if i["incident_id"] == incident_id), None)
            if existing:
                return dict(existing)
            record = {"incident_id": incident_id, "kind": kind, "item_id": item_id, "quantity": float(quantity), "employee_id": employee_id, "department_id": department_id, "verified": bool(verified), "evidence_ref": evidence_ref, "notes": notes, "created_at": _utc_now()}
            self.state["incidents"].append(record)
            if kind == "maintenance":
                self.state["maintenance"].append(record)
            self._audit("incident_recorded", {"incident_id": incident_id, "kind": kind})
            self._save()
            return dict(record)

    def mark_synced(self, transaction_id: str) -> Dict[str, Any]:
        with self._lock:
            tx = self.state["transactions"].get(transaction_id)
            if not tx:
                raise KeyError("transaction_not_found")
            tx["sync_status"] = "synced"
            self.state["offline_sync_queue"] = [q for q in self.state["offline_sync_queue"] if q.get("id") != transaction_id]
            self._audit("offline_transaction_synced", {"transaction_id": transaction_id})
            self._save()
            return dict(tx)

    def operations_report(self) -> Dict[str, Any]:
        with self._lock:
            txs = list(self.state["transactions"].values())
            ratings = list(self.state["ratings"])
            stock = list(self.state["stock"].values())
            return {
                "sales_total": round(sum(float(t.get("sale_amount", 0)) for t in txs), 2),
                "commission_total": round(sum(float(t.get("commission_amount", 0)) for t in txs), 2),
                "services_completed": len(txs),
                "average_rating": round(sum(r["score"] for r in ratings) / len(ratings), 2) if ratings else None,
                "incidents_total": len(self.state["incidents"]),
                "maintenance_total": len(self.state["maintenance"]),
                "offline_pending": len(self.state["offline_sync_queue"]),
                "reorder_items": [dict(i) for i in stock if float(i.get("quantity", 0)) <= float(i.get("reorder_level", 0))],
                "generated_at": _utc_now(),
            }
