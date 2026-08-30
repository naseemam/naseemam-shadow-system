"""Public storefront structure for Hilm Alnada.

Defines the customer-facing information architecture and shared customer account
requirements. All customer activity should write to the canonical customer profile
and become available to authorized management/POS projections without duplicate
re-entry.
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
    "calculate_home_visit_price_and_fees",
    "confirm_booking_details",
    "checkout_and_payment",
    "issue_booking_number",
    "sync_booking_to_authorized_operations_view",
    "send_confirmation_and_followup",
)

PRODUCT_FIELDS: Tuple[str, ...] = (
    "product_name",
    "category",
    "description",
    "price",
    "sale_price_when_active",
    "stock_status",
    "images",
    "recommended_related_services",
    "recommended_related_products",
)


@dataclass(frozen=True)
class HilmPublicStorefrontContract:
    registration_required_for_purchase_and_booking: bool = True
    customer_profile_is_canonical: bool = True
    account_activity_syncs_to_pos_and_management: bool = True
    duplicate_customer_reentry_required: bool = False
    home_visit_supported: bool = True
    service_booking_supported: bool = True
    product_sales_supported: bool = True
    offers_supported: bool = True
    packages_supported: bool = True
    loyalty_supported: bool = True
    gift_purchases_supported: bool = True


def hilm_public_storefront_contract() -> HilmPublicStorefrontContract:
    return HilmPublicStorefrontContract()
