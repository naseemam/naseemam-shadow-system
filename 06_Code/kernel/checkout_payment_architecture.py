"""Checkout and payment architecture for Hilm Alnada.

Supports card/wallet gateway integration plus buy-now-pay-later providers such as
Tabby and Tamara when merchant accounts and authenticated connectors are configured.
Actual charging/financial commitment remains subject to the existing sovereign
gate at the moment funds are committed.
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

CHECKOUT_FLOW: Tuple[str, ...] = (
    "require_authenticated_customer",
    "load_cart_or_booking",
    "validate_prices_and_offer_eligibility",
    "apply_loyalty_or_package_redemption_when_selected",
    "select_payment_method",
    "create_payment_attempt",
    "redirect_or_render_provider_checkout_when_required",
    "receive_provider_result",
    "verify_payment_server_side",
    "mark_order_or_booking_paid_only_after_verification",
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
    tabby_supported_when_configured: bool = True
    tamara_supported_when_configured: bool = True
    provider_callbacks_must_be_verified_server_side: bool = True
    client_redirect_is_not_payment_proof: bool = True
    paid_state_requires_verified_provider_result: bool = True
    payment_status_syncs_to_booking_order_pos_and_management: bool = True
    actual_financial_commitment_uses_existing_sovereign_gate: bool = True
    payment_provider_credentials_are_never_exposed_to_client: bool = True


def checkout_payment_contract() -> CheckoutPaymentContract:
    return CheckoutPaymentContract()
