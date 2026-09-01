"""Standard material-consumption model for Hilm Alnada service operations.

Each service may define expected material consumption by operational factors such
as hair length/density, session type, treatment size, or room/package variant.
Actual warehouse issues are compared with the expected range so Nida and Ameer can
flag waste, unusual usage, under-issuance, or repeated deviations without changing
inventory or blaming an employee automatically.
"""

from dataclasses import dataclass
from typing import Tuple


CONSUMPTION_STANDARD_FIELDS: Tuple[str, ...] = (
    "standard_id",
    "service_id",
    "material_item_id",
    "unit",
    "variant_dimensions",
    "expected_quantity",
    "minimum_reasonable_quantity",
    "maximum_reasonable_quantity",
    "effective_from",
    "effective_to_optional",
    "version",
    "notes",
)

VARIANT_DIMENSION_EXAMPLES: Tuple[str, ...] = (
    "hair_length",
    "hair_density",
    "service_variant",
    "treatment_area",
    "session_duration",
    "customer_specific_adjustment_when_documented",
)

CONSUMPTION_COMPARISON_FIELDS: Tuple[str, ...] = (
    "service_execution_id",
    "service_id",
    "employee_id",
    "material_item_id",
    "standard_version",
    "expected_quantity",
    "actual_issued_quantity",
    "returned_quantity",
    "net_consumed_quantity",
    "variance_quantity",
    "variance_percent",
    "variance_status",
    "variance_reason_optional",
    "reviewed_by_optional",
    "reviewed_at_optional",
)

VARIANCE_STATES: Tuple[str, ...] = (
    "within_expected_range",
    "below_expected_range",
    "above_expected_range",
    "significant_variance_review_required",
    "documented_exception",
)

STANDARD_CONSUMPTION_FLOW: Tuple[str, ...] = (
    "load_service_and_operational_variant",
    "load_active_material_consumption_standard",
    "calculate_expected_material_requirements",
    "show_expected_quantity_to_storekeeper_before_issue",
    "record_actual_issue_from_operational_warehouse",
    "record_unused_return_when_applicable",
    "calculate_net_consumption",
    "compare_actual_to_expected_range",
    "flag_significant_variance_without_auto-penalty",
    "allow_documented_reason_and_review",
    "include_variances_in_costing_and_inventory_reports",
    "nida_monitors_operational_variances",
    "ameer_reviews_repeated_or_materially_significant_patterns",
)


@dataclass(frozen=True)
class ServiceMaterialConsumptionContract:
    service_material_standards_supported: bool = True
    standards_can_vary_by_service_dimensions: bool = True
    storekeeper_sees_expected_quantity_before_issue: bool = True
    actual_issue_and_return_are_recorded: bool = True
    net_consumption_is_compared_to_standard: bool = True
    significant_variance_is_flagged: bool = True
    variance_does_not_create_automatic_employee_penalty: bool = True
    standards_are_versioned: bool = True
    historic_service_costing_keeps_original_standard_version: bool = True
    nida_monitors_variances: bool = True
    ameer_reviews_repeated_or_significant_patterns: bool = True


def service_material_consumption_contract() -> ServiceMaterialConsumptionContract:
    return ServiceMaterialConsumptionContract()
