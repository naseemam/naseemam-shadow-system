from __future__ import annotations

import hashlib
import hmac
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping


_CURRENCY_DECIMALS = {
    "BHD": 3, "JOD": 3, "KWD": 3, "OMR": 3,
    "AED": 2, "EGP": 2, "EUR": 2, "GBP": 2, "QAR": 2,
    "SAR": 2, "USD": 2,
}


def _get(data: Mapping[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, Mapping):
            return ""
        current = current.get(key, "")
    return current


def format_amount(value: Any, currency: str) -> str:
    decimals = _CURRENCY_DECIMALS.get(str(currency).upper(), 2)
    quant = Decimal("1").scaleb(-decimals)
    amount = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return f"{amount:.{decimals}f}"


def tap_hash_material(payload: Mapping[str, Any]) -> str:
    kind = str(payload.get("object", "charge")).lower()
    identifier = payload.get("id", "")
    amount = format_amount(payload.get("amount", "0"), str(payload.get("currency", "SAR")))
    currency = payload.get("currency", "")
    gateway_reference = _get(payload, "reference", "gateway")
    payment_reference = _get(payload, "reference", "payment")
    status = payload.get("status", "")
    if kind == "invoice":
        updated = payload.get("updated", "")
        created = payload.get("created", "")
        return f"x_id{identifier}x_amount{amount}x_currency{currency}x_updated{updated}x_status{status}x_created{created}"
    created = _get(payload, "transaction", "created")
    return f"x_id{identifier}x_amount{amount}x_currency{currency}x_gateway_reference{gateway_reference}x_payment_reference{payment_reference}x_status{status}x_created{created}"


def verify_tap_hashstring(payload: Mapping[str, Any], received_hash: str, secret_key: str | None = None) -> bool:
    secret = secret_key or os.getenv("TAP_SECRET_KEY", "")
    if not secret or not received_hash:
        return False
    material = tap_hash_material(payload)
    expected = hmac.new(secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.lower(), str(received_hash).strip().lower())


def tap_status_to_test_status(status: str) -> str:
    normalized = str(status).upper()
    if normalized in {"CAPTURED", "AUTHORIZED", "PAID", "SUCCESS"}:
        return "paid"
    if normalized in {"REFUNDED", "REFUND", "VOIDED"}:
        return "refunded"
    if normalized in {"FAILED", "DECLINED", "CANCELLED", "CANCELED"}:
        return "failed"
    raise ValueError("unsupported_tap_status")
