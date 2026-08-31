from datetime import date

import pytest

from kernel.customer_account_booking_pos_runtime import (
    LoyaltyEvent,
    PackageEntitlement,
    apply_loyalty_event,
    booking_completion_loyalty_event,
    booking_to_pos_ticket,
    customer_account_projection,
    deduplicate_pos_tickets,
    redeem_package,
    runtime_contract,
)


def _booking(**overrides):
    booking = {
        "booking_id": "bk-1",
        "booking_number": "HN-1001",
        "customer_id": "cus-1",
        "service_id": "svc-hair-1",
        "provider_id": "emp-7",
        "scheduled_start": "2026-09-01T16:00:00+03:00",
        "final_price": 250,
        "payment_status": "paid",
        "booking_status": "confirmed",
        "active_offer_or_package": None,
    }
    booking.update(overrides)
    return booking


def test_customer_account_projection_uses_one_canonical_identity_and_hides_internal_fields():
    profile = {
        "customer_id": "cus-1",
        "display_name": "عميلة حلم الندى",
        "mobile": "+966500000000",
        "email": "customer@example.test",
        "auth_subject": "auth0|customer-1",
        "loyalty_points": 120,
        "internal_risk_note": "must-not-leak",
    }
    projection = customer_account_projection(profile)
    assert projection["customer_id"] == "cus-1"
    assert projection["auth_subject"] == "auth0|customer-1"
    assert "internal_risk_note" not in projection


def test_booking_projects_directly_to_cashier_without_duplicate_reentry():
    ticket = booking_to_pos_ticket(_booking())
    assert ticket["ticket_source"] == "booking"
    assert ticket["source_booking_id"] == "bk-1"
    assert ticket["customer_id"] == "cus-1"
    assert ticket["service_id"] == "svc-hair-1"
    assert ticket["price_snapshot"] == 250
    assert ticket["cashier_requires_manual_reentry"] is False
    assert ticket["idempotency_key"] == "booking:bk-1"


def test_cashier_projection_is_idempotent_per_booking():
    first = booking_to_pos_ticket(_booking())
    duplicate = dict(first)
    unique = booking_to_pos_ticket(_booking(booking_id="bk-2", booking_number="HN-1002"))
    result = deduplicate_pos_tickets((first, duplicate, unique))
    assert len(result) == 2
    assert {item["source_booking_id"] for item in result} == {"bk-1", "bk-2"}


def test_gift_package_tracks_purchaser_beneficiary_and_remaining_uses():
    gift = PackageEntitlement(
        entitlement_id="ent-1",
        package_id="pkg-bridal-1",
        purchaser_customer_id="cus-buyer",
        beneficiary_customer_id="cus-recipient",
        redemption_code="GIFT-ABC123",
        eligible_service_ids=("svc-hair-1", "svc-makeup-1"),
        remaining_uses=2,
        expires_on=date(2026, 12, 31),
    )
    updated = redeem_package(
        gift,
        service_id="svc-hair-1",
        customer_id="cus-recipient",
        as_of=date(2026, 9, 1),
    )
    assert updated.purchaser_customer_id == "cus-buyer"
    assert updated.beneficiary_customer_id == "cus-recipient"
    assert updated.remaining_uses == 1
    assert updated.status == "active"


def test_package_rejects_wrong_beneficiary_or_ineligible_service():
    gift = PackageEntitlement(
        entitlement_id="ent-1",
        package_id="pkg-1",
        purchaser_customer_id="cus-buyer",
        beneficiary_customer_id="cus-recipient",
        redemption_code="GIFT-1",
        eligible_service_ids=("svc-1",),
        remaining_uses=1,
    )
    with pytest.raises(ValueError, match="package_wrong_beneficiary"):
        redeem_package(gift, service_id="svc-1", customer_id="cus-other")
    with pytest.raises(ValueError, match="service_not_eligible_for_package"):
        redeem_package(gift, service_id="svc-2", customer_id="cus-recipient")


def test_loyalty_credit_requires_completed_paid_booking_and_is_exactly_once():
    completed = _booking(booking_status="completed", payment_status="paid")
    event = booking_completion_loyalty_event(completed, points_earned=25)
    balance, processed = apply_loyalty_event(
        current_balance=100,
        processed_event_ids=(),
        event=event,
    )
    assert balance == 125
    same_balance, same_processed = apply_loyalty_event(
        current_balance=balance,
        processed_event_ids=processed,
        event=event,
    )
    assert same_balance == 125
    assert same_processed == processed


def test_loyalty_does_not_credit_unpaid_or_unfinished_booking():
    with pytest.raises(ValueError, match="booking_not_completed"):
        booking_completion_loyalty_event(_booking(), points_earned=20)
    with pytest.raises(ValueError, match="booking_not_paid"):
        booking_completion_loyalty_event(
            _booking(booking_status="completed", payment_status="pending"),
            points_earned=20,
        )


def test_loyalty_redemption_cannot_create_negative_balance():
    event = LoyaltyEvent(
        event_id="redeem:1",
        customer_id="cus-1",
        source_type="reward_redemption",
        source_id="reward-1",
        points_delta=-150,
    )
    with pytest.raises(ValueError, match="insufficient_loyalty_points"):
        apply_loyalty_event(current_balance=100, processed_event_ids=(), event=event)


def test_runtime_contract_covers_end_to_end_identity_booking_pos_and_loyalty():
    contract = runtime_contract()
    assert contract.one_customer_identity_across_storefront_booking_pos_management is True
    assert contract.booking_projects_to_pos_without_manual_reentry is True
    assert contract.booking_id_is_pos_idempotency_source is True
    assert contract.gift_keeps_purchaser_and_beneficiary_separate is True
    assert contract.loyalty_events_are_idempotent is True
