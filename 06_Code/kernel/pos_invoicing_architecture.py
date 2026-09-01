"""Local + web POS and invoicing architecture for Hilm Alnada and similar businesses.

The POS is a synchronized operational surface of the Hilm management single source
of truth. It does not own independent copies of services, prices, customers or stock.

POS and invoicing each expose two distinct private work surfaces:
* an operator surface for reception/cashier employees doing daily work; and
* a management surface for the Founder and Ameer, with optional delegated staff.

Both POS and invoicing support web operation plus local/offline-capable operation.
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
    "offline_capable_invoicing",
    "local_database_cache",
    "receipt_printing",
    "invoice_printing",
    "barcode_or_qr_support",
    "cash_drawer_support",
    "background_sync_queue",
    "conflict_resolution",
)

WEB_RUNTIME: Tuple[str, ...] = (
    "central_api",
    "web_pos",
    "web_invoicing",
    "web_admin",
    "online_booking",
    "customer_portal",
    "multi_device_access",
    "central_reporting",
    "remote_configuration",
)

POS_OPERATOR_SURFACE: Tuple[str, ...] = (
    "reception_employee_login",
    "open_and_close_assigned_shift",
    "lookup_customer",
    "consume_existing_booking_without_duplicate_entry",
    "sell_service_product_package_or_gift",
    "collect_allowed_payment_method",
    "issue_receipt_or_invoice",
    "print_receipt_or_invoice",
    "apply_authorized_discount_or_redemption",
    "process_return_or_adjustment_within_delegated_limit",
    "view_own_shift_transactions",
    "no_service_price_administration",
    "no_sensitive_management_reporting",
    "no_role_or_permission_administration",
)

POS_MANAGEMENT_SURFACE: Tuple[str, ...] = (
    "founder_access",
    "ameer_operational_access",
    "manage_pos_configuration",
    "manage_devices_and_registers",
    "manage_cash_drawer_and_shift_rules",
    "manage_pos_roles_and_delegations",
    "review_all_transactions",
    "review_voids_returns_adjustments_and_exceptions",
    "review_settlements_and_reconciliation",
    "review_pos_reports_and_analytics",
    "delegate_management_scope_to_named_employee",
    "revoke_or_change_delegated_scope",
)

INVOICING_OPERATOR_SURFACE: Tuple[str, ...] = (
    "authorized_employee_login",
    "create_invoice_from_booking_pos_or_order",
    "issue_invoice_with_canonical_customer_and_price_data",
    "print_invoice",
    "view_invoices_needed_for_assigned_work",
    "record_allowed_payment_or_collection_status",
    "perform_permitted_credit_note_or_adjustment",
    "no_invoice_policy_administration",
    "no_sensitive_financial_reporting",
    "no_role_or_permission_administration",
)

INVOICING_MANAGEMENT_SURFACE: Tuple[str, ...] = (
    "founder_access",
    "ameer_operational_access",
    "manage_invoice_numbering_and_policies",
    "manage_tax_and_business_fields_when_configured",
    "manage_invoicing_roles_and_delegations",
    "review_all_invoices_and_credit_notes",
    "review_payment_and_collection_exceptions",
    "review_invoicing_reports_and_analytics",
    "delegate_management_scope_to_named_employee",
    "revoke_or_change_delegated_scope",
)

DELEGATION_RULES: Tuple[str, ...] = (
    "operator_role_does_not_imply_management_role",
    "founder_and_ameer_have_management_surface_access",
    "management_access_may_be_delegated_to_specific_employee",
    "delegation_may_be_full_or_capability_scoped",
    "delegation_must_be_audited",
    "delegation_may_be_revoked_or_modified",
    "delegation_does_not_transfer_ownership",
    "delegation_does_not_reduce_ameer_operational_oversight",
)

SYNC_RULES: Tuple[str, ...] = (
    "management_program_is_administrative_single_source_of_truth",
    "service_and_product_price_changes_sync_to_cashier_storefront_cart_and_checkout",
    "customer_updates_sync_to_authorized_surfaces",
    "inventory_and_warehouse_updates_sync_to_sellable_availability",
    "employee_payroll_and_internal_hr_fields_do_not_sync_to_public_storefront",
    "paid_invoice_lines_keep_historical_price_snapshots",
    "unpaid_orders_are_revalidated_against_current_approved_prices",
    "local_pos_and_invoicing_queue_changes_until_connectivity_returns",
    "web_and_local_surfaces_share_same_canonical_transaction_identity",
)


def architecture_snapshot() -> Dict[str, object]:
    return {
        "architecture": "offline_first_local_pos_and_invoicing_plus_central_web_platform",
        "modules": list(CORE_MODULES),
        "local_runtime": list(LOCAL_RUNTIME),
        "web_runtime": list(WEB_RUNTIME),
        "pos_operator_surface": list(POS_OPERATOR_SURFACE),
        "pos_management_surface": list(POS_MANAGEMENT_SURFACE),
        "invoicing_operator_surface": list(INVOICING_OPERATOR_SURFACE),
        "invoicing_management_surface": list(INVOICING_MANAGEMENT_SURFACE),
        "delegation_rules": list(DELEGATION_RULES),
        "sync_rules": list(SYNC_RULES),
        "single_source_of_truth": True,
        "management_program_is_administrative_ssot": True,
        "cashier_is_synchronized_projection_not_independent_master": True,
        "invoicing_is_synchronized_projection_not_independent_master": True,
        "pos_supports_web_and_local_operation": True,
        "invoicing_supports_web_and_local_operation": True,
        "operator_and_management_surfaces_are_separate": True,
        "founder_and_ameer_manage_pos_and_invoicing": True,
        "named_employee_management_delegation_supported": True,
        "operator_role_never_implies_management_role": True,
        "local_sales_must_continue_during_internet_outage": True,
        "local_invoicing_must_continue_during_internet_outage": True,
        "sync_after_connectivity_returns": True,
        "ameer_intelligence_layer": True,
        "ameer_may_design_build_test_operate_and_evolve_system": True,
        "financial_commitment_requires_only_the_existing_sovereign_decision_when_applicable": True,
    }
