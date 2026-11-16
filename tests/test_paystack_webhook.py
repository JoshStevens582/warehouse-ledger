from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import login
from warehouse_ledger.config import get_settings
from warehouse_ledger.models import Order, OrderStatus, Product


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


@pytest.fixture()
def paystack_secret(monkeypatch: pytest.MonkeyPatch) -> Generator[str, None, None]:
    secret = "sk_test_local_only"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)
    get_settings.cache_clear()
    yield secret
    get_settings.cache_clear()


def test_webhook_idempotent(
    client: TestClient,
    session_factory: sessionmaker[Session],
    paystack_secret: str,
) -> None:
    supervisor_token = login(client, "supervisor@example.com", "supervisor123")
    db = session_factory()
    try:
        product_id = db.scalar(select(Product.id).where(Product.sku == "BOX-7A"))
        assert product_id is not None
    finally:
        db.close()

    order_resp = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {supervisor_token}"},
        json={
            "customer_email": "buyer@example.com",
            "lines": [{"product_id": product_id, "quantity": 1, "unit_price": "99.00"}],
        },
    )
    order_id = order_resp.json()["id"]
    reference = f"wh-test-{order_id}"

    db = session_factory()
    try:
        order = db.get(Order, order_id)
        assert order is not None
        order.paystack_reference = reference
        db.commit()
    finally:
        db.close()

    event_id = secrets.randbelow(2_000_000_000) + 1
    payload = {
        "event": "charge.success",
        "data": {
            "id": event_id,
            "reference": reference,
            "amount": 9900,
            "currency": "ZAR",
        },
    }
    body = json.dumps(payload).encode()
    signature = _sign(body, paystack_secret)

    first = client.post(
        "/api/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": signature, "content-type": "application/json"},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "ok"

    second = client.post(
        "/api/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": signature, "content-type": "application/json"},
    )
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    order_get = client.get(
        f"/api/orders/{order_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert order_get.json()["status"] == OrderStatus.paid.value

    payments = client.get(
        f"/api/orders/{order_id}/payments",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert len(payments.json()) == 1
