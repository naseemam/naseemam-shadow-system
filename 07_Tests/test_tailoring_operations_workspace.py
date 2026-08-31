import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_cashier_can_capture_in_person_measurements_into_customer_profile():
    mod = _load("tailoring_operations_workspace")
    contract = mod.tailoring_operations_contract()
    assert contract.cashier_can_capture_in_person_measurements is True
    assert contract.cashier_measurements_save_to_customer_measurement_profile is True
    assert contract.cashier_can_select_existing_family_measurement_profile is True
    assert "save_new_version_to_customer_measurement_profile" in mod.IN_PERSON_CASHIER_MEASUREMENT_FLOW
    assert "snapshot_measurements_for_order" in mod.IN_PERSON_CASHIER_MEASUREMENT_FLOW


def test_tailoring_dashboard_tracks_full_operational_journey():
    mod = _load("tailoring_operations_workspace")
    contract = mod.tailoring_operations_contract()
    assert contract.tailoring_has_dedicated_operations_dashboard is True
    assert contract.tracks_customer_volume_and_active_orders is True
    assert contract.tracks_measurement_fabric_tailoring_fitting_alteration_delivery is True
    assert "active_customer_count" in mod.TAILORING_DASHBOARD_VIEWS
    assert "overdue_orders" in mod.TAILORING_DASHBOARD_VIEWS
    assert "fabric_received" in mod.TAILORING_WORKFLOW_STAGES
    assert "cutting" in mod.TAILORING_WORKFLOW_STAGES
    assert "sewing" in mod.TAILORING_WORKFLOW_STAGES
    assert "delivered" in mod.TAILORING_WORKFLOW_STAGES


def test_manual_paper_capture_is_fast_but_cannot_silently_corrupt_measurements():
    mod = _load("tailoring_operations_workspace")
    contract = mod.tailoring_operations_contract()
    assert contract.supports_manual_form_scan_or_photo_attachment is True
    assert contract.extracted_manual_form_data_is_draft_until_confirmed is True
    assert contract.source_image_is_retained_for_audit is True
    assert "mark_extracted_values_as_unverified_draft" in mod.PAPER_CAPTURE_FLOW
    assert "authorized_employee_reviews_and_confirms" in mod.PAPER_CAPTURE_FLOW
    assert "paper_extraction_never_overwrites_canonical_data_without_human_confirmation" in mod.ERROR_PREVENTION_RULES


def test_hilm_and_staff_share_one_canonical_tailoring_order():
    mod = _load("tailoring_operations_workspace")
    contract = mod.tailoring_operations_contract()
    assert contract.hilm_follows_customer_across_tailoring_stages is True
    assert contract.canonical_order_shared_with_cashier_management_and_tailor is True
    assert "cashier_tailor_management_and_hilm_share_the_same_canonical_order" in mod.ERROR_PREVENTION_RULES
