"""Employee performance, operational consumption analytics, and fixed-asset accountability for Hilm Alnada."""

from dataclasses import dataclass
from typing import Tuple

EMPLOYEE_CONSUMPTION_ANALYTICS: Tuple[str, ...] = (
    "rank_highest_consumption_employee",
    "rank_lowest_consumption_employee",
    "compare_consumption_to_completed_service_volume",
    "compare_actual_to_standard_consumption",
    "normalize_by_service_type_duration_hair_length_or_treatment_scope",
    "flag_repeated_material_overuse",
    "flag_abnormally_low_use_when_service_quality_may_be_affected",
    "show_consumption_cost_per_employee",
    "show_consumption_cost_per_service",
    "show_consumption_trend_by_period",
)

FIXED_ASSET_FIELDS: Tuple[str, ...] = (
    "asset_id",
    "asset_category",
    "asset_name",
    "brand_model",
    "serial_number_when_available",
    "purchase_date",
    "purchase_cost",
    "supplier",
    "invoice_reference",
    "warranty_expiry",
    "location",
    "department_id",
    "responsible_employee_id",
    "condition",
    "maintenance_schedule",
    "last_maintenance_at",
    "next_maintenance_at",
    "photos",
    "handover_receipt_reference",
    "damage_history",
    "repair_history",
    "retirement_or_disposal_status",
)

FIXED_ASSET_EXAMPLES: Tuple[str, ...] = (
    "hair_dryer",
    "styling_chair",
    "wash_station",
    "facial_machine",
    "massage_bed",
    "moroccan_bath_equipment",
    "coffee_machine",
    "refrigerator",
    "pos_device",
    "printer",
    "tablet",
    "tailoring_machine",
)

ASSET_ACCOUNTABILITY_FLOW: Tuple[str, ...] = (
    "register_asset_with_invoice_or_source_document",
    "assign_asset_to_department",
    "assign_responsible_employee_when_applicable",
    "generate_handover_receipt",
    "record_condition_and_photos_at_handover",
    "track_maintenance_and_faults",
    "record_damage_or_loss_with_evidence",
    "record_return_or_reassignment",
    "retain_history_for_audit",
)

EMPLOYEE_BEHAVIOR_AND_COMPLIANCE_EVENTS: Tuple[str, ...] = (
    "attendance",
    "absence",
    "late_arrival",
    "early_departure",
    "service_start_delay",
    "excessive_idle_time_when_measurable",
    "task_completion_delay",
    "cleaning_noncompliance",
    "sterilization_noncompliance",
    "tool_care_noncompliance",
    "asset_damage",
    "avoidable_material_waste",
    "customer_complaint",
    "customer_praise",
    "quality_rework",
)

PERFORMANCE_SCORE_COMPONENTS: Tuple[str, ...] = (
    "attendance_and_punctuality",
    "sales_or_productivity",
    "customer_satisfaction",
    "service_quality",
    "cleaning_and_sterilization",
    "asset_and_tool_care",
    "material_efficiency",
    "teamwork_and_operational_compliance",
)

BONUS_POLICY_GUIDANCE = {
    "period": "monthly_after_month_close",
    "recommended_min_percent_of_base_salary": 5,
    "recommended_target_percent_of_base_salary": 10,
    "recommended_max_percent_of_base_salary": 15,
    "requires_closed_attendance": True,
    "requires_inventory_reconciliation": True,
    "requires_resolved_material_anomalies": True,
    "requires_quality_and_customer_review": True,
    "single_metric_bonus_prohibited": True,
    "automatic_salary_penalty_from_operational_flags": False,
}

MANAGEMENT_PROGRAM_AREAS: Tuple[str, ...] = (
    "cashier_and_invoicing",
    "retail_inventory",
    "operational_inventory",
    "warehouse_and_storekeeper",
    "purchasing_and_suppliers",
    "fixed_assets",
    "employees_and_hr",
    "attendance_and_time",
    "performance_and_bonus",
    "cleaning_and_sterilization",
    "service_quality",
    "customer_experience",
    "maintenance",
    "finance_and_expenses",
    "reports_and_analytics",
)

@dataclass(frozen=True)
class EmployeePerformanceAssetContract:
    highest_and_lowest_consumption_rankings_supported: bool = True
    consumption_must_be_normalized_by_service_volume_and_standard: bool = True
    fixed_assets_have_department_and_responsible_employee: bool = True
    asset_handover_receipts_supported: bool = True
    asset_condition_photos_supported: bool = True
    attendance_and_lateness_tracked: bool = True
    operational_delay_events_supported: bool = True
    cleaning_and_sterilization_compliance_tracked: bool = True
    tool_neglect_and_damage_tracked: bool = True
    monthly_multi_factor_bonus_supported: bool = True
    operational_flags_do_not_auto_deduct_salary: bool = True
    multiple_specialized_management_program_areas_supported: bool = True


def employee_performance_asset_contract() -> EmployeePerformanceAssetContract:
    return EmployeePerformanceAssetContract()
