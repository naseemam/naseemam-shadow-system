from importlib import util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_fabrics_are_a_first_class_store_department():
    retail = _load("hilm_retail_store_catalog")
    assert "fabrics" in retail.RETAIL_DEPARTMENTS
    assert "أقمشة عبايات" in retail.RETAIL_DEPARTMENTS["fabrics"]
    assert "أقمشة فساتين" in retail.RETAIL_DEPARTMENTS["fabrics"]
    assert "fabric_length_available" in retail.PRODUCT_FIELDS
    assert retail.hilm_retail_store_contract().fabrics_can_attach_to_online_tailoring_orders is True


def test_online_tailoring_collects_and_saves_measurements():
    tailoring = _load("tailoring_online_order")
    required = {
        "height", "shoulder_width", "bust", "waist", "hips",
        "sleeve_length", "garment_length"
    }
    assert required.issubset(tailoring.TAILORING_MEASUREMENT_FIELDS)
    contract = tailoring.tailoring_online_order_contract()
    assert contract.online_tailoring_supported is True
    assert contract.measurements_required_for_custom_tailoring is True
    assert contract.measurements_are_saved_to_customer_tailoring_profile is True
    assert contract.measurement_changes_are_versioned is True
    assert contract.customer_may_choose_store_fabric is True


def test_storefront_exposes_fabrics_tailoring_and_payment_gateway():
    storefront = _load("hilm_public_storefront_structure")
    assert "fabrics" in storefront.PUBLIC_SECTIONS
    assert "online_tailoring" in storefront.PUBLIC_SECTIONS
    assert "payment_gateway" in storefront.PUBLIC_SECTIONS
    assert "tailoring_orders" in storefront.CUSTOMER_ACCOUNT_VIEWS
    assert "saved_tailoring_measurements" in storefront.CUSTOMER_ACCOUNT_VIEWS
    assert "checkout_through_shared_payment_gateway" in storefront.TAILORING_FLOW


def test_shared_gateway_covers_tailoring_fabrics_and_other_storefront_commerce():
    payment = _load("checkout_payment_architecture")
    expected = {
        "service_booking", "home_visit_booking", "retail_product_order",
        "fabric_order", "online_tailoring_order", "package_purchase", "gift_purchase"
    }
    assert expected.issubset(payment.PAYABLE_COMMERCE_TYPES)
    contract = payment.checkout_payment_contract()
    assert contract.shared_gateway_serves_all_storefront_commerce is True
    assert contract.tailoring_orders_use_shared_gateway is True
    assert contract.fabric_orders_use_shared_gateway is True
    assert contract.provider_callbacks_must_be_verified_server_side is True
    assert contract.ordinary_customer_payment_requires_founder_approval is False
