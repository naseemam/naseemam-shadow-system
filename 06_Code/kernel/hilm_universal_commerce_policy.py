"""Universal commerce policy for all Hilm Alnada departments.

Every current or future customer-facing department that sells a service, product,
package, room, add-on or booking participates in the same cart and shared payment
gateway. Service names, prices and sellable options come from the canonical Hilm
catalog or another explicitly canonical product/inventory catalog, never from
hard-coded duplicate prices inside department screens.

Future departments inherit this policy automatically when registered as sellable.
"""

from dataclasses import dataclass
from typing import Tuple


CURRENT_SERVICE_CATALOG_SECTIONS: Tuple[str, ...] = (
    "hair",
    "makeup",
    "eyebrows",
    "lashes",
    "lips",
    "nails",
    "facial",
    "manicure_pedicure",
    "hair_removal",
    "massage",
    "relaxation_room",
    "celebration_room",
    "coffee_lounge",
    "tailoring",
    "offers",
)

COMMERCE_ITEM_TYPES: Tuple[str, ...] = (
    "service",
    "appointment",
    "room_booking",
    "home_visit",
    "tailoring_order",
    "fabric",
    "retail_product",
    "coffee_item",
    "food_item",
    "package",
    "gift",
    "add_on",
)

UNIVERSAL_COMMERCE_FLOW: Tuple[str, ...] = (
    "register_department",
    "declare_sellable_items",
    "resolve_service_or_product_from_canonical_catalog",
    "load_current_canonical_price",
    "validate_availability_inventory_or_capacity",
    "add_item_to_shared_cart",
    "allow_cross_department_cart_when_compatible",
    "revalidate_price_and_availability_before_checkout",
    "checkout_through_shared_payment_gateway",
    "verify_payment_server_side",
    "issue_single_receipt_or_invoice",
    "sync_transaction_to_cashier_and_management",
    "route_fulfilment_to_owning_department",
)

FUTURE_DEPARTMENT_ONBOARDING_RULES: Tuple[str, ...] = (
    "new_sellable_department_inherits_shared_cart",
    "new_sellable_department_inherits_shared_payment_gateway",
    "service_prices_must_resolve_from_canonical_catalog",
    "product_prices_must_resolve_from_canonical_product_catalog",
    "department_ui_must_not_duplicate_price_as_independent_source_of_truth",
    "catalog_change_propagates_to_storefront_booking_cashier_and_checkout",
)

CATALOG_SOURCE_RULES: Tuple[str, ...] = (
    "services_and_service_prices_use_hilm_catalog_and_booking_rules",
    "retail_products_and_fabrics_use_hilm_retail_store_catalog",
    "room_packages_and_add_ons_resolve_from_canonical_catalog_entries",
    "missing_catalog_price_must_remain_unpriced_until_canonically_defined",
    "never_invent_missing_price_in_department_flow",
)


@dataclass(frozen=True)
class HilmUniversalCommerceContract:
    every_current_sellable_department_uses_shared_cart: bool = True
    every_current_sellable_department_uses_shared_payment_gateway: bool = True
    every_future_sellable_department_inherits_shared_cart: bool = True
    every_future_sellable_department_inherits_shared_payment_gateway: bool = True
    service_names_and_prices_come_from_canonical_catalog: bool = True
    product_names_and_prices_come_from_canonical_product_catalog: bool = True
    department_screens_are_not_independent_price_sources: bool = True
    canonical_price_change_propagates_to_all_commerce_surfaces: bool = True
    cross_department_cart_supported_when_items_are_compatible: bool = True
    price_and_availability_revalidated_before_payment: bool = True
    payment_is_server_verified: bool = True
    cashier_and_management_receive_same_transaction: bool = True
    missing_price_may_not_be_invented: bool = True


def hilm_universal_commerce_contract() -> HilmUniversalCommerceContract:
    return HilmUniversalCommerceContract()
