from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import login
from warehouse_ledger.models import Product


def test_row_rule_and_roles(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    db = session_factory()
    try:
        product_id = db.scalar(select(Product.id).where(Product.sku == "BOX-7A"))
        assert product_id is not None
    finally:
        db.close()

    receiver_token = login(client, "receiver@example.com", "receiver123")
    picker_token = login(client, "picker@example.com", "picker123")
    supervisor_token = login(client, "supervisor@example.com", "supervisor123")

    delivery = client.post(
        "/api/movements",
        headers={"Authorization": f"Bearer {receiver_token}"},
        json={"product_id": product_id, "quantity_delta": 10, "note": "delivery"},
    )
    assert delivery.status_code == 201

    blocked = client.post(
        "/api/movements",
        headers={"Authorization": f"Bearer {receiver_token}"},
        json={"product_id": product_id, "quantity_delta": -2},
    )
    assert blocked.status_code == 403

    order = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {supervisor_token}"},
        json={
            "customer_email": "buyer@example.com",
            "lines": [{"product_id": product_id, "quantity": 2, "unit_price": "50.00"}],
        },
    )
    assert order.status_code == 201
    order_id = order.json()["id"]

    pick = client.post(
        "/api/movements",
        headers={"Authorization": f"Bearer {picker_token}"},
        json={
            "product_id": product_id,
            "quantity_delta": -2,
            "order_id": order_id,
        },
    )
    assert pick.status_code == 201

    products = client.get(
        "/api/products",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert products.status_code == 200
    row = next(p for p in products.json() if p["id"] == product_id)
    assert row["shelf_quantity"] == 8
