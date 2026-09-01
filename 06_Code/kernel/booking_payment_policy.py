"""Booking payment rules for Hilm Alnada by booking channel.

Phone and in-person bookings require a 50% deposit calculated from the canonical
base service amount, unless the customer elects to pay in full at booking. The
remaining balance must be paid before service execution. Storefront bookings require
full payment at booking and do not expose a deposit option.
"""

from dataclasses import dataclass
from typing import Dict


PHONE = "phone"
IN_PERSON = "in_person"
STOREFRONT = "storefront"

DEPOSIT_RATE = 0.50


def booking_payment_quote(channel: str, base_amount: float, customer_wants_full_payment: bool = False) -> Dict[str, float | str | bool]:
    if base_amount < 0:
        raise ValueError("base amount cannot be negative")

    if channel == STOREFRONT:
        return {
            "channel": channel,
            "base_amount": base_amount,
            "deposit_option_available": False,
            "amount_due_at_booking": base_amount,
            "remaining_before_service": 0.0,
            "payment_mode": "full_payment_required",
        }

    if channel in {PHONE, IN_PERSON}:
        if customer_wants_full_payment:
            return {
                "channel": channel,
                "base_amount": base_amount,
                "deposit_option_available": True,
                "amount_due_at_booking": base_amount,
                "remaining_before_service": 0.0,
                "payment_mode": "full_payment_selected",
            }
        deposit = round(base_amount * DEPOSIT_RATE, 2)
        return {
            "channel": channel,
            "base_amount": base_amount,
            "deposit_option_available": True,
            "amount_due_at_booking": deposit,
            "remaining_before_service": round(base_amount - deposit, 2),
            "payment_mode": "fifty_percent_deposit",
        }

    raise ValueError(f"unsupported booking channel: {channel}")


@dataclass(frozen=True)
class BookingPaymentContract:
    phone_booking_deposit_percent: int = 50
    in_person_booking_deposit_percent: int = 50
    phone_or_in_person_full_payment_allowed: bool = True
    deposit_is_calculated_from_base_amount: bool = True
    remaining_balance_due_before_service: bool = True
    storefront_requires_full_payment: bool = True
    storefront_deposit_option_available: bool = False


def booking_payment_contract() -> BookingPaymentContract:
    return BookingPaymentContract()
