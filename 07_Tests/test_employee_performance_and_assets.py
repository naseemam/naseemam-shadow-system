import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_consumption_rankings_are_contextual_not_raw_only():
    mod = _load("employee_performance_and_assets")
    contract = mod.employee_performance_asset_contract()
    assert contract.highest_and_lowest_consumption_rankings_supported is True
    assert contract.consumption_must_be_normalized_by_service_volume_and_standard is True
    assert "compare_consumption_to_completed_service_volume" in mod.EMPLOYEE_CONSUMPTION_ANALYTICS
    assert "compare_actual_to_standard_consumption" in mod.EMPLOYEE_CONSUMPTION_ANALYTICS


def test_fixed_assets_have_department_and_employee_accountability():
    mod = _load("employee_performance_and_assets")
    assert "department_id" in mod.FIXED_ASSET_FIELDS
    assert "responsible_employee_id" in mod.FIXED_ASSET_FIELDS
    assert "handover_receipt_reference" in mod.FIXED_ASSET_FIELDS
    assert "photos" in mod.FIXED_ASSET_FIELDS
    assert "record_condition_and_photos_at_handover" in mod.ASSET_ACCOUNTABILITY_FLOW


def test_workforce_behavior_cleaning_and_tool_care_are_tracked():
    mod = _load("employee_performance_and_assets")
    contract = mod.employee_performance_asset_contract()
    assert contract.attendance_and_lateness_tracked is True
    assert contract.operational_delay_events_supported is True
    assert contract.cleaning_and_sterilization_compliance_tracked is True
    assert contract.tool_neglect_and_damage_tracked is True
    assert "sterilization_noncompliance" in mod.EMPLOYEE_BEHAVIOR_AND_COMPLIANCE_EVENTS
    assert "asset_damage" in mod.EMPLOYEE_BEHAVIOR_AND_COMPLIANCE_EVENTS


def test_bonus_is_monthly_multifactor_and_not_automatic_salary_penalty():
    mod = _load("employee_performance_and_assets")
    contract = mod.employee_performance_asset_contract()
    assert contract.monthly_multi_factor_bonus_supported is True
    assert contract.operational_flags_do_not_auto_deduct_salary is True
    assert mod.BONUS_POLICY_GUIDANCE["period"] == "monthly_after_month_close"
    assert mod.BONUS_POLICY_GUIDANCE["recommended_target_percent_of_base_salary"] == 10
    assert mod.BONUS_POLICY_GUIDANCE["single_metric_bonus_prohibited"] is True
    assert mod.BONUS_POLICY_GUIDANCE["automatic_salary_penalty_from_operational_flags"] is False


def test_management_program_is_split_into_specialized_areas():
    mod = _load("employee_performance_and_assets")
    required = {
        "cashier_and_invoicing",
        "retail_inventory",
        "operational_inventory",
        "fixed_assets",
        "employees_and_hr",
        "attendance_and_time",
        "performance_and_bonus",
        "cleaning_and_sterilization",
        "service_quality",
        "maintenance",
    }
    assert required.issubset(set(mod.MANAGEMENT_PROGRAM_AREAS))
