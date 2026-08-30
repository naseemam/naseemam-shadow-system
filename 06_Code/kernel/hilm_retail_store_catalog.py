"""Retail product departments for the Hilm Alnada public store.

This catalog is distinct from bookable beauty services. Product SKUs, variants,
stock and selling prices are managed through the canonical commerce/inventory
source and exposed to the storefront, cashier and management surfaces.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


RETAIL_DEPARTMENTS: Dict[str, Tuple[str, ...]] = {
    "perfumes": ("عطورات",),
    "makeup": (
        "مكياج الوجه",
        "مكياج العيون",
        "مكياج الشفاه",
        "الحواجب",
        "الرموش",
        "أدوات وإكسسوارات المكياج",
    ),
    "hair_products": ("منتجات الشعر",),
    "skin_products": ("منتجات البشرة",),
    "graduation_abayas": ("عبايات تخرج",),
    "school_uniforms": ("يونيفورم مدرسي",),
    "occasion_abayas": ("عبايات مناسبات",),
    "dresses": ("فساتين",),
    "daraas": ("دراعات",),
}

PRODUCT_FIELDS: Tuple[str, ...] = (
    "product_id",
    "department",
    "category",
    "name",
    "description",
    "images",
    "sku",
    "barcode",
    "brand",
    "variants",
    "size",
    "color",
    "cost_price",
    "selling_price",
    "offer_price",
    "stock_quantity",
    "low_stock_threshold",
    "availability_status",
)

PRODUCT_COMMERCE_FLOW: Tuple[str, ...] = (
    "browse_department",
    "search_products",
    "filter_and_compare",
    "hilm_recommends_relevant_products",
    "select_variant",
    "validate_stock",
    "add_to_cart",
    "checkout",
    "verify_payment",
    "decrement_inventory",
    "issue_invoice",
    "sync_sale_to_cashier_and_management",
)


@dataclass(frozen=True)
class HilmRetailStoreContract:
    separate_from_bookable_services: bool = True
    shares_customer_account_and_cart: bool = True
    cashier_sees_retail_products: bool = True
    inventory_is_canonical: bool = True
    prices_are_canonical: bool = True
    supports_variants_sizes_and_colors: bool = True
    supports_barcode_and_sku: bool = True
    supports_product_offers: bool = True
    hilm_may_search_recommend_and_help_purchase: bool = True
    sale_updates_inventory_automatically: bool = True
    storefront_cashier_management_share_product_ssot: bool = True


def hilm_retail_store_contract() -> HilmRetailStoreContract:
    return HilmRetailStoreContract()
