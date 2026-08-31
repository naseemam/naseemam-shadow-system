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
