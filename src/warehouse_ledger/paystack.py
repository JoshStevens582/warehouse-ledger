from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any

import httpx

from warehouse_ledger.config import get_settings


def verify_webhook_signature(payload: bytes, signature: str | None) -> bool:
    secret = get_settings().paystack_secret_key
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


async def initialize_transaction(
    *,
    email: str,
    amount: Decimal,
    reference: str,
    currency: str = "ZAR",
    callback_url: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.paystack_secret_key:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not set")
    kobo = int(amount * 100)
    body = {
        "email": email,
        "amount": kobo,
        "reference": reference,
        "currency": currency,
        "callback_url": callback_url or settings.checkout_callback_url,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {settings.paystack_secret_key}",
                "Content-Type": "application/json",
            },
            content=json.dumps(body),
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("status"):
            raise RuntimeError(data.get("message", "Paystack initialize failed"))
        inner = data["data"]
        if not isinstance(inner, dict):
            raise RuntimeError("Unexpected Paystack response")
        return inner
