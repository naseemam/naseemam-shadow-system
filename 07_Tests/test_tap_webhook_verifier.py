import hashlib
import hmac

import pytest

from kernel.tap_webhook_verifier import tap_hash_material, tap_status_to_test_status, verify_tap_hashstring


def test_tap_hashstring_matches_official_material_shape():
    payload = {
        "id": "chg_test_1",
        "object": "charge",
        "amount": 1,
        "currency": "SAR",
        "status": "CAPTURED",
        "transaction": {"created": "1698392202943"},
        "reference": {"gateway": "gw-1", "payment": "pay-1"},
    }
    material = tap_hash_material(payload)
    assert material == "x_idchg_test_1x_amount1.00x_currencySARx_gateway_referencegw-1x_payment_referencepay-1x_statusCAPTUREDx_created1698392202943"
    signature = hmac.new(b"sk_test_example", material.encode(), hashlib.sha256).hexdigest()
    assert verify_tap_hashstring(payload, signature, "sk_test_example") is True
    assert verify_tap_hashstring(payload, signature[:-1] + "0", "sk_test_example") is False


def test_tap_status_mapping():
    assert tap_status_to_test_status("CAPTURED") == "paid"
    assert tap_status_to_test_status("REFUNDED") == "refunded"
    assert tap_status_to_test_status("DECLINED") == "failed"
    with pytest.raises(ValueError, match="unsupported_tap_status"):
        tap_status_to_test_status("INITIATED")
