import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_room_surfaces_support_catalog_driven_addons():
    mod = _load("room_experience_addons_catalog")
    contract = mod.room_experience_addons_contract()
    assert contract.celebration_room_uses_catalog_packages is True
    assert contract.vip_and_relaxation_rooms_support_catalog_addons is True
    assert contract.coffee_items_selectable_with_prices is True
    assert contract.spa_and_massage_items_selectable_with_prices is True
    assert contract.facial_items_selectable_with_prices is True
    assert contract.bridal_services_selectable_with_prices is True


def test_verified_catalog_prices_include_room_bridal_facial_massage_and_coffee():
    mod = _load("room_experience_addons_catalog")
    prices = mod.VERIFIED_CATALOG_PRICES
    assert prices["celebration_basic_package"] == 450
    assert prices["celebration_distinguished_package"] == 650
    assert prices["celebration_luxury_package"] == 850
    assert prices["relaxation_room_30_minutes"] == 80
    assert prices["relaxation_room_60_minutes"] == 120
    assert prices["relaxation_room_vip_90_minutes"] == 180
    assert prices["bridal_makeup"] == 800
    assert prices["hydrafacial"] == 499
    assert prices["classic_relaxation_massage_60"] == 400
    assert prices["espresso"] == 18
    assert prices["margherita_pizza"] == 28


def test_room_addons_never_fork_canonical_prices_and_use_shared_checkout():
    mod = _load("room_experience_addons_catalog")
    rules = mod.CATALOG_LINK_RULES
    flow = mod.ROOM_EXPERIENCE_BOOKING_FLOW
    assert "room_addons_never_duplicate_or_fork_service_prices" in rules
    assert "price_is_reloaded_at_checkout" in rules
    assert "moroccan_bath_appears_only_when_a_canonical_price_is_configured" in rules
    assert "checkout_through_shared_payment_gateway" in flow
    assert "create_single_composite_booking" in flow
    assert "hilm_follows_customer_and_coordinates_selected_services" in flow
