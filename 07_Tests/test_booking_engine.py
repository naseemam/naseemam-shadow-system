from datetime import datetime
from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_booking_requires_time_and_can_derive_end():
    mod = _load("booking_engine")
    start = datetime(2026, 9, 1, 10, 0)
    assert mod.derive_end_time(start, 90) == datetime(2026, 9, 1, 11, 30)


def test_provider_conflict_is_detected_for_overlapping_slot():
    mod = _load("booking_engine")
    existing = ({
        "scheduled_start": datetime(2026, 9, 1, 10, 0),
        "scheduled_end": datetime(2026, 9, 1, 11, 0),
        "provider_id": "p1",
        "resource_ids": (),
        "booking_status": "confirmed",
    },)
    assert mod.conflicts_with_existing_booking(
        start=datetime(2026, 9, 1, 10, 30),
        end=datetime(2026, 9, 1, 11, 30),
        provider_id="p1",
        resource_ids=(),
        existing_bookings=existing,
    ) is True


def test_room_conflict_is_detected_even_with_different_provider():
    mod = _load("booking_engine")
    existing = ({
        "scheduled_start": datetime(2026, 9, 1, 18, 0),
        "scheduled_end": datetime(2026, 9, 1, 20, 0),
        "provider_id": "p1",
        "resource_ids": ("celebration_room",),
        "booking_status": "confirmed",
    },)
    assert mod.conflicts_with_existing_booking(
        start=datetime(2026, 9, 1, 19, 0),
        end=datetime(2026, 9, 1, 21, 0),
        provider_id="p2",
        resource_ids=("celebration_room",),
        existing_bookings=existing,
    ) is True


def test_cancelled_booking_does_not_block_slot():
    mod = _load("booking_engine")
    existing = ({
        "scheduled_start": datetime(2026, 9, 1, 10, 0),
        "scheduled_end": datetime(2026, 9, 1, 11, 0),
        "provider_id": "p1",
        "resource_ids": (),
        "booking_status": "cancelled",
    },)
    assert mod.conflicts_with_existing_booking(
        start=datetime(2026, 9, 1, 10, 30),
        end=datetime(2026, 9, 1, 11, 30),
        provider_id="p1",
        resource_ids=(),
        existing_bookings=existing,
    ) is False


def test_home_visit_reserves_service_and_travel_time():
    mod = _load("booking_engine")
    assert mod.home_visit_block_minutes(60, 30, 30) == 120


def test_booking_contract_matches_store_and_pos_rules():
    mod = _load("booking_engine")
    contract = mod.booking_engine_contract()
    assert contract.every_booking_requires_start_time is True
    assert contract.provider_conflict_check_required is True
    assert contract.room_and_resource_conflict_check_required is True
    assert contract.addon_time_changes_trigger_revalidation is True
    assert contract.coffee_preorder_attaches_to_booking is True
    assert contract.celebration_room_requires_time_slot is True
    assert contract.home_visit_requires_travel_buffer is True
    assert contract.storefront_booking_requires_full_payment is True
    assert contract.phone_and_in_person_booking_support_fifty_percent_deposit is True
    assert contract.cashier_consumes_booking_without_duplicate_entry is True
