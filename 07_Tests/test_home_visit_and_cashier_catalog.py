import importlib.util
from pathlib import Path


def _load(name, relative_path):
    root = Path(__file__).resolve().parents[1]
    path = root / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog = _load("hilm_catalog_and_booking_rules", "06_Code/kernel/hilm_catalog_and_booking_rules.py")
module = _load("home_visit_and_cashier_catalog", "06_Code/kernel/home_visit_and_cashier_catalog.py")


def test_cashier_receives_all_catalog_services_and_prices():
    expected = sum(len(services) for services in catalog.SERVICE_CATALOG.values())
    assert len(module.CASHIER_SERVICE_CATALOG) == expected
    assert all("name" in row and "price" in row for row in module.CASHIER_SERVICE_CATALOG)


def test_home_visit_uses_per_service_surcharge_without_inventing_amount():
    result = module.home_visit_price("example", 100, None)
    assert result["base_price"] == 100
    assert result["final_price"] is None
    assert result["status"] == "surcharge_configuration_required"


def test_home_visit_final_price_is_base_plus_surcharge():
    result = module.home_visit_price("example", 100, 35)
    assert result["final_price"] == 135
    assert result["status"] == "priced"


def test_contract_requires_shared_service_source_of_truth():
    contract = module.home_visit_and_cashier_contract()
    assert contract.home_visit_has_per_service_surcharge is True
    assert contract.cashier_uses_entire_canonical_catalog is True
    assert contract.cashier_must_not_have_duplicate_manual_price_source is True
    assert contract.storefront_cashier_management_share_service_ssot is True
