"""Unified customer identity, packages, gift codes, bookings, POS visibility, and loyalty.

The Hilm Alnada storefront, booking system, POS, and management system share one customer identity and one source of truth.
"""

from dataclasses import dataclass
from typing import Tuple


CUSTOMER_PROFILE_SYNC: Tuple[str, ...] = (
    "website_registration_creates_customer_profile",
    "storefront_orders_attach_to_customer_profile",
    "bookings_attach_to_customer_profile",
    "packages_attach_to_customer_profile",
    "gifted_packages_attach_purchaser_and_recipient",
    "pos_reads_same_customer_profile",
    "management_system_reads_same_customer_profile",
)

PACKAGE_CAPABILITIES: Tuple[str, ...] = (
    "fixed_price_packages",
    "book_package_for_self",
    "buy_package_as_gift",
    "buy_package_for_another_customer",
    "generate_unique_redemption_code",
    "associate_code_with_package",
    "associate_code_with_customer_or_recipient",
    "show_code_in_pos",
    "redeem_code_at_reception",
    "track_remaining_entitlements",
    "track_package_expiry_when_applicable",
)

LOYALTY_CAPABILITIES: Tuple[str, ...] = (
    "loyalty_account_per_customer",
    "earn_points_from_eligible_sales",
    "earn_points_from_eligible_bookings",
    "redeem_points_on_eligible_purchase",
    "show_balance_in_customer_account",
    "show_balance_in_pos",
    "show_history_in_management_system",
    "support_tiers_or_status_levels",
    "support_targeted_rewards",
    "prevent_duplicate_credit",
)

OFFER_SECTION_CAPABILITIES: Tuple[str, ...] = (
    "ameer_may_create_offer",
    "ameer_may_change_offer_name",
    "ameer_may_change_offer_price",
    "ameer_may_change_offer_services",
    "ameer_may_change_offer_schedule",
    "ameer_may_publish_offer_to_storefront",
    "ameer_may_retire_offer",
    "founder_manual_entry_not_required",
)


@dataclass(frozen=True)
class CustomerCommerceContract:
    registration_required_for_account_bound_purchase: bool = True
    automatic_profile_sync_to_pos: bool = True
    automatic_booking_sync_to_pos: bool = True
    automatic_order_sync_to_pos: bool = True
    packages_support_gifting: bool = True
    package_redemption_uses_unique_code: bool = True
    loyalty_enabled: bool = True
    offer_section_is_ameer_managed: bool = True


def customer_commerce_contract() -> CustomerCommerceContract:
    return CustomerCommerceContract()
