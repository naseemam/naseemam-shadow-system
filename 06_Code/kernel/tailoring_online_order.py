"""Online tailoring order contract for Hilm Alnada.

Customers may order tailoring through the public storefront, choose a garment or
custom tailoring service, optionally select fabric from the Hilm store, submit
measurements, notes and reference images, then proceed through the shared checkout
and payment gateway. Tailoring orders synchronize to management/cashier views
without duplicate entry.
"""

from dataclasses import dataclass
from typing import Tuple


TAILORING_MEASUREMENT_FIELDS: Tuple[str, ...] = (
    "height",
    "shoulder_width",
    "bust",
    "waist",
    "hips",
    "sleeve_length",
    "upper_arm_circumference",
    "wrist_circumference",
    "garment_length",
    "neck_circumference",
    "inseam_when_applicable",
    "custom_measurement_notes",
)

TAILORING_ORDER_FIELDS: Tuple[str, ...] = (
    "tailoring_order_id",
    "customer_id",
    "garment_type",
    "tailoring_service_id",
    "selected_fabric_product_id",
    "selected_fabric_variant_id",
    "fabric_length_required",
    "customer_supplies_own_fabric",
    "measurements",
    "reference_images",
    "design_notes",
    "requested_completion_date",
    "fitting_required",
    "fitting_booking_id",
    "quoted_tailoring_price",
    "fabric_price",
    "total_price",
    "payment_status",
    "order_status",
)

TAILORING_ORDER_FLOW: Tuple[str, ...] = (
    "authenticate_customer",
    "select_tailoring_service_or_garment",
    "select_store_fabric_or_customer_owned_fabric",
    "capture_required_measurements",
    "upload_reference_images_when_available",
    "capture_design_notes",
    "validate_measurement_completeness",
    "validate_and_reserve_fabric_when_store_fabric_selected",
    "calculate_tailoring_and_fabric_total",
    "confirm_completion_or_fitting_requirements",
    "checkout_through_shared_payment_gateway",
    "verify_payment_server_side",
    "create_tailoring_order",
    "sync_to_tailoring_management_and_cashier",
    "send_order_confirmation_and_status_updates",
)


@dataclass(frozen=True)
class TailoringOnlineOrderContract:
    online_tailoring_supported: bool = True
    measurements_required_for_custom_tailoring: bool = True
    customer_may_choose_store_fabric: bool = True
    customer_may_supply_own_fabric: bool = True
    reference_images_supported: bool = True
    measurements_are_saved_to_customer_tailoring_profile: bool = True
    measurement_changes_are_versioned: bool = True
    fabric_stock_is_reserved_before_payment_completion: bool = True
    shared_payment_gateway_is_used: bool = True
    payment_must_be_server_verified: bool = True
    cashier_and_management_receive_same_order: bool = True
    duplicate_order_reentry_required: bool = False


def tailoring_online_order_contract() -> TailoringOnlineOrderContract:
    return TailoringOnlineOrderContract()
