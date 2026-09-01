"""Canonical Hilm Alnada booking engine rules.

Every booking is time-bound and validated against the shared service catalog,
provider/resource availability and booking channel payment policy. Add-ons such as
coffee preorders, relaxation/private room time and celebration-room packages remain
attached to the same canonical booking and must trigger revalidation when they
change timing, resources or total price.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Optional, Tuple


BOOKING_STATES: Tuple[str, ...] = (
    "draft",
    "awaiting_payment",
    "confirmed",
    "arrived",
    "in_service",
    "completed",
    "cancelled",
    "no_show",
)

BOOKING_CHANNELS: Tuple[str, ...] = ("storefront", "phone", "in_person")

REQUIRED_BOOKING_FIELDS: Tuple[str, ...] = (
    "booking_id",
    "booking_number",
    "customer_id",
    "channel",
    "service_id",
    "scheduled_start",
    "duration_minutes",
    "scheduled_end",
    "provider_id",
    "resource_ids",
    "base_price",
    "final_price",
    "payment_status",
    "booking_status",
)

OPTIONAL_BOOKING_COMPONENTS: Tuple[str, ...] = (
    "coffee_preorder",
    "relaxation_or_private_room",
    "celebration_room",
    "active_offer_or_package",
    "home_visit",
    "retail_product_reservations",
)


def derive_end_time(start: datetime, duration_minutes: int) -> datetime:
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than zero")
    return start + timedelta(minutes=duration_minutes)


def intervals_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def conflicts_with_existing_booking(
    *,
    start: datetime,
    end: datetime,
    provider_id: Optional[str],
    resource_ids: Iterable[str],
    existing_bookings: Iterable[Mapping[str, object]],
) -> bool:
    resources = set(resource_ids)
    for booking in existing_bookings:
        if booking.get("booking_status") in {"cancelled", "no_show"}:
            continue
        other_start = booking.get("scheduled_start")
        other_end = booking.get("scheduled_end")
        if not isinstance(other_start, datetime) or not isinstance(other_end, datetime):
            continue
        if not intervals_overlap(start, end, other_start, other_end):
            continue
        same_provider = bool(provider_id) and booking.get("provider_id") == provider_id
        other_resources = set(booking.get("resource_ids") or ())
        shared_resource = bool(resources.intersection(other_resources))
        if same_provider or shared_resource:
            return True
    return False


def home_visit_block_minutes(service_duration_minutes: int, travel_buffer_before: int, travel_buffer_after: int) -> int:
    if min(service_duration_minutes, travel_buffer_before, travel_buffer_after) < 0:
        raise ValueError("home visit duration and buffers cannot be negative")
    if service_duration_minutes == 0:
        raise ValueError("service duration must be greater than zero")
    return service_duration_minutes + travel_buffer_before + travel_buffer_after


@dataclass(frozen=True)
class BookingEngineContract:
    canonical_booking_ssot: bool = True
    every_booking_requires_start_time: bool = True
    every_booking_requires_duration_or_end_time: bool = True
    provider_conflict_check_required: bool = True
    room_and_resource_conflict_check_required: bool = True
    addon_time_changes_trigger_revalidation: bool = True
    addon_price_changes_trigger_total_recalculation: bool = True
    coffee_preorder_attaches_to_booking: bool = True
    coffee_prep_timing_may_be_separate_from_service_slot: bool = True
    relaxation_room_requires_time_slot: bool = True
    celebration_room_requires_time_slot: bool = True
    home_visit_requires_service_area_validation: bool = True
    home_visit_requires_travel_buffer: bool = True
    home_visit_customer_price_is_final_price_only: bool = True
    storefront_booking_requires_full_payment: bool = True
    phone_and_in_person_booking_support_fifty_percent_deposit: bool = True
    cashier_consumes_booking_without_duplicate_entry: bool = True


def booking_engine_contract() -> BookingEngineContract:
    return BookingEngineContract()
