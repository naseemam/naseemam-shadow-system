"""Hilm Alnada storefront as an autonomous 24/24 sales agent.

The storefront is not a passive catalogue. It guides each customer from discovery
through recommendation, booking, cart, payment handoff, fulfilment and review.
"""

from dataclasses import dataclass
from typing import Tuple


CUSTOMER_JOURNEY: Tuple[str, ...] = (
    "enter_storefront",
    "understand_customer_need",
    "browse_service_catalog",
    "recommend_services",
    "recommend_service_provider",
    "check_availability",
    "create_or_update_booking",
    "build_cart",
    "apply_eligible_offer",
    "checkout",
    "payment_handoff",
    "purchase_confirmation",
    "pre_visit_followup",
    "service_fulfilment",
    "request_employee_rating",
    "retention_followup",
)

STOREFRONT_COMPONENTS: Tuple[str, ...] = (
    "service_categories",
    "service_catalog",
    "service_detail_pages",
    "prices",
    "provider_profiles",
    "recommendations",
    "availability",
    "booking",
    "cart",
    "buy_now",
    "checkout",
    "payment",
    "order_confirmation",
    "booking_number",
    "customer_account",
    "offers",
    "employee_rating",
)


@dataclass(frozen=True)
class StorefrontSalesAgentContract:
    availability: str = "24/24"
    waits_for_founder_to_open_chat: bool = False
    may_recommend_services: bool = True
    may_recommend_service_provider: bool = True
    may_create_booking: bool = True
    may_prepare_cart_and_checkout: bool = True
    may_prepare_and_apply_operational_offers: bool = True
    may_request_employee_rating: bool = True
    final_financial_commitment_requires_sovereign_gate: bool = True


def storefront_sales_agent_contract() -> StorefrontSalesAgentContract:
    return StorefrontSalesAgentContract()
