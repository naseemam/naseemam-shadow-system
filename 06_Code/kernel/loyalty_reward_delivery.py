"""Loyalty threshold reward and customer delivery contract for Hilm Alnada.

When a customer reaches the configured loyalty threshold, the system grants a free
service reward and delivers it through WhatsApp when an authenticated connector is
available. The reward remains linked to the canonical customer profile and may be
redeemed through booking/POS using its code.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoyaltyRewardContract:
    threshold_is_configurable: bool = True
    grants_free_service_at_threshold: bool = True
    reward_linked_to_customer_profile: bool = True
    reward_has_redeemable_code: bool = True
    reward_visible_in_booking_and_pos: bool = True
    whatsapp_delivery_when_authenticated: bool = True
    waits_for_founder_to_send_reward: bool = False
    connector_absence_is_technical_blocker_not_approval_gate: bool = True


def loyalty_reward_contract() -> LoyaltyRewardContract:
    return LoyaltyRewardContract()
