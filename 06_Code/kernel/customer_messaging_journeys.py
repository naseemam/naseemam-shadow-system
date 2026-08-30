"""Proactive customer messaging journeys for Hilm Alnada.

Hilm, the digital storefront employee, may proactively communicate with registered
customers through authenticated messaging connectors. Messages are tied to the
canonical customer profile and customer journey, not isolated marketing blasts.
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
    multiple_customer_sessions_are_isolated: bool = True
    authenticated_connector_required_for_external_delivery: bool = True
    must_respect_customer_contact_preferences_and_channel_rules: bool = True
    must_record_delivery_and_conversion: bool = True


def customer_messaging_contract() -> CustomerMessagingContract:
    return CustomerMessagingContract()
