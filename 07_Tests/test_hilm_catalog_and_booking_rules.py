from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "06_Code" / "kernel" / "hilm_catalog_and_booking_rules.py"
spec = spec_from_file_location("hilm_catalog_and_booking_rules", MODULE_PATH)
module = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_catalog_contains_required_storefront_sections():
    required = {
        "hair",
        "makeup",
        "eyebrows",
        "lashes",
        "lips",
        "nails",
        "facial",
        "manicure_pedicure",
        "hair_removal",
        "massage",
        "relaxation_room",
        "celebration_room",
        "coffee_lounge",
        "tailoring",
        "offers",
    }
    assert required.issubset(set(module.CATALOG_SECTIONS))


def test_catalog_uses_dynamic_offers_section():
    assert module.SERVICE_CATALOG["offers"] == ()
    assert module.booking_rule_contract().offers_are_dynamic_and_separate_from_base_catalog


def test_time_is_mandatory_for_every_booking():
    contract = module.booking_rule_contract()
    assert contract.every_booking_requires_start_time
    assert contract.booking_duration_required
    assert contract.end_time_is_derived_or_explicit
    assert contract.employee_conflict_check_required
    assert contract.resource_conflict_check_required


def test_rooms_are_time_bound_and_rechecked():
    contract = module.booking_rule_contract()
    assert contract.celebration_room_requires_time_slot
    assert contract.relaxation_room_requires_time_slot
    assert "recheck_availability_after_addons" in module.CROSS_SELL_RULES["before_checkout"]


def test_hilm_cross_sells_coffee_room_and_offer_during_booking():
    rules = module.CROSS_SELL_RULES["during_any_service_booking"]
    assert "offer_coffee_lounge_preorder" in rules
    assert "offer_relaxation_room_when_timing_allows" in rules
    assert "offer_celebration_room_when_context_suggests_occasion" in rules
    assert "offer_relevant_active_offer_or_package" in rules


def test_coffee_can_be_ordered_from_store_and_attached_to_booking():
    contract = module.booking_rule_contract()
    assert contract.coffee_order_can_be_preordered_from_store
    assert contract.coffee_order_can_attach_to_booking


def test_catalog_has_source_prices_for_key_sections():
    hair = {item["name"]: item for item in module.SERVICE_CATALOG["hair"]}
    massage = {item["name"]: item for item in module.SERVICE_CATALOG["massage"]}
    coffee = {item["name"]: item for item in module.SERVICE_CATALOG["coffee_lounge"]}
    celebration = {item["name"]: item for item in module.SERVICE_CATALOG["celebration_room"]}
    assert hair["هيد سبا"]["price"] == 399
    assert massage["مساج كلاسيك"]["price"] == 400
    assert coffee["اسبريسو"]["price"] == 18
    assert celebration["الباقة الأساسية"]["price"] == 450
