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


def test_home_visit_price_includes_ten_percent_uplift():
    result = module.home_visit_price("example", 100)
    assert result["final_price"] == 110
    assert result["customer_price_label"] == 110
    assert result["status"] == "priced"


def test_customer_does_not_see_separate_home_visit_fee():
    result = module.home_visit_price("example", 250)
    assert result["final_price"] == 275
    assert result["customer_sees_separate_home_visit_fee"] is False
    assert "home_visit_surcharge" not in result


def test_contract_requires_shared_service_source_of_truth():
    contract = module.home_visit_and_cashier_contract()
    assert contract.home_visit_uplift_percent == 10
    assert contract.home_visit_final_price_includes_uplift is True
    assert contract.customer_sees_separate_home_visit_fee is False
    assert contract.cashier_uses_entire_canonical_catalog is True
    assert contract.cashier_must_not_have_duplicate_manual_price_source is True
    assert contract.storefront_cashier_management_share_service_ssot is True
