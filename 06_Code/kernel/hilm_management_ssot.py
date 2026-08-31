"""Hilm Alnada management system as the administrative single source of truth.

The management program owns approved operational records for services, products,
prices, customers, employees, payroll, discounts, resources, inventory, warehouses,
suppliers and invoicing. Customer-facing and cashier surfaces consume synchronized
projections from this source instead of maintaining independent copies.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


MANAGEMENT_DOMAINS: Tuple[str, ...] = (
    "services",
    "service_prices",
    "products",
    "product_prices",
    "customers",
    "employees",
    "payroll",
    "employee_discounts_and_deductions",
    "commissions",
    "resources",
    "inventory",
    "warehouses",
    "suppliers",
    "purchases",
    "offers",
    "packages",
    "loyalty",
    "bookings",
    "invoices",
    "payments",
    "returns_and_adjustments",
)

PUBLIC_SYNC_DOMAINS: Tuple[str, ...] = (
    "services",
    "service_prices",
    "products",
    "product_prices",
    "offers",
    "packages",
    "loyalty",
    "availability_relevant_resources",
)

CASHIER_SYNC_DOMAINS: Tuple[str, ...] = (
    "services",
    "service_prices",
    "products",
    "product_prices",
    "customers",
    "offers",
    "packages",
    "loyalty",
    "inventory_availability",
    "bookings",
    "invoices",
    "payments",
    "returns_and_adjustments",
)

PRIVATE_INTERNAL_DOMAINS: Tuple[str, ...] = (
    "employees",
    "payroll",
    "employee_discounts_and_deductions",
    "commissions",
    "supplier_costs",
    "purchases",
    "warehouse_internal_movements",
)

SYNC_TARGETS: Tuple[str, ...] = (
    "public_storefront",
    "booking_engine",
    "shared_cart",
    "checkout_payment_gateway",
    "cashier_pos",
    "customer_account",
    "hilm_sales_agent",
    "inventory_runtime",
    "reporting",
)

CHANGE_EVENTS: Tuple[str, ...] = (
    "service_created",
    "service_updated",
    "service_price_changed",
    "product_created",
    "product_updated",
    "product_price_changed",
    "customer_updated",
    "employee_updated",
    "payroll_changed",
    "employee_discount_or_deduction_changed",
    "resource_changed",
    "inventory_changed",
    "warehouse_stock_moved",
    "offer_changed",
    "package_changed",
)

SYNC_FLOW: Tuple[str, ...] = (
    "authorized_management_change_submitted",
    "validate_domain_rules",
    "persist_canonical_record",
    "append_audit_event",
    "publish_domain_change_event",
    "rebuild_only_affected_projections",
    "update_cashier_and_storefront_when_relevant",
    "update_cart_and_checkout_price_source_when_relevant",
    "invalidate_stale_cache_when_relevant",
    "verify_projection_versions",
)

PRICE_CHANGE_RULES: Tuple[str, ...] = (
    "service_and_product_prices_are_edited_in_management_source_only",
    "storefront_cashier_cart_and_checkout_read_current_approved_price_projection",
    "new_price_applies_to_new_cart_or_booking_validation",
    "existing_paid_invoice_keeps_historical_price_snapshot",
    "existing_unpaid_cart_or_booking_is_revalidated_before_payment",
    "price_changes_are_audited_with_actor_timestamp_old_and_new_value",
)

INVENTORY_SYNC_RULES: Tuple[str, ...] = (
    "warehouse_receipt_increases_canonical_stock",
    "sale_or_reservation_decreases_or_reserves_canonical_stock",
    "return_release_or_cancellation_restores_stock_when_applicable",
    "storefront_availability_uses_canonical_sellable_stock",
    "cashier_and_storefront_must_not_maintain_independent_stock_counts",
)

CUSTOMER_SYNC_RULES: Tuple[str, ...] = (
    "customer_profile_has_one_canonical_identity",
    "cashier_and_storefront_share_customer_history_and_allowed_profile_fields",
    "tailoring_measurement_profiles_attach_to_canonical_customer",
    "private_internal_notes_are_not_exposed_to_public_storefront",
)


@dataclass(frozen=True)
class HilmManagementSSOTContract:
    management_program_is_administrative_ssot: bool = True
    price_changes_sync_to_storefront_cashier_cart_and_checkout: bool = True
    product_changes_sync_to_storefront_and_cashier: bool = True
    service_changes_sync_to_storefront_and_cashier: bool = True
    customer_changes_sync_to_allowed_surfaces: bool = True
    inventory_and_warehouse_changes_sync_to_sellable_availability: bool = True
    employee_and_payroll_data_remain_private_internal: bool = True
    historical_paid_invoices_keep_price_snapshots: bool = True
    unpaid_commerce_is_revalidated_after_price_change: bool = True
    all_changes_are_audited: bool = True
    future_management_domains_can_publish_same_change_event_pattern: bool = True


def management_ssot_contract() -> HilmManagementSSOTContract:
    return HilmManagementSSOTContract()


def domain_visibility() -> Dict[str, Tuple[str, ...]]:
    return {
        "public_sync": PUBLIC_SYNC_DOMAINS,
        "cashier_sync": CASHIER_SYNC_DOMAINS,
        "private_internal": PRIVATE_INTERNAL_DOMAINS,
    }
