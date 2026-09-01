from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.hilm_alert_center_runtime import HilmAlertCenterRuntime


def test_alert_lifecycle_dedup_and_report(tmp_path):
    runtime = HilmAlertCenterRuntime(tmp_path / "alerts.json")
    first = runtime.create_alert(category="reorder", title="Shampoo low", message="2 units remain", severity="important", department_id="hair", item_id="shampoo", root_cause_key="low_stock")
    second = runtime.create_alert(category="reorder", title="Shampoo low", message="1 unit remains", severity="urgent", department_id="hair", item_id="shampoo", root_cause_key="low_stock")
    assert first["alert_id"] == second["alert_id"]
    assert second["repeat_count"] == 2
    transitioned = runtime.transition(first["alert_id"], "in_progress", actor="nada", action="checked warehouse")
    assert transitioned["status"] == "in_progress"
    reviewed = runtime.ameer_review([first["alert_id"]], review_note="include in purchase digest")
    assert reviewed[0]["ameer_review_status"] == "reviewed"
    report = runtime.printable_report()
    assert report["printable"] is True
    assert report["exportable"] is True


def test_purchase_digest_aggregates_items_not_messages(tmp_path):
    runtime = HilmAlertCenterRuntime(tmp_path / "alerts.json")
    runtime.create_alert(category="stockout", title="Gloves", message="empty", severity="urgent", department_id="facial", item_id="gloves", root_cause_key="stock")
    runtime.create_alert(category="stockout", title="Gloves", message="still empty", severity="urgent", department_id="facial", item_id="gloves", root_cause_key="stock")
    runtime.create_alert(category="reorder", title="Oil", message="low", department_id="massage", item_id="oil", root_cause_key="stock")
    digest = runtime.purchase_digest_source()
    assert digest["distinct_items"] == 2
    gloves = next(row for row in digest["items"] if row["item_id"] == "gloves")
    assert gloves["alerts"] == 2
    assert digest["source_of_truth"] == "hilm_alert_center"
