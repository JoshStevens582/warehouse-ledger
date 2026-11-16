from __future__ import annotations

import secrets

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import login
from warehouse_ledger.models import Order, OrderStatus, Payment, Product


def test_record_test_payment_marks_order_paid(
    client: TestClient,
    session_factory: sessionmaker[Session],
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
            "lines": [{"product_id": product_id, "quantity": 2, "unit_price": "50.00"}],
        },
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]
    reference = f"wh-{order_id}-{secrets.token_hex(6)}"

    db = session_factory()
    try:
        order = db.get(Order, order_id)
        assert order is not None
        order.paystack_reference = reference
        db.commit()
    finally:
        db.close()

    record = client.post(
        f"/api/orders/{order_id}/record-test-payment",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert record.status_code == 200
    assert record.json()["status"] in {"ok", OrderStatus.paid.value}

    order_get = client.get(
        f"/api/orders/{order_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert order_get.json()["status"] == OrderStatus.paid.value

    db = session_factory()
    try:
        order = db.get(Order, order_id)
        assert order is not None
        assert order.status == OrderStatus.paid
        payments = db.scalars(select(Payment).where(Payment.order_id == order_id)).all()
        assert len(payments) == 1
        assert payments[0].paystack_reference == reference
    finally:
        db.close()


def test_record_test_payment_requires_checkout_reference(
    client: TestClient,
    session_factory: sessionmaker[Session],
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
            "lines": [{"product_id": product_id, "quantity": 1, "unit_price": "25.00"}],
        },
    )
    order_id = order_resp.json()["id"]

    record = client.post(
        f"/api/orders/{order_id}/record-test-payment",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert record.status_code == 400
    assert "reference" in record.json()["detail"].lower()


def test_record_test_payment_supervisor_only(client: TestClient) -> None:
    picker_token = login(client, "picker@example.com", "picker123")
    record = client.post(
        "/api/orders/1/record-test-payment",
        headers={"Authorization": f"Bearer {picker_token}"},
    )
    assert record.status_code == 403