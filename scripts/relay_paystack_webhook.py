"""Post a signed charge.success webhook to the local API (when Paystack cannot reach localhost).

Usage (from workspace root, secret only in .env):

    uv run python warehouse-ledger/scripts/relay_paystack_webhook.py wh-1-abc123
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sys

import httpx

from warehouse_ledger.config import get_settings


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: relay_paystack_webhook.py <paystack_reference>", file=sys.stderr)
        raise SystemExit(2)
    reference = sys.argv[1]
    secret = get_settings().paystack_secret_key
    if not secret:
        print("PAYSTACK_SECRET_KEY is not set in .env", file=sys.stderr)
        raise SystemExit(1)
    event_id = secrets.randbelow(2_000_000_000) + 1
    payload = {
        "event": "charge.success",
        "data": {
            "id": event_id,
            "reference": reference,
            "amount": 5000,
            "currency": "ZAR",
        },
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    response = httpx.post(
        "http://127.0.0.1:8080/api/webhooks/paystack",
        content=body,
        headers={
            "content-type": "application/json",
            "x-paystack-signature": signature,
        },
        timeout=30.0,
    )
    print(response.status_code, response.text)


if __name__ == "__main__":
    main()