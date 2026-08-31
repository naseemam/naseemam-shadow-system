"""Celebration room booking and customization for Hilm Alnada.

Customers can reserve the celebration room through the public storefront, upload
reference images, describe the occasion and preferences, choose optional services,
and pay through the shared checkout flow. The booking remains one canonical record
for customer, Hilm, cashier and management.
"""

from dataclasses import dataclass
from typing import Tuple


CELEBRATION_BOOKING_FIELDS: Tuple[str, ...] = (
    "celebration_booking_id",
    "booking_number",
    "customer_id",
    "customer_name",
    "customer_phone",
    "occasion_name",
    "occasion_type",
    "occasion_notes",
    "booking_date",
    "start_time",
    "duration_minutes",
    "guest_count",
    "reference_images",
    "theme_preferences",
    "color_preferences",
    "setup_notes",
    "requested_addons",
    "special_requests",
    "total_price",
    "payment_status",
    "booking_status",
    "hilm_followup_status",
)

CELEBRATION_ADDONS: Tuple[str, ...] = (
    "makeup_service",
    "juice_service",
    "meal_service",
    "balloons_and_decor",
    "photography",
    "no_photography",
    "music_playlist",
    "no_music",
    "screen_or_display_content",
    "cake_or_dessert_when_available",
    "coffee_and_hot_drinks",
    "custom_flower_or_table_setup",
    "gift_or_welcome_setup",
    "other_custom_request",
)

CELEBRATION_MEDIA_FIELDS: Tuple[str, ...] = (
    "customer_reference_images",
    "decoration_reference_images",
    "cake_or_table_reference_images",
    "makeup_reference_images",
    "screen_content_images_or_files",
)

CELEBRATION_BOOKING_FLOW: Tuple[str, ...] = (
    "authenticate_customer",
    "select_celebration_room",
    "enter_occasion_name_and_type",
    "select_booking_date_start_time_and_duration",
    "enter_guest_count",
    "upload_reference_images",
    "capture_theme_colors_and_preferences",
    "select_requested_addons",
    "capture_special_requests",
    "check_room_availability_and_conflicts",
    "check_addon_availability",
    "calculate_room_and_addon_total",
    "review_complete_event_summary",
    "checkout_through_shared_payment_gateway",
    "verify_payment_server_side",
    "create_canonical_celebration_booking",
    "sync_to_cashier_management_and_hilm",
    "hilm_follows_requirements_before_event",
    "send_confirmation_and_reminders",
)

HILM_CELEBRATION_FOLLOWUP_STATES: Tuple[str, ...] = (
    "booking_received",
    "requirements_reviewed",
    "reference_images_reviewed",
    "addons_confirmed",
    "setup_in_progress",
    "ready_for_event",
    "event_active",
    "event_completed",
    "post_event_followup",
)


@dataclass(frozen=True)
class CelebrationRoomBookingContract:
    website_booking_supported: bool = True
    customer_can_upload_reference_images: bool = True
    occasion_name_and_type_are_captured: bool = True
    booking_time_and_duration_are_required: bool = True
    addons_are_selectable: bool = True
    photography_preference_supported: bool = True
    music_preference_supported: bool = True
    food_and_drink_requests_supported: bool = True
    decoration_and_balloon_requests_supported: bool = True
    makeup_addon_supported: bool = True
    shared_payment_gateway_is_used: bool = True
    payment_must_be_server_verified: bool = True
    hilm_tracks_event_requirements_end_to_end: bool = True
    cashier_management_and_hilm_share_one_booking: bool = True


def celebration_room_booking_contract() -> CelebrationRoomBookingContract:
    return CelebrationRoomBookingContract()
