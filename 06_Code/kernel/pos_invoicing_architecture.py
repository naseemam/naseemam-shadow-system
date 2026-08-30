"""Local + web POS and invoicing architecture for Hilm Alnada and similar businesses."""

from __future__ import annotations

from typing import Dict, Tuple


CORE_MODULES: Tuple[str, ...] = (
    "service_catalog",
    "customers",
    "employees",
    "bookings",
    "point_of_sale",
    "invoicing",
    "payments",
    "inventory",
    "purchases_and_suppliers",
    "offers_and_packages",
    "commissions",
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


def architecture_snapshot() -> Dict[str, object]:
    return {
        "architecture": "offline_first_local_pos_plus_central_web_platform",
        "modules": list(CORE_MODULES),
        "local_runtime": list(LOCAL_RUNTIME),
        "web_runtime": list(WEB_RUNTIME),
        "single_source_of_truth": True,
        "local_sales_must_continue_during_internet_outage": True,
        "sync_after_connectivity_returns": True,
        "ameer_intelligence_layer": True,
        "ameer_may_design_build_test_operate_and_evolve_system": True,
        "financial_commitment_requires_only_the_existing_sovereign_decision_when_applicable": True,
    }
