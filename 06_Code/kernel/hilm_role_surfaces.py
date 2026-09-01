"""Role-separated Hilm Alnada application surfaces.

The full management program is an administrative system. Reception staff receive
a purpose-built sales/POS surface rather than visibility into management data.
"""

from __future__ import annotations

from typing import Dict, Tuple


MANAGEMENT_MODULES: Tuple[str, ...] = (
    "inventory",
    "employees",
    "payroll",
    "customers",
    "customer_data",
    "bookings",
    "services_and_prices",
    "suppliers",
    "purchases",
    "expenses",
    "commissions",
    "sales",
    "reports",
    "analytics",
    "settings",
    "permissions",
)

RECEPTION_POS_MODULES: Tuple[str, ...] = (
    "service_sale",
    "customer_lookup_or_create",
    "booking_lookup",
    "invoice_issue",
    "payment_collection",
    "receipt_printing",
    "sale_history_for_authorized_shift",
)


def role_surface_contract() -> Dict[str, object]:
    return {
        "management": {
            "audience": "owner_and_explicitly_authorized_management_only",
            "modules": list(MANAGEMENT_MODULES),
        },
        "reception_pos": {
            "audience": "reception_cashier",
            "modules": list(RECEPTION_POS_MODULES),
            "must_not_expose": [
                "payroll",
                "employee_private_records",
                "management_reports",
                "supplier_financials",
                "system_settings",
                "permission_management",
            ],
        },
        "authorization_rule": "enforce_server_side_not_ui_hiding_only",
        "single_source_of_truth": True,
    }
