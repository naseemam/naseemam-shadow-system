"""Public storefront structure for Hilm Alnada.

Defines the customer-facing information architecture and shared customer account
requirements. Customer activity writes to canonical service, product, customer,
booking, order, payment and inventory sources and becomes available to authorized
management/POS projections without duplicate re-entry.
"""

from dataclasses import dataclass
from typing import Tuple


PUBLIC_SECTIONS: Tuple[str, ...] = (
    "home",
    "services",
    "service_categories",
    "service_catalog",
    "offers",
    "packages",
    "bookings",
    "home_visit_booking",
    "products",
    "product_departments",
    "product_search_and_filters",
    "loyalty",
    "gift_packages",
    "employee_profiles_when_publicly_enabled",
    "customer_reviews",
    "about_center",
    "contact_and_location",
    "cart",
    "checkout",
    "customer_account",
)

ACCOUNT_FIELDS: Tuple[str, ...] = (
    "customer_name",
    "mobile_number",
    "email",
    "address",
)

CUSTOMER_ACCOUNT_VIEWS: Tuple[str, ...] = (
    "profile",
    "bookings",
    "orders",
    "packages",
    "gift_packages",
    "loyalty_points",
    "loyalty_rewards",
    "saved_addresses",
    "payment_statuses",
    "ratings_and_reviews",
)

HOME_VISIT_FLOW: Tuple[str, ...] = (
    "select_home_visit_service",
    "confirm_eligible_service_area",
    "select_customer_address",
    "select_date_and_time",
    "select_or_recommend_service_provider",
    "calculate_final_home_visit_price_with_included_uplift",
    "confirm_booking_details",
    "checkout_and_full_storefront_payment",
    "issue_booking_number",
    "sync_booking_to_authorized_operations_view",
    "send_confirmation_and_followup",
)

PRODUCT_FLOW: Tuple[str, ...] = (
    "browse_product_department",
    "search_and_filter_products",
    "view_canonical_product_and_variant",
    "hilm_recommends_related_products_or_services",
    "validate_and_reserve_inventory",
    "add_to_shared_cart",
    "checkout_and_customer_payment",
    "verify_payment_server_side",
    "complete_order_and_inventory_event",
    "issue_invoice",
    "sync_order_to_cashier_and_management",
)

PRODUCT_FIELDS: Tuple[str, ...] = (
    "product_id",
    "department",
    "category",
    "subcategory",
    "product_name",
    "description",
    "brand",
    "sku",
    "barcode",
    "variants",
    "size",
    "color",
    "fabric",
    "measurements",
    "selling_price",
    "sale_price_when_active",
    "stock_status",
    "available_quantity",
    "images",
    "recommended_related_services",
    "recommended_related_products",
)

CANONICAL_STORE_DOMAINS: Tuple[str, ...] = (
    "customer",
    "service_catalog",
    "service_pricing",
    "product_catalog",
    "product_pricing",
    "inventory",
    "booking",
    "order",
    "payment",
    "invoice",
    "loyalty",
    "package_and_gift",
)


@dataclass(frozen=True)
class HilmPublicStorefrontContract:
    registration_required_for_purchase_and_booking: bool = True
    customer_profile_is_canonical: bool = True
    account_activity_syncs_to_pos_and_management: bool = True
    duplicate_customer_reentry_required: bool = False
    home_visit_supported: bool = True
    home_visit_price_displays_final_price_without_separate_uplift_line: bool = True
    storefront_booking_requires_full_payment: bool = True
    service_booking_supported: bool = True
    product_sales_supported: bool = True
    product_and_service_cart_is_shared: bool = True
    product_inventory_is_canonical: bool = True
    product_variants_supported: bool = True
    cashier_and_management_consume_same_product_ssot: bool = True
    offers_supported: bool = True
    packages_supported: bool = True
    loyalty_supported: bool = True
    gift_purchases_supported: bool = True
    customer_payment_is_not_founder_business_spend: bool = True


def hilm_public_storefront_contract() -> HilmPublicStorefrontContract:
    return HilmPublicStorefrontContract()
