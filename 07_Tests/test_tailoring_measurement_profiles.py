import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_customer_account_supports_multiple_measurement_profiles():
    mod = _load("tailoring_online_order")
    contract = mod.tailoring_online_order_contract()
    assert contract.customer_account_supports_multiple_measurement_profiles is True
    assert contract.measurement_profiles_may_represent_self_or_other_people is True
    assert contract.each_order_selects_one_measurement_profile is True
    assert contract.order_keeps_measurement_snapshot_for_historical_accuracy is True


def test_measurement_profile_identifies_relationship_and_optional_name():
    mod = _load("tailoring_online_order")
    assert "measurement_profile_id" in mod.MEASUREMENT_PROFILE_FIELDS
    assert "profile_label" in mod.MEASUREMENT_PROFILE_FIELDS
    assert "person_name_optional" in mod.MEASUREMENT_PROFILE_FIELDS
    assert "relationship_label" in mod.MEASUREMENT_PROFILE_FIELDS
    assert "أنا" in mod.MEASUREMENT_PROFILE_RELATIONSHIP_EXAMPLES
    assert "ابنتي" in mod.MEASUREMENT_PROFILE_RELATIONSHIP_EXAMPLES
    assert "أمي" in mod.MEASUREMENT_PROFILE_RELATIONSHIP_EXAMPLES
    assert "أختي" in mod.MEASUREMENT_PROFILE_RELATIONSHIP_EXAMPLES
    assert "ابنة أخي" in mod.MEASUREMENT_PROFILE_RELATIONSHIP_EXAMPLES


def test_tailoring_order_references_profile_and_snapshots_measurements():
    mod = _load("tailoring_online_order")
    assert "measurement_profile_id" in mod.TAILORING_ORDER_FIELDS
    assert "measurement_profile_version" in mod.TAILORING_ORDER_FIELDS
    assert "measurements_snapshot" in mod.TAILORING_ORDER_FIELDS
    assert "select_or_create_measurement_profile" in mod.TAILORING_ORDER_FLOW
    assert "snapshot_selected_measurement_profile_for_order" in mod.TAILORING_ORDER_FLOW


def test_cashier_can_print_complete_tailoring_work_order_for_tailor():
    mod = _load("tailoring_online_order")
    contract = mod.tailoring_online_order_contract()
    assert contract.employee_can_print_complete_tailoring_work_order is True
    assert contract.printed_work_order_includes_name_order_number_phone_and_measurements is True
    assert contract.tailor_receives_operational_work_order_without_customer_reentry is True
    required = {
        "order_number",
        "customer_name",
        "customer_phone",
        "measurements_snapshot",
        "measurement_profile_label",
        "garment_type",
        "tailoring_service",
    }
    assert required.issubset(set(mod.PRINTABLE_TAILORING_WORK_ORDER_FIELDS))
    assert "generate_printable_tailoring_work_order" in mod.TAILORING_ORDER_FLOW
    assert "employee_prints_and_hands_work_order_to_tailor" in mod.TAILORING_ORDER_FLOW


def test_tailoring_supports_customer_alterations_and_images_across_services():
    mod = _load("tailoring_online_order")
    contract = mod.tailoring_online_order_contract()
    assert contract.alteration_requests_supported_across_tailoring_services is True
    assert contract.alteration_images_supported is True
    assert contract.printed_work_order_includes_alterations_and_image_references is True
    assert "alteration_notes" in mod.PRINTABLE_TAILORING_WORK_ORDER_FIELDS
    assert "reference_image_thumbnails_or_references" in mod.PRINTABLE_TAILORING_WORK_ORDER_FIELDS
    assert "capture_alteration_requests_when_applicable" in mod.TAILORING_ORDER_FLOW
    assert "attach_alteration_reference_images_when_available" in mod.TAILORING_ORDER_FLOW


def test_hilm_follows_tailoring_customer_through_alterations_and_completion():
    mod = _load("tailoring_online_order")
    contract = mod.tailoring_online_order_contract()
    assert contract.hilm_tracks_tailoring_customer_end_to_end is True
    assert contract.hilm_tracks_alteration_and_fitting_status is True
    assert "sent_to_tailor" in mod.HILM_TAILORING_FOLLOWUP_STATES
    assert "alteration_requested" in mod.HILM_TAILORING_FOLLOWUP_STATES
    assert "alteration_in_progress" in mod.HILM_TAILORING_FOLLOWUP_STATES
    assert "ready_for_pickup_or_delivery" in mod.HILM_TAILORING_FOLLOWUP_STATES
    assert "hilm_follows_customer_and_order_status" in mod.TAILORING_ORDER_FLOW
