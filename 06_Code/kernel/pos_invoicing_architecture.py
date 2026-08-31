"""Local + web POS and invoicing architecture for Hilm Alnada and similar businesses.

The POS is a synchronized operational surface of the Hilm management single source
of truth. It does not own independent copies of services, prices, customers or stock.
"""

from __future__ import annotations

from typing import Dict, Tuple


CORE_MODULES: Tuple[str, ...] = (
    "service_catalog",
    "customers",
    "employees",
    "payroll",
    "bookings",
    "point_of_sale",
    "invoicing",
    "payments",
    "inventory",
    "warehouses",
    "purchases_and_suppliers",
    "resources",
    "offers_and_packages",
    "commissions",
    "employee_discounts_and_deductions",
    "expenses",
    "cash_drawer_and_shifts",
    "returns_and_adjustments",
    "reports_and_analytics",
    "audit_log",
    "roles_and_permissions",
    "sync_and_backup",
)

LOCAL_RUNTIME: Tuple[str, ...] = (
    "offline_capable_pos",
    "local_database_cache",
    "receipt_printing",
    "barcode_or_qr_support",
    "cash_drawer_support",
    "background_sync_queue",
    "conflict_resolution",
)

WEB_RUNTIME: Tuple[str, ...] = (
    "central_api",
    "web_admin",
    "online_booking",
    "customer_portal",
    "multi_device_access",
    "central_reporting",
    "remote_configuration",
)

SYNC_RULES: Tuple[str, ...] = (
    "management_program_is_administrative_single_source_of_truth",
    "service_and_product_price_changes_sync_to_cashier_storefront_cart_and_checkout",
    "customer_updates_sync_to_authorized_surfaces",
    "inventory_and_warehouse_updates_sync_to_sellable_availability",
    "employee_payroll_and_internal_hr_fields_do_not_sync_to_public_storefront",
    "paid_invoice_lines_keep_historical_price_snapshots",
    "unpaid_orders_are_revalidated_against_current_approved_prices",
)


def architecture_snapshot() -> Dict[str, object]:
    return {
        "architecture": "offline_first_local_pos_plus_central_web_platform",
        "modules": list(CORE_MODULES),
        "local_runtime": list(LOCAL_RUNTIME),
        "web_runtime": list(WEB_RUNTIME),
        "sync_rules": list(SYNC_RULES),
        "single_source_of_truth": True,
        "management_program_is_administrative_ssot": True,
        "cashier_is_synchronized_projection_not_independent_master": True,
        "local_sales_must_continue_during_internet_outage": True,
        "sync_after_connectivity_returns": True,
        "ameer_intelligence_layer": True,
        "ameer_may_design_build_test_operate_and_evolve_system": True,
        "financial_commitment_requires_only_the_existing_sovereign_decision_when_applicable": True,
    }
