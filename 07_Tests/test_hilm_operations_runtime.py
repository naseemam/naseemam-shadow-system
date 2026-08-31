from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.hilm_operations_runtime import HilmOperationsRuntime


def test_service_completion_consumes_stock_calculates_commission_and_is_idempotent():
    with TemporaryDirectory() as td:
        runtime = HilmOperationsRuntime(Path(td) / "ops.json")
        runtime.upsert_stock_item("glove", name="قفازات", quantity=10, unit="pair", reorder_level=2)
        runtime.set_service_recipe("svc-1", {"glove": 2})
        first = runtime.complete_service(transaction_id="tx-1", booking_id="b-1", customer_id="c-1", service_id="svc-1", employee_id="e-1", sale_amount=200, commission_rate=0.10)
        second = runtime.complete_service(transaction_id="tx-1", booking_id="b-1", customer_id="c-1", service_id="svc-1", employee_id="e-1", sale_amount=200, commission_rate=0.10)
        assert first == second
        assert first["commission_amount"] == 20.0
        assert runtime.state["stock"]["glove"]["quantity"] == 8.0
        assert runtime.operations_report()["services_completed"] == 1


def test_local_offline_sale_queues_and_later_syncs_without_duplicate_consumption():
    with TemporaryDirectory() as td:
        runtime = HilmOperationsRuntime(Path(td) / "ops.json")
        runtime.upsert_stock_item("oil", name="زيت", quantity=5, unit="bottle")
        runtime.set_service_recipe("massage", {"oil": 1})
        tx = runtime.complete_service(transaction_id="local-1", booking_id="b-2", customer_id="c-2", service_id="massage", employee_id="e-2", sale_amount=400, source="local", online=False)
        assert tx["sync_status"] == "queued"
        assert runtime.operations_report()["offline_pending"] == 1
        runtime.mark_synced("local-1")
        assert runtime.operations_report()["offline_pending"] == 0
        assert runtime.state["stock"]["oil"]["quantity"] == 4.0


def test_rating_incidents_and_verified_vandalism_rule():
    with TemporaryDirectory() as td:
        runtime = HilmOperationsRuntime(Path(td) / "ops.json")
        runtime.complete_service(transaction_id="tx-rating", booking_id="b", customer_id="c", service_id="s", employee_id="e", sale_amount=100)
        rating = runtime.add_rating(transaction_id="tx-rating", employee_id="e", score=5, comment="ممتاز")
        assert rating["score"] == 5
        runtime.record_incident(incident_id="m-1", kind="maintenance", item_id="dryer-1", notes="فحص")
        try:
            runtime.record_incident(incident_id="v-1", kind="verified_vandalism", item_id="dryer-1", verified=False)
        except ValueError as exc:
            assert "verification" in str(exc)
        else:
            raise AssertionError("unverified vandalism must not be recorded")
        runtime.record_incident(incident_id="v-2", kind="verified_vandalism", item_id="dryer-1", verified=True, evidence_ref="case-22")
        report = runtime.operations_report()
        assert report["maintenance_total"] == 1
        assert report["incidents_total"] == 2


def test_state_persists_across_runtime_restart():
    with TemporaryDirectory() as td:
        path = Path(td) / "ops.json"
        runtime = HilmOperationsRuntime(path)
        runtime.upsert_stock_item("mask", name="ماسك", quantity=7, unit="piece")
        restarted = HilmOperationsRuntime(path)
        assert restarted.state["stock"]["mask"]["quantity"] == 7.0
