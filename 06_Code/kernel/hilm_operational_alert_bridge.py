"""Translate real Hilm operational state into deduplicated alerts."""
from __future__ import annotations

from typing import Any, Dict


def sync_operations_to_alerts(operations, alerts) -> Dict[str, int]:
    report = operations.operations_report()
    created_or_updated = 0

    for item in report.get("reorder_items") or []:
        quantity = float(item.get("quantity", 0))
        reorder = float(item.get("reorder_level", 0))
        severity = "urgent" if quantity <= 0 else "important"
        alerts.create_alert(
            category="stockout" if quantity <= 0 else "reorder",
            title=f"مخزون منخفض: {item.get('name') or item.get('item_id')}",
            message=f"الرصيد الحالي {quantity:g} {item.get('unit') or ''}، حد إعادة الطلب {reorder:g}",
            severity=severity,
            item_id=str(item.get("item_id") or ""),
            assignee="nada",
            root_cause_key="inventory_reorder_level",
            source_ref=f"stock:{item.get('item_id')}",
        )
        created_or_updated += 1

    state = getattr(operations, "state", {}) or {}
    for incident in state.get("incidents") or []:
        kind = str(incident.get("kind") or "")
        category = "maintenance" if kind == "maintenance" else kind if kind in {"damage", "waste", "loss"} else "administrative"
        severity = "important" if kind in {"maintenance", "damage", "loss", "verified_vandalism"} else "normal"
        alerts.create_alert(
            category=category,
            title=f"حالة تشغيلية: {kind}",
            message=str(incident.get("notes") or f"تم تسجيل {kind}"),
            severity=severity,
            department_id=str(incident.get("department_id") or ""),
            employee_id=str(incident.get("employee_id") or ""),
            item_id=str(incident.get("item_id") or ""),
            assignee="nada",
            root_cause_key=str(incident.get("incident_id") or kind),
            source_ref=f"incident:{incident.get('incident_id')}",
        )
        created_or_updated += 1

    return {"created_or_updated": created_or_updated, "reorder_items": len(report.get("reorder_items") or [])}
