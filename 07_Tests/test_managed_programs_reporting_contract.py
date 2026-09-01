from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.managed_programs_reporting_contract import program_contract


def test_every_program_is_managed_printable_and_analytical():
    contract = program_contract()
    capabilities = set(contract["required_capabilities"])
    analytics = set(contract["required_analytics"])
    reports = set(contract["printable_reports"])

    assert contract["applies_to_existing_programs"] is True
    assert contract["applies_to_future_programs"] is True
    assert contract["analytics_are_not_optional_addons"] is True
    assert contract["data_entry_editing_and_printing_are_first_class_features"] is True

    assert {"create_records", "edit_records", "print_forms", "print_reports", "analytics_dashboard"}.issubset(capabilities)
    assert {"inventory_variance", "damage", "waste", "maintenance_due", "cost_impact"}.issubset(analytics)
    assert {"monthly_management_report", "inventory_count_report", "damage_waste_loss_report", "maintenance_and_asset_report"}.issubset(reports)


def test_ameer_and_specialist_worker_manage_each_program():
    management = program_contract()["management_model"]
    assert management["primary_operational_manager"] == "ameer"
    assert management["responsible_specialist_worker_required"] is True
    assert management["worker_examples"]["billing_pos_inventory_warehouses"] == "nada"
    assert management["founder_manual_micro_management_required"] is False


def test_reports_are_printable_traceable_and_snapshot_safe():
    req = program_contract()["report_requirements"]
    assert req["printable"] is True
    assert req["editable_before_finalization"] is True
    assert req["show_source_transactions"] is True
    assert req["show_calculation_basis"] is True
    assert req["show_variance_and_cost_impact"] is True
    assert req["retain_historical_snapshots"] is True
    assert req["finalized_reports_are_immutable_snapshots"] is True
