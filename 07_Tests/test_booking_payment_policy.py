from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_phone_and_in_person_booking_use_fifty_percent_deposit_by_default():
    mod = _load("booking_payment_policy")
    for channel in (mod.PHONE, mod.IN_PERSON):
        quote = mod.booking_payment_quote(channel, 400)
        assert quote["amount_due_at_booking"] == 200
        assert quote["remaining_before_service"] == 200
        assert quote["payment_mode"] == "fifty_percent_deposit"


def test_phone_or_in_person_customer_can_pay_in_full_at_booking():
    mod = _load("booking_payment_policy")
    quote = mod.booking_payment_quote(mod.PHONE, 400, customer_wants_full_payment=True)
    assert quote["amount_due_at_booking"] == 400
    assert quote["remaining_before_service"] == 0
    assert quote["payment_mode"] == "full_payment_selected"


def test_storefront_booking_requires_full_payment_and_has_no_deposit_option():
    mod = _load("booking_payment_policy")
    quote = mod.booking_payment_quote(mod.STOREFRONT, 400)
    assert quote["deposit_option_available"] is False
    assert quote["amount_due_at_booking"] == 400
    assert quote["remaining_before_service"] == 0
    assert quote["payment_mode"] == "full_payment_required"


def test_deposit_is_based_on_amount_given_to_policy_and_negative_amount_is_rejected():
    mod = _load("booking_payment_policy")
    assert mod.booking_payment_quote(mod.IN_PERSON, 275)["amount_due_at_booking"] == 137.5
    try:
        mod.booking_payment_quote(mod.PHONE, -1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative base amount must be rejected")


def test_booking_payment_contract_matches_approved_channel_rules():
    mod = _load("booking_payment_policy")
    contract = mod.booking_payment_contract()
    assert contract.phone_booking_deposit_percent == 50
    assert contract.in_person_booking_deposit_percent == 50
    assert contract.phone_or_in_person_full_payment_allowed is True
    assert contract.remaining_balance_due_before_service is True
    assert contract.storefront_requires_full_payment is True
    assert contract.storefront_deposit_option_available is False
