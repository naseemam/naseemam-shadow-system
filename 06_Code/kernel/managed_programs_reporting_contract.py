"""Universal management, analytics, and printable-report contract for Hilm Alnada programs."""

from __future__ import annotations

from typing import Dict, Tuple


REQUIRED_PROGRAM_CAPABILITIES: Tuple[str, ...] = (
    "create_records",
    "edit_records",
    "search_and_filter",
    "role_scoped_access",
    "audit_history",
    "print_forms",
    "print_reports",
    "export_reports",
    "attachments_and_scans",
    "responsible_worker_assignment",
    "ameer_operational_oversight",
    "analytics_dashboard",
    "scheduled_analysis",
    "exception_alerts",
)

REQUIRED_ANALYTICS: Tuple[str, ...] = (
    "opening_balance_vs_current_balance",
    "receipts_and_issues",
    "inventory_variance",
    "consumption_vs_service_standard",
    "highest_and_lowest_consumption_by_employee",
    "damage",
    "waste",
    "loss",
    "misuse",
    "verified_vandalism",
    "returns",
    "maintenance_due",
    "maintenance_cost",
    "asset_downtime",
    "replacement_due",
    "stockout_risk",
    "reorder_need",
    "supplier_variance",
    "department_variance",
    "employee_variance",
    "trend_over_time",
    "cost_impact",
)

PRINTABLE_REPORTS: Tuple[str, ...] = (
    "daily_operational_report",
    "weekly_exception_report",
    "monthly_management_report",
    "inventory_count_report",
    "damage_waste_loss_report",
    "maintenance_and_asset_report",
    "employee_consumption_report",
    "department_consumption_report",
    "purchase_and_supplier_report",
    "audit_and_adjustment_report",
)

PROGRAM_MANAGEMENT_MODEL: Dict[str, object] = {
    "system_of_record": "hilm_management_platform",
    "primary_operational_manager": "ameer",
    "responsible_specialist_worker_required": True,
    "worker_examples": {
        "billing_pos_inventory_warehouses": "nada",
        "future_programs": "assigned_specialist_worker",
    },
    "ameer_responsibilities": (
        "operate_and_coordinate_programs",
        "monitor_responsible_workers",
        "analyze_cross_program_data",
        "detect_anomalies_and_trends",
        "prepare_and_route_operational_actions",
        "verify_integrations_and_data_consistency",
        "produce_management_reports",
    ),
    "worker_responsibilities": (
        "manage_daily_domain_operations",
        "validate_entries",
        "review_exceptions",
        "maintain_domain_records",
        "escalate_material_anomalies_to_ameer",
    ),
    "founder_manual_micro_management_required": False,
}

REPORT_REQUIREMENTS: Dict[str, object] = {
    "printable": True,
    "editable_before_finalization": True,
    "filterable_by_date_department_employee_item_supplier_asset": True,
    "show_source_transactions": True,
    "show_calculation_basis": True,
    "show_opening_and_closing_balances_when_applicable": True,
    "show_variance_and_cost_impact": True,
    "show_responsible_worker": True,
    "show_ameer_review_status": True,
    "retain_historical_snapshots": True,
    "finalized_reports_are_immutable_snapshots": True,
}


def program_contract() -> Dict[str, object]:
    return {
        "required_capabilities": list(REQUIRED_PROGRAM_CAPABILITIES),
        "required_analytics": list(REQUIRED_ANALYTICS),
        "printable_reports": list(PRINTABLE_REPORTS),
        "management_model": PROGRAM_MANAGEMENT_MODEL,
        "report_requirements": REPORT_REQUIREMENTS,
        "applies_to_existing_programs": True,
        "applies_to_future_programs": True,
        "analytics_are_not_optional_addons": True,
        "printing_is_not_limited_to_invoices": True,
        "data_entry_editing_and_printing_are_first_class_features": True,
    }
