import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_all_current_and_future_sellable_departments_use_shared_commerce():
    mod = _load("hilm_universal_commerce_policy")
    contract = mod.hilm_universal_commerce_contract()
    assert contract.every_current_sellable_department_uses_shared_cart is True
    assert contract.every_current_sellable_department_uses_shared_payment_gateway is True
    assert contract.every_future_sellable_department_inherits_shared_cart is True
    assert contract.every_future_sellable_department_inherits_shared_payment_gateway is True


def test_services_and_products_resolve_from_canonical_catalogs():
    mod = _load("hilm_universal_commerce_policy")
    contract = mod.hilm_universal_commerce_contract()
    assert contract.service_names_and_prices_come_from_canonical_catalog is True
    assert contract.product_names_and_prices_come_from_canonical_product_catalog is True
    assert contract.department_screens_are_not_independent_price_sources is True
    assert contract.canonical_price_change_propagates_to_all_commerce_surfaces is True
    assert "never_invent_missing_price_in_department_flow" in mod.CATALOG_SOURCE_RULES


def test_shared_checkout_covers_rooms_coffee_addons_and_future_departments():
    mod = _load("checkout_payment_architecture")
    contract = mod.checkout_payment_contract()
    assert contract.all_current_sellable_departments_use_shared_cart_and_gateway is True
    assert contract.future_sellable_departments_inherit_shared_cart_and_gateway is True
    assert contract.room_and_vip_bookings_use_shared_gateway is True
    assert contract.coffee_and_food_addons_use_shared_gateway is True
    assert "future_registered_sellable_department_item" in mod.PAYABLE_COMMERCE_TYPES
    assert "resolve_current_item_names_and_prices_from_canonical_catalogs" in mod.CHECKOUT_FLOW
