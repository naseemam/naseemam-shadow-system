from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_required_retail_departments_are_present():
    mod = _load("hilm_retail_store_catalog")
    required = {
        "perfumes",
        "makeup",
        "hair_products",
        "skin_products",
        "graduation_abayas",
        "school_uniforms",
        "occasion_abayas",
        "dresses",
        "daraas",
    }
    assert required.issubset(mod.RETAIL_DEPARTMENTS)


def test_makeup_taxonomy_covers_major_makeup_sections():
    mod = _load("hilm_retail_store_catalog")
    makeup = " ".join(mod.RETAIL_DEPARTMENTS["makeup"])
    for expected in ("فاونديشن", "كونسيلر", "بودرة", "ظلال", "ماسكارا", "شفاه", "حواجب", "رموش", "فرش"):
        assert expected in makeup


def test_product_model_supports_real_inventory_and_clothing_variants():
    mod = _load("hilm_retail_store_catalog")
    required_fields = {
        "product_id", "department", "category", "subcategory", "sku", "barcode",
        "supplier_id", "variants", "size", "color", "fabric", "measurements",
        "cost_price", "selling_price", "offer_price", "stock_quantity",
        "reserved_quantity", "available_quantity", "low_stock_threshold",
        "reorder_quantity", "batch_number", "expiry_date", "storefront_visible",
    }
    assert required_fields.issubset(set(mod.PRODUCT_FIELDS))
    assert "sale_completed" in mod.INVENTORY_EVENTS
    assert "damaged_or_expired_writeoff" in mod.INVENTORY_EVENTS


def test_store_cashier_and_management_share_one_product_source():
    mod = _load("hilm_retail_store_catalog")
    contract = mod.hilm_retail_store_contract()
    assert contract.inventory_is_canonical is True
    assert contract.prices_are_canonical is True
    assert contract.cashier_sees_retail_products is True
    assert contract.supports_variant_level_inventory is True
    assert contract.sale_updates_inventory_automatically is True
    assert contract.storefront_cashier_management_share_product_ssot is True
    assert contract.customer_payment_is_not_founder_business_spend is True
