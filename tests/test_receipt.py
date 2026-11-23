from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import login
from warehouse_ledger.config import get_settings
from warehouse_ledger.models import Order, Payment, Product, Receipt
from warehouse_ledger.services.receipts import ReceiptNotReady, write_payment_receipt
from warehouse_ledger.worker import WorkerSettings, send_payment_receipt


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


def _paid_order(
    client: TestClient,
    session_factory: sessionmaker[Session],
    secret: str,
) -> tuple[str, int, int]:
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
            "lines": [{"product_id": product_id, "quantity": 2, "unit_price": "10.50"}],
        },
    )
    assert order_resp.status_code == 201
    order_id = int(order_resp.json()["id"])
    reference = f"wh-receipt-{order_id}"
    db = session_factory()
    try:
        order = db.get(Order, order_id)
        assert order is not None
        order.paystack_reference = reference
        db.commit()
    finally:
        db.close()

    payload = {
        "event": "charge.success",
        "data": {
            "id": secrets.randbelow(2_000_000_000) + 1,
            "reference": reference,
            "amount": 2100,
            "currency": "ZAR",
        },
    }
    body = json.dumps(payload).encode()
    paid = client.post(
        "/api/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": _sign(body, secret), "content-type": "application/json"},
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "ok"
    return supervisor_token, order_id, product_id


@pytest.fixture()
def paystack_secret(monkeypatch: pytest.MonkeyPatch) -> Generator[str, None, None]:
    secret = "sk_test_local_only"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)
    get_settings.cache_clear()
    yield secret
    get_settings.cache_clear()


def test_receipt_is_written_once(
    client: TestClient,
    session_factory: sessionmaker[Session],
    paystack_secret: str,
) -> None:
    supervisor_token, order_id, _product_id = _paid_order(client, session_factory, paystack_secret)
    missing = client.get(
        f"/api/orders/{order_id}/receipt",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert missing.status_code == 404

    db = session_factory()
    try:
        payment_id = db.scalar(select(Payment.id).where(Payment.order_id == order_id))
        assert payment_id is not None
        assert write_payment_receipt(db, payment_id) == "written"
        assert write_payment_receipt(db, payment_id) == "duplicate"
        payment = db.get(Payment, payment_id)
        assert payment is not None
        payment.receipt_sent_at = None
        db.commit()
        assert write_payment_receipt(db, payment_id) == "duplicate"
        db.refresh(payment)
        assert payment.receipt_sent_at is not None
        receipt_count = db.scalar(
            select(func.count()).select_from(Receipt).where(Receipt.payment_id == payment_id)
        )
        assert receipt_count == 1
    finally:
        db.close()

    written = client.get(
        f"/api/orders/{order_id}/receipt",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert written.status_code == 200
    body = written.json()["body"]
    assert "BOX-7A x 2 @ 10.50" in body
    assert "ZAR 21.00" in body

    receiver_token = login(client, "receiver@example.com", "receiver123")
    forbidden = client.get(
        f"/api/orders/{order_id}/receipt",
        headers={"Authorization": f"Bearer {receiver_token}"},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_worker_raises_when_payment_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
) -> None:
    monkeypatch.setattr("warehouse_ledger.worker.SessionLocal", session_factory)
    with pytest.raises(ReceiptNotReady):
        await send_payment_receipt({}, 9_999_999)


@pytest.mark.asyncio
async def test_worker_raises_when_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Session:
        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    def fail(_db: object, _payment_id: int) -> str:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("warehouse_ledger.worker.SessionLocal", lambda: _Session())
    monkeypatch.setattr("warehouse_ledger.worker.write_payment_receipt", fail)
    with pytest.raises(RuntimeError, match="database unavailable"):
        await send_payment_receipt({}, 1)


def test_worker_retries_three_times() -> None:
    assert WorkerSettings.max_tries == 3


@pytest.mark.asyncio
async def test_worker_returns_written_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Session:
        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("warehouse_ledger.worker.SessionLocal", lambda: _Session())
    monkeypatch.setattr(
        "warehouse_ledger.worker.write_payment_receipt",
        lambda _db, _payment_id: "written",
    )
    assert await send_payment_receipt({}, 1) == "written"
