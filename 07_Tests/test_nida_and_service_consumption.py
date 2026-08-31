import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_service_material_consumption_supports_expected_vs_actual_tracking():
    mod = _load("service_material_consumption")
    contract = mod.service_material_consumption_contract()
    assert contract.service_material_standards_supported is True
    assert contract.standards_can_vary_by_service_dimensions is True
    assert contract.actual_issue_and_return_are_recorded is True
    assert contract.net_consumption_is_compared_to_standard is True
    assert contract.significant_variance_is_flagged is True
    assert contract.variance_does_not_create_automatic_employee_penalty is True
    assert "hair_length" in mod.VARIANT_DIMENSION_EXAMPLES
    assert "hair_density" in mod.VARIANT_DIMENSION_EXAMPLES


def test_consumption_standards_are_versioned_for_historical_costing():
    mod = _load("service_material_consumption")
    contract = mod.service_material_consumption_contract()
    assert contract.standards_are_versioned is True
    assert contract.historic_service_costing_keeps_original_standard_version is True
    assert "standard_version" in mod.CONSUMPTION_COMPARISON_FIELDS


def test_nida_is_scoped_operations_worker_under_ameer():
    mod = _load("nida_operations_worker")
    contract = mod.nida_operations_worker_contract()
    assert contract.worker_id == "nida"
    assert contract.arabic_name == "ندى"
    assert contract.ameer_is_supervising_orchestrator is True
    assert contract.nida_has_no_sovereign_authority is True
    assert contract.nida_handles_pos_invoicing_and_warehouses is True


def test_nida_cannot_post_unverified_document_extraction_or_bypass_governance():
    mod = _load("nida_operations_worker")
    contract = mod.nida_operations_worker_contract()
    assert contract.unverified_document_extraction_cannot_post_stock is True
    assert "silently_overwrite_confirmed_inventory_from_unverified_ocr" in mod.NIDA_MUST_NOT
    assert "bypass_ameer_or_project_permissions" in mod.NIDA_MUST_NOT


def test_nida_monitors_material_variance_and_escalates_patterns_to_ameer():
    consumption = _load("service_material_consumption")
    nida = _load("nida_operations_worker")
    assert consumption.service_material_consumption_contract().nida_monitors_variances is True
    assert consumption.service_material_consumption_contract().ameer_reviews_repeated_or_significant_patterns is True
    assert "repeated_material_consumption_variance" in nida.NIDA_ESCALATION_TRIGGERS
