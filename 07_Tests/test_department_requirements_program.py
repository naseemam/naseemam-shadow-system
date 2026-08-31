from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "06_Code" / "kernel" / "department_requirements_program.py"
spec = spec_from_file_location("department_requirements_program", MODULE)
mod = module_from_spec(spec)
spec.loader.exec_module(mod)


def test_catalog_departments_and_home_visits_are_registered():
    assert "hair" in mod.CATALOG_DEPARTMENTS
    assert "coffee_lounge" in mod.CATALOG_DEPARTMENTS
    assert "tailoring" in mod.CATALOG_DEPARTMENTS
    assert "home_visits" in mod.ADDITIONAL_OPERATIONAL_DEPARTMENTS


def test_requirements_cover_setup_operations_and_lifecycle():
    required = {
        "fixed_assets_and_equipment",
        "reusable_tools",
        "operating_materials",
        "single_use_consumables",
        "cleaning_and_disinfection",
        "maintenance_requirements",
        "damage_and_replacement",
        "minimum_stock_and_reorder_point",
    }
    assert required.issubset(set(mod.REQUIREMENT_CATEGORIES))


def test_unverified_exact_items_are_not_invented():
    assert "exact_equipment_brand_quantity_or_specification_must_not_be_invented" in mod.REQUIREMENT_SOURCE_RULES
    assert "unverified_exact_items_remain_blank_until_setup_review" in mod.REQUIREMENT_SOURCE_RULES


def test_home_visit_department_has_independent_kit_and_stock():
    rules = set(mod.HOME_VISIT_RULES)
    assert "home_visits_have_separate_portable_assets" in rules
    assert "home_visits_have_separate_operating_stock" in rules
    assert "home_visits_have_separate_consumable_stock" in rules
    assert "fixed_center_assets_are_not_removed_for_visits_by_default" in rules
    assert "temporary_transfer_from_center_requires_recorded_custody_transfer" in rules


def test_printable_register_has_custody_maintenance_and_reorder_fields():
    fields = set(mod.PRINTABLE_SETUP_FIELDS)
    for field in (
        "department_lead",
        "responsible_employee",
        "setup_quantity",
        "minimum_quantity",
        "reorder_point",
        "maintenance_frequency",
        "damage_status",
        "replacement_required",
    ):
        assert field in fields


def test_nada_and_ameer_roles_are_preserved():
    contract = mod.requirements_contract()
    assert contract.nada_operates_daily_tracking is True
    assert contract.ameer_monitors_exceptions_and_cross_department_patterns is True
    assert contract.home_visit_stock_is_independent is True
    assert contract.no_unverified_exact_items_are_invented is True
