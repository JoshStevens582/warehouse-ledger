from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import login


def test_checkout_supervisor_only(client: TestClient) -> None:
    picker_token = login(client, "picker@example.com", "picker123")
    checkout = client.post(
        "/api/orders/1/checkout",
        headers={"Authorization": f"Bearer {picker_token}"},
    )
    assert checkout.status_code == 403