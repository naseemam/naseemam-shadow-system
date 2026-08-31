"""Checkout and payment architecture for Hilm Alnada.

Supports the shared storefront payment gateway for service bookings, home visits,
retail products, fabrics, online tailoring orders, packages and gifts. It also
supports card/wallet methods plus buy-now-pay-later providers such as Tabby and
Tamara when merchant accounts and authenticated connectors are configured.

An ordinary customer paying for the customer's own order or booking is commerce
fulfilment, not a Founder sovereign financial commitment. The Founder financial
gate applies when Ameer or the business commits Founder/business funds, not when
a customer independently completes checkout.
"""

from dataclasses import dataclass
from typing import Tuple

PAYMENT_METHODS: Tuple[str, ...] = (
    "card_gateway",
    "apple_pay_when_supported",
    "mada_when_supported",
    "tabby_when_merchant_enabled",
    "tamara_when_merchant_enabled",
    "cash_at_center_when_enabled",
    "loyalty_reward_redemption",
    "package_or_gift_code_redemption",
)

PAYABLE_COMMERCE_TYPES: Tuple[str, ...] = (
    "service_booking",
    "home_visit_booking",
    "retail_product_order",
    "fabric_order",
    "online_tailoring_order",
    "package_purchase",
    "gift_purchase",
)

CHECKOUT_FLOW: Tuple[str, ...] = (
    "require_authenticated_customer",
    "load_cart_booking_or_tailoring_order",
    "validate_prices_inventory_and_offer_eligibility",
    "apply_loyalty_or_package_redemption_when_selected",
    "select_payment_method",
    "create_payment_attempt",
    "redirect_or_render_provider_checkout_when_required",
    "receive_provider_result",
    "verify_payment_server_side",
    "mark_order_or_booking_paid_only_after_verification",
    "finalize_reserved_inventory_or_fabric_when_applicable",
    "issue_invoice_or_receipt",
    "sync_status_to_pos_and_management",
    "send_customer_confirmation",
)

PAYMENT_STATES: Tuple[str, ...] = (
    "pending",
    "requires_customer_action",
    "authorized",
    "paid",
    "failed",
    "cancelled",
    "refunded",
    "partially_refunded",
)

@dataclass(frozen=True)
class CheckoutPaymentContract:
    shared_gateway_serves_all_storefront_commerce: bool = True
    tailoring_orders_use_shared_gateway: bool = True
    fabric_orders_use_shared_gateway: bool = True
    tabby_supported_when_configured: bool = True
    tamara_supported_when_configured: bool = True
    provider_callbacks_must_be_verified_server_side: bool = True
    client_redirect_is_not_payment_proof: bool = True
    paid_state_requires_verified_provider_result: bool = True
    payment_status_syncs_to_booking_order_pos_and_management: bool = True
    ordinary_customer_payment_requires_founder_approval: bool = False
    founder_financial_gate_applies_to_business_spend_not_customer_checkout: bool = True
    payment_provider_credentials_are_never_exposed_to_client: bool = True


def checkout_payment_contract() -> CheckoutPaymentContract:
    return CheckoutPaymentContract()
