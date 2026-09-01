"""Customer account -> booking -> POS -> package/gift -> loyalty integration runtime.

This module turns the existing Hilm commerce contracts into deterministic integration
helpers. It does not replace persistence, authentication providers, payment gateways,
or the canonical service catalog. It defines the shared identifiers and idempotent
transitions those runtimes must preserve.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple


ACCOUNT_REQUIRED_FIELDS: Tuple[str, ...] = (
    "customer_id",
    "display_name",
    "mobile",
    "auth_subject",
)

BOOKING_TO_POS_REQUIRED_FIELDS: Tuple[str, ...] = (
    "booking_id",
    "booking_number",
    "customer_id",
    "service_id",
    "final_price",
    "payment_status",
    "booking_status",
)


def _required(record: Mapping[str, object], fields: Iterable[str], label: str) -> None:
    missing = [field for field in fields if record.get(field) in (None, "")]
    if missing:
        raise ValueError(f"{label}_missing_required_fields:{','.join(missing)}")


def customer_account_projection(profile: Mapping[str, object]) -> Dict[str, object]:
    """Return the customer-facing projection without exposing internal-only fields."""
    _required(profile, ACCOUNT_REQUIRED_FIELDS, "customer_profile")
    allowed = (
        "customer_id",
        "display_name",
        "mobile",
        "email",
        "auth_subject",
        "loyalty_points",
        "loyalty_tier",
        "active_package_ids",
        "gift_code_ids",
        "saved_measurement_profile_ids",
    )
    return {key: profile.get(key) for key in allowed if key in profile}


def booking_to_pos_ticket(booking: Mapping[str, object]) -> Dict[str, object]:
    """Project one canonical booking into POS without duplicate data entry.

    The booking id is the idempotency/source key. Price is a booking snapshot; the
    cashier must not silently re-key the customer, service, or booked price.
    """
    _required(booking, BOOKING_TO_POS_REQUIRED_FIELDS, "booking")
    return {
        "ticket_source": "booking",
        "source_booking_id": booking["booking_id"],
        "idempotency_key": f"booking:{booking['booking_id']}",
        "booking_number": booking["booking_number"],
        "customer_id": booking["customer_id"],
        "service_id": booking["service_id"],
        "provider_id": booking.get("provider_id"),
        "scheduled_start": booking.get("scheduled_start"),
        "booking_status": booking["booking_status"],
        "payment_status": booking["payment_status"],
        "price_snapshot": booking["final_price"],
        "package_or_offer_id": booking.get("active_offer_or_package"),
        "cashier_requires_manual_reentry": False,
    }


def deduplicate_pos_tickets(tickets: Sequence[Mapping[str, object]]) -> Tuple[Dict[str, object], ...]:
    """Keep one POS projection per canonical booking idempotency key."""
    seen = set()
    result = []
    for ticket in tickets:
        key = ticket.get("idempotency_key")
        if not key:
            raise ValueError("pos_ticket_missing_idempotency_key")
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(ticket))
    return tuple(result)


@dataclass(frozen=True)
class PackageEntitlement:
    entitlement_id: str
    package_id: str
    purchaser_customer_id: str
    beneficiary_customer_id: str
    redemption_code: str
    eligible_service_ids: Tuple[str, ...]
    remaining_uses: int
    expires_on: Optional[date] = None
    status: str = "active"


def redeem_package(
    entitlement: PackageEntitlement,
    *,
    service_id: str,
    customer_id: str,
    as_of: Optional[date] = None,
) -> PackageEntitlement:
    if entitlement.status != "active":
        raise ValueError("package_not_active")
    if entitlement.beneficiary_customer_id != customer_id:
        raise ValueError("package_wrong_beneficiary")
    if service_id not in entitlement.eligible_service_ids:
        raise ValueError("service_not_eligible_for_package")
    if entitlement.remaining_uses <= 0:
        raise ValueError("package_exhausted")
    today = as_of or date.today()
    if entitlement.expires_on and today > entitlement.expires_on:
        raise ValueError("package_expired")
    remaining = entitlement.remaining_uses - 1
    return replace(entitlement, remaining_uses=remaining, status="consumed" if remaining == 0 else "active")


@dataclass(frozen=True)
class LoyaltyEvent:
    event_id: str
    customer_id: str
    source_type: str
    source_id: str
    points_delta: int


def apply_loyalty_event(
    *,
    current_balance: int,
    processed_event_ids: Iterable[str],
    event: LoyaltyEvent,
) -> Tuple[int, Tuple[str, ...]]:
    """Apply a loyalty event exactly once and never allow a negative balance."""
    seen = tuple(processed_event_ids)
    if event.event_id in seen:
        return current_balance, seen
    next_balance = current_balance + event.points_delta
    if next_balance < 0:
        raise ValueError("insufficient_loyalty_points")
    return next_balance, (*seen, event.event_id)


def booking_completion_loyalty_event(
    booking: Mapping[str, object], *, points_earned: int
) -> LoyaltyEvent:
    _required(booking, ("booking_id", "customer_id", "booking_status", "payment_status"), "booking")
    if booking["booking_status"] != "completed":
        raise ValueError("booking_not_completed")
    if booking["payment_status"] not in {"paid", "captured"}:
        raise ValueError("booking_not_paid")
    if points_earned < 0:
        raise ValueError("points_earned_must_be_non_negative")
    booking_id = str(booking["booking_id"])
    return LoyaltyEvent(
        event_id=f"booking-completed:{booking_id}",
        customer_id=str(booking["customer_id"]),
        source_type="booking",
        source_id=booking_id,
        points_delta=points_earned,
    )


@dataclass(frozen=True)
class CustomerCommerceRuntimeContract:
    one_customer_identity_across_storefront_booking_pos_management: bool = True
    auth_subject_maps_to_canonical_customer_id: bool = True
    booking_projects_to_pos_without_manual_reentry: bool = True
    booking_id_is_pos_idempotency_source: bool = True
    package_and_gift_entitlements_are_customer_bound: bool = True
    gift_keeps_purchaser_and_beneficiary_separate: bool = True
    redemption_updates_remaining_entitlements: bool = True
    loyalty_events_are_idempotent: bool = True
    loyalty_credit_requires_completed_paid_booking: bool = True
    customer_profile_internal_fields_are_not_exposed_by_default: bool = True


def runtime_contract() -> CustomerCommerceRuntimeContract:
    return CustomerCommerceRuntimeContract()
