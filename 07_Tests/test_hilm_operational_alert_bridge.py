from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.hilm_alert_center_runtime import HilmAlertCenterRuntime
from kernel.hilm_operations_runtime import HilmOperationsRuntime
from kernel.hilm_operational_alert_bridge import sync_operations_to_alerts


def test_low_stock_and_incidents_become_deduplicated_alerts(tmp_path):
    operations = HilmOperationsRuntime(tmp_path / "operations.json")
    alerts = HilmAlertCenterRuntime(tmp_path / "alerts.json")
    operations.upsert_stock_item("oil", name="Massage oil", quantity=1, unit="bottle", reorder_level=2)
    operations.record_incident(incident_id="m1", kind="maintenance", item_id="bed-1", department_id="massage", notes="service due")
    first = sync_operations_to_alerts(operations, alerts)
    second = sync_operations_to_alerts(operations, alerts)
    assert first["reorder_items"] == 1
    assert second["reorder_items"] == 1
    current = alerts.list_alerts()
    assert len(current) == 2
    reorder = next(a for a in current if a["category"] == "reorder")
    assert reorder["repeat_count"] == 2
    maintenance = next(a for a in current if a["category"] == "maintenance")
    assert maintenance["assignee"] == "nada"
