"""Canonical retail product and inventory model for the Hilm Alnada store.

Retail products are separate from bookable beauty services while sharing the same
customer account, cart, checkout, cashier, invoice and management platform. This
module defines the canonical department taxonomy and the fields required for real
inventory, variants, purchasing and storefront projection.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


RETAIL_DEPARTMENTS: Dict[str, Tuple[str, ...]] = {
    "perfumes": (
        "عطور نسائية",
        "عطور شرقية",
        "عطور فرنسية وعالمية",
        "بخور ومعطرات",
        "مجموعات وهدايا عطرية",
    ),
    "makeup": (
        "برايمر ومثبت مكياج",
        "فاونديشن",
        "كونسيلر ومصححات",
        "بودرة",
        "بلاشر وبرونزر وهايلايتر",
        "ظلال عيون",
        "آيلاينر وكحل",
        "ماسكارا",
        "منتجات الحواجب",
        "رموش ولاصق رموش",
        "أحمر شفاه",
        "محدد شفاه",
        "ملمع ومنتجات عناية الشفاه",
        "فرش وأدوات وإكسسوارات المكياج",
    ),
    "hair_products": (
        "شامبو وبلسم",
        "ماسكات وعلاجات",
        "زيوت وسيرومات",
        "منتجات تصفيف",
        "حماية من الحرارة",
        "منتجات الشعر المصبوغ",
        "أدوات وإكسسوارات الشعر",
    ),
    "skin_products": (
        "منظفات",
        "تونر",
        "سيرومات",
        "مرطبات",
        "واقي شمس",
        "ماسكات وتقشير",
        "عناية الجسم",
        "مجموعات عناية",
    ),
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
    "subcategory",
    "name",
    "description",
    "images",
    "sku",
    "barcode",
    "brand",
    "supplier_id",
    "variants",
    "size",
    "color",
    "fabric",
    "measurements",
    "cost_price",
    "selling_price",
    "offer_price",
    "tax_class",
    "stock_quantity",
    "reserved_quantity",
    "available_quantity",
    "low_stock_threshold",
    "reorder_quantity",
    "batch_number",
    "expiry_date",
    "availability_status",
    "storefront_visible",
    "related_products",
    "related_services",
    "created_at",
    "updated_at",
)

VARIANT_FIELDS: Tuple[str, ...] = (
    "variant_id",
    "product_id",
    "sku",
    "barcode",
    "size",
    "color",
    "fabric",
    "measurements",
    "cost_price",
    "selling_price",
    "offer_price",
    "stock_quantity",
    "reserved_quantity",
    "available_quantity",
    "availability_status",
)

INVENTORY_EVENTS: Tuple[str, ...] = (
    "purchase_received",
    "customer_order_reserved",
    "customer_order_released",
    "sale_completed",
    "return_received",
    "manual_adjustment_with_audit",
    "stock_transfer",
    "damaged_or_expired_writeoff",
)

PRODUCT_COMMERCE_FLOW: Tuple[str, ...] = (
    "browse_department",
    "search_products",
    "filter_and_compare",
    "hilm_recommends_relevant_products",
    "select_variant",
    "validate_available_stock",
    "reserve_stock_for_order",
    "add_to_shared_cart",
    "checkout",
    "verify_customer_payment",
    "complete_order",
    "decrement_or_finalize_reserved_inventory",
    "issue_invoice",
    "sync_sale_to_cashier_and_management",
    "record_inventory_event",
)


@dataclass(frozen=True)
class HilmRetailStoreContract:
    separate_from_bookable_services: bool = True
    shares_customer_account_cart_checkout_and_invoice: bool = True
    cashier_sees_retail_products: bool = True
    inventory_is_canonical: bool = True
    prices_are_canonical: bool = True
    supports_variant_level_inventory: bool = True
    supports_variants_sizes_colors_fabrics_and_measurements: bool = True
    supports_barcode_and_sku: bool = True
    supports_supplier_and_reorder_data: bool = True
    supports_batch_and_expiry_for_applicable_beauty_products: bool = True
    supports_product_offers: bool = True
    hilm_may_search_compare_recommend_and_help_purchase: bool = True
    sale_updates_inventory_automatically: bool = True
    storefront_cashier_management_share_product_ssot: bool = True
    inventory_changes_require_auditable_events: bool = True
    customer_payment_is_not_founder_business_spend: bool = True


def hilm_retail_store_contract() -> HilmRetailStoreContract:
    return HilmRetailStoreContract()
