"""Razorpay order creation and payment-signature verification for exam
registration fees.

If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not configured (local/dev),
falls back to a "mock" mode: create_order() returns a locally-generated
order id, and verify_signature() accepts any payment id as long as the
signature matches what a mock client would produce with the same
(unset) secret. This keeps the booking flow testable without live
credentials, while the code path used in production is the same either
way. Point RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET at real credentials to
go live — no code changes needed.
"""

import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Any

import httpx

from core.settings import Settings

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"


def is_live() -> bool:
    return bool(Settings.RAZORPAY_KEY_ID and Settings.RAZORPAY_KEY_SECRET)


async def create_order(*, amount: Decimal, currency: str, receipt: str) -> dict[str, Any]:
    """Returns a dict with at least an 'id' key (the order id)."""
    if not is_live():
        return {"id": f"mock_order_{uuid.uuid4().hex[:20]}", "status": "created"}

    paise = int((amount * 100).to_integral_value())
    async with httpx.AsyncClient(
        base_url=RAZORPAY_BASE_URL,
        auth=(Settings.RAZORPAY_KEY_ID, Settings.RAZORPAY_KEY_SECRET),
        timeout=15.0,
    ) as client:
        resp = await client.post(
            "/orders",
            json={"amount": paise, "currency": currency, "receipt": receipt},
        )
        resp.raise_for_status()
        return resp.json()


def verify_signature(*, order_id: str, payment_id: str, signature: str) -> bool:
    secret = Settings.RAZORPAY_KEY_SECRET or "mock-secret"
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def sign_mock_payment(order_id: str, payment_id: str) -> str:
    """Test helper: produces a signature that verify_signature() will accept
    in mock mode (no Razorpay keys configured). Not used in production code
    paths — exists so integration tests can simulate a successful checkout."""
    secret = Settings.RAZORPAY_KEY_SECRET or "mock-secret"
    payload = f"{order_id}|{payment_id}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
