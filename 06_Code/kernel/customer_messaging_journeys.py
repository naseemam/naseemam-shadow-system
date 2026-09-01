"""Proactive customer messaging journeys for Hilm Alnada.

Hilm, the digital storefront employee, may proactively communicate with registered
customers through authenticated messaging connectors. Messages are tied to the
canonical customer profile and customer journey, not isolated marketing blasts.
Tailoring orders receive end-to-end follow-up, including measurements, fabric,
fittings, alteration requests, reference images, readiness and delivery/pickup.
"""

from dataclasses import dataclass
from typing import Tuple


MESSAGE_TRIGGERS: Tuple[str, ...] = (
    "relevant_offer_available",
    "service_recommendation_available",
    "abandoned_service_or_booking_journey",
    "abandoned_cart_or_checkout",
    "booking_started_not_completed",
    "booking_confirmation",
    "appointment_reminder",
    "loyalty_reward_earned",
    "free_service_reward_available",
    "package_or_gift_available",
    "post_service_followup",
    "employee_rating_request",
    "customer_reactivation_opportunity",
    "tailoring_order_received",
    "tailoring_measurements_need_confirmation",
    "tailoring_fabric_confirmed",
    "tailoring_sent_to_tailor",
    "tailoring_fitting_required",
    "tailoring_alteration_requested",
    "tailoring_alteration_status_changed",
    "tailoring_reference_image_received",
    "tailoring_ready_for_final_review",
    "tailoring_ready_for_pickup_or_delivery",
    "tailoring_completed",
)

MESSAGE_ACTIONS: Tuple[str, ...] = (
    "select_relevant_customer_segment",
    "personalize_message_from_customer_profile",
    "include_relevant_store_or_booking_link",
    "resume_customer_journey_from_link",
    "recommend_service_or_package",
    "help_complete_booking",
    "help_complete_checkout",
    "send_reward_code_when_applicable",
    "follow_up_until_completed_or_no_longer_relevant",
    "record_delivery_and_conversion_outcome",
    "show_tailoring_order_number_and_current_status",
    "confirm_selected_measurement_profile",
    "collect_or_confirm_tailoring_reference_images",
    "collect_alteration_notes_and_images",
    "coordinate_fitting_when_required",
    "confirm_pickup_or_delivery_details",
)

TAILORING_FOLLOWUP_JOURNEY: Tuple[str, ...] = (
    "confirm_order_and_payment",
    "confirm_measurement_profile_and_snapshot",
    "confirm_fabric_selection_or_customer_owned_fabric",
    "confirm_reference_images_and_design_notes",
    "notify_when_work_order_is_sent_to_tailor",
    "track_in_tailoring_status",
    "coordinate_fitting_when_required",
    "capture_alteration_request_notes_and_images",
    "track_alteration_progress",
    "notify_ready_for_final_review",
    "notify_ready_for_pickup_or_delivery",
    "confirm_completion",
    "request_tailoring_rating_and_feedback",
)

CHANNELS: Tuple[str, ...] = (
    "whatsapp_when_authenticated",
    "email_when_authenticated",
    "storefront_inbox_or_account",
)


@dataclass(frozen=True)
class CustomerMessagingContract:
    identity: str = "Hilm"
    availability: str = "24/24"
    proactive: bool = True
    waits_for_founder_to_send_routine_messages: bool = False
    supports_personalized_store_links: bool = True
    supports_booking_completion_links: bool = True
    supports_loyalty_reward_messages: bool = True
    supports_offer_and_service_promotion: bool = True
    supports_post_service_followup: bool = True
    supports_employee_rating_request: bool = True
    supports_end_to_end_tailoring_followup: bool = True
    supports_tailoring_alteration_notes_and_images: bool = True
    supports_tailoring_fitting_coordination: bool = True
    multiple_customer_sessions_are_isolated: bool = True
    authenticated_connector_required_for_external_delivery: bool = True
    must_respect_customer_contact_preferences_and_channel_rules: bool = True
    must_record_delivery_and_conversion: bool = True


def customer_messaging_contract() -> CustomerMessagingContract:
    return CustomerMessagingContract()
