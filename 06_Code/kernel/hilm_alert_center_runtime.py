"""Persistent operational alert center for Hilm Alnada."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import uuid

CATEGORIES = {
    "inventory", "stockout", "reorder", "inventory_variance", "damage", "waste", "loss",
    "maintenance", "asset", "invoice", "payment", "supplier", "purchase_order", "attendance",
    "employee_performance", "sanitation", "booking", "customer", "complaint", "expiry", "administrative",
}
SEVERITIES = {"informational", "normal", "important", "urgent"}
STATUSES = {"new", "seen", "in_progress", "resolved"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HilmAlertCenterRuntime:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"alerts": {}, "history": []})

    def _read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"alerts": {}, "history": []}

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def create_alert(self, *, category: str, title: str, message: str, severity: str = "normal",
                     department_id: str = "", employee_id: str = "", item_id: str = "",
                     assignee: str = "nada", due_at: str = "", root_cause_key: str = "",
                     source_ref: str = "") -> Dict[str, Any]:
        if category not in CATEGORIES:
            raise ValueError("unsupported_alert_category")
        if severity not in SEVERITIES:
            raise ValueError("unsupported_alert_severity")
        if not title.strip() or not message.strip():
            raise ValueError("alert_title_and_message_required")
        data = self._read()
        dedupe_key = "|".join([category, department_id, employee_id, item_id, root_cause_key, title.strip().lower()])
        for alert in data["alerts"].values():
            if alert.get("dedupe_key") == dedupe_key and alert.get("status") != "resolved":
                alert["repeat_count"] = int(alert.get("repeat_count", 1)) + 1
                alert["updated_at"] = _now()
                alert["message"] = message
                self._write(data)
                return dict(alert)
        alert_id = f"alert_{uuid.uuid4().hex[:16]}"
        alert = {
            "alert_id": alert_id, "category": category, "severity": severity, "status": "new",
            "title": title.strip(), "message": message.strip(), "department_id": department_id,
            "employee_id": employee_id, "item_id": item_id, "assignee": assignee, "due_at": due_at,
            "root_cause_key": root_cause_key, "source_ref": source_ref, "dedupe_key": dedupe_key,
            "repeat_count": 1, "created_at": _now(), "updated_at": _now(), "resolved_at": "",
            "actions": [], "ameer_review_status": "pending",
        }
        data["alerts"][alert_id] = alert
        data["history"].append({"at": _now(), "alert_id": alert_id, "event": "created"})
        self._write(data)
        return dict(alert)

    def transition(self, alert_id: str, status: str, *, actor: str, action: str = "") -> Dict[str, Any]:
        if status not in STATUSES:
            raise ValueError("unsupported_alert_status")
        data = self._read()
        if alert_id not in data["alerts"]:
            raise KeyError("alert_not_found")
        alert = data["alerts"][alert_id]
        alert["status"] = status
        alert["updated_at"] = _now()
        if status == "resolved":
            alert["resolved_at"] = _now()
        if action:
            alert["actions"].append({"at": _now(), "actor": actor, "action": action})
        data["history"].append({"at": _now(), "alert_id": alert_id, "event": status, "actor": actor})
        self._write(data)
        return dict(alert)

    def ameer_review(self, alert_ids: Iterable[str], *, review_note: str = "") -> List[Dict[str, Any]]:
        data = self._read()
        reviewed = []
        for alert_id in alert_ids:
            alert = data["alerts"].get(alert_id)
            if not alert:
                continue
            alert["ameer_review_status"] = "reviewed"
            alert["ameer_reviewed_at"] = _now()
            alert["ameer_review_note"] = review_note
            reviewed.append(dict(alert))
        self._write(data)
        return reviewed

    def list_alerts(self, *, category: str = "", severity: str = "", status: str = "",
                    department_id: str = "", employee_id: str = "") -> List[Dict[str, Any]]:
        alerts = list(self._read()["alerts"].values())
        filters = {"category": category, "severity": severity, "status": status,
                   "department_id": department_id, "employee_id": employee_id}
        for key, value in filters.items():
            if value:
                alerts = [a for a in alerts if a.get(key) == value]
        return sorted(alerts, key=lambda a: (a.get("severity") == "urgent", a.get("created_at", "")), reverse=True)

    def printable_report(self) -> Dict[str, Any]:
        alerts = self.list_alerts()
        return {
            "generated_at": _now(), "printable": True, "exportable": True,
            "counts": {status: sum(1 for a in alerts if a.get("status") == status) for status in STATUSES},
            "alerts": alerts,
        }

    def purchase_digest_source(self) -> Dict[str, Any]:
        active = [a for a in self.list_alerts() if a["status"] != "resolved" and a["category"] in {"stockout", "reorder", "inventory"}]
        items = {}
        for alert in active:
            key = alert.get("item_id") or alert["alert_id"]
            row = items.setdefault(key, {"item_id": alert.get("item_id", ""), "alerts": 0, "departments": set(), "severity": alert["severity"]})
            row["alerts"] += int(alert.get("repeat_count", 1))
            if alert.get("department_id"):
                row["departments"].add(alert["department_id"])
            if alert["severity"] == "urgent":
                row["severity"] = "urgent"
        normalized = []
        for row in items.values():
            row["departments"] = sorted(row["departments"])
            normalized.append(row)
        return {"distinct_items": len(normalized), "items": normalized, "source_of_truth": "hilm_alert_center"}
