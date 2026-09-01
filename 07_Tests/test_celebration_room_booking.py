import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_celebration_booking_captures_time_duration_and_reference_images():
    mod = _load("celebration_room_booking")
    assert "occasion_name" in mod.CELEBRATION_BOOKING_FIELDS
    assert "start_time" in mod.CELEBRATION_BOOKING_FIELDS
    assert "duration_minutes" in mod.CELEBRATION_BOOKING_FIELDS
    assert "reference_images" in mod.CELEBRATION_BOOKING_FIELDS
    contract = mod.celebration_room_booking_contract()
    assert contract.customer_can_upload_reference_images is True
    assert contract.booking_time_and_duration_are_required is True


def test_customer_can_choose_event_addons_and_preferences():
    mod = _load("celebration_room_booking")
    for addon in (
        "makeup_service",
        "juice_service",
        "meal_service",
        "balloons_and_decor",
        "photography",
        "no_photography",
        "music_playlist",
        "no_music",
    ):
        assert addon in mod.CELEBRATION_ADDONS


def test_celebration_booking_uses_shared_payment_and_single_record():
    mod = _load("celebration_room_booking")
    contract = mod.celebration_room_booking_contract()
    assert contract.shared_payment_gateway_is_used is True
    assert contract.payment_must_be_server_verified is True
    assert contract.cashier_management_and_hilm_share_one_booking is True
    assert "checkout_through_shared_payment_gateway" in mod.CELEBRATION_BOOKING_FLOW
    assert "sync_to_cashier_management_and_hilm" in mod.CELEBRATION_BOOKING_FLOW


def test_hilm_follows_event_requirements_before_and_after_event():
    mod = _load("celebration_room_booking")
    assert "requirements_reviewed" in mod.HILM_CELEBRATION_FOLLOWUP_STATES
    assert "addons_confirmed" in mod.HILM_CELEBRATION_FOLLOWUP_STATES
    assert "ready_for_event" in mod.HILM_CELEBRATION_FOLLOWUP_STATES
    assert "post_event_followup" in mod.HILM_CELEBRATION_FOLLOWUP_STATES
