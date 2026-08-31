"""Operational workspace for Hilm Alnada tailoring.

Coordinates in-person cashier measurement intake, fabric handoff, tailoring work,
fittings, alterations, pickup/delivery and Hilm customer follow-up. Paper forms may
be scanned/photographed for rapid attachment, but extracted text is always a draft
that requires field validation before it can update canonical measurements or an
order. The original image remains attached for audit and error correction.
"""

from dataclasses import dataclass
from typing import Tuple


TAILORING_DASHBOARD_VIEWS: Tuple[str, ...] = (
    "today_measurements",
    "awaiting_fabric",
    "fabric_received",
    "awaiting_tailor_assignment",
    "in_tailoring",
    "awaiting_fitting",
    "alterations",
    "ready_for_pickup_or_delivery",
    "overdue_orders",
    "completed_orders",
    "active_customer_count",
    "orders_by_tailor",
    "orders_by_due_date",
)

IN_PERSON_CASHIER_MEASUREMENT_FLOW: Tuple[str, ...] = (
    "find_or_create_customer_account_by_verified_phone",
    "select_or_create_measurement_profile",
    "cashier_or_authorized_employee_enters_measurements",
    "validate_numeric_ranges_and_required_fields",
    "show_previous_measurements_and_highlight_large_changes",
    "employee_confirms_measurements_with_customer",
    "save_new_version_to_customer_measurement_profile",
    "attach_measurement_profile_to_tailoring_order",
    "snapshot_measurements_for_order",
    "print_or_send_tailoring_work_order",
)

PAPER_CAPTURE_FLOW: Tuple[str, ...] = (
    "capture_scan_or_photo_of_manual_form",
    "store_original_image_as_order_attachment",
    "extract_candidate_fields_when_supported",
    "mark_extracted_values_as_unverified_draft",
    "show_image_beside_structured_fields",
    "validate_expected_field_names_and_numeric_ranges",
    "flag_low_confidence_or_ambiguous_values",
    "authorized_employee_reviews_and_confirms",
    "write_confirmed_values_to_canonical_order_or_measurement_profile",
    "retain_source_image_and_confirmation_audit",
)

TAILORING_WORKFLOW_STAGES: Tuple[str, ...] = (
    "intake",
    "measurements_taken",
    "fabric_pending",
    "fabric_received",
    "ready_for_tailor",
    "assigned_to_tailor",
    "cutting",
    "sewing",
    "initial_review",
    "fitting_pending",
    "fitting_completed",
    "alteration_pending",
    "alteration_in_progress",
    "final_quality_check",
    "ready_for_pickup_or_delivery",
    "delivered",
    "closed",
)

TAILORING_TRACKING_FIELDS: Tuple[str, ...] = (
    "tailoring_order_id",
    "order_number",
    "customer_id",
    "customer_name",
    "customer_phone",
    "measurement_profile_id",
    "measurements_snapshot",
    "fabric_source",
    "fabric_product_or_description",
    "fabric_quantity",
    "fabric_received_at",
    "assigned_tailor_id",
    "current_stage",
    "stage_started_at",
    "requested_completion_date",
    "promised_delivery_date",
    "fitting_booking_id",
    "alteration_requests",
    "customer_reference_images",
    "employee_progress_images",
    "manual_form_attachments",
    "payment_status",
    "handoff_status",
    "delivered_at",
    "received_by_name",
    "hilm_followup_status",
    "last_customer_update_at",
)

ERROR_PREVENTION_RULES: Tuple[str, ...] = (
    "phone_must_be_verified_before_merging_customer_records",
    "measurement_values_use_structured_numeric_fields_not_free_text_when_possible",
    "measurement_units_are_explicit",
    "large_change_from_previous_version_is_flagged_for_confirmation",
    "paper_extraction_never_overwrites_canonical_data_without_human_confirmation",
    "ambiguous_or_low_confidence_extraction_is_flagged",
    "original_scan_or_photo_is_retained_for_audit",
    "order_number_is_generated_and_not_manually_retyped_across_views",
    "cashier_tailor_management_and_hilm_share_the_same_canonical_order",
)


@dataclass(frozen=True)
class TailoringOperationsContract:
    cashier_can_capture_in_person_measurements: bool = True
    cashier_measurements_save_to_customer_measurement_profile: bool = True
    cashier_can_select_existing_family_measurement_profile: bool = True
    tailoring_has_dedicated_operations_dashboard: bool = True
    tracks_customer_volume_and_active_orders: bool = True
    tracks_measurement_fabric_tailoring_fitting_alteration_delivery: bool = True
    supports_manual_form_scan_or_photo_attachment: bool = True
    extracted_manual_form_data_is_draft_until_confirmed: bool = True
    source_image_is_retained_for_audit: bool = True
    structured_validation_reduces_typing_errors: bool = True
    hilm_follows_customer_across_tailoring_stages: bool = True
    canonical_order_shared_with_cashier_management_and_tailor: bool = True


def tailoring_operations_contract() -> TailoringOperationsContract:
    return TailoringOperationsContract()
