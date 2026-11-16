from __future__ import annotations

import os

os.environ["WAREHOUSE_LEDGER_TESTING"] = "1"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from warehouse_ledger.db import get_db
from warehouse_ledger.main import app
from warehouse_ledger.seed import seed_demo_data

_TEST_DB_DEFAULT = "postgresql+psycopg://ledger:ledger@localhost:5432/warehouse_ledger_test"
_DEV_DB_DEFAULT = "postgresql+psycopg://ledger:ledger@localhost:5432/warehouse_ledger"


def _pick_test_database_url() -> str:
    """Never TRUNCATE warehouse_ledger unless explicitly opted in (play data lives there)."""
    order: list[str] = []
    if from_env := os.environ.get("TEST_DATABASE_URL"):
        order.append(from_env)
    order.append(_TEST_DB_DEFAULT)
    if os.environ.get("WAREHOUSE_LEDGER_ALLOW_TEST_TRUNCATE_DEV") == "1":
        if dev := os.environ.get("DATABASE_URL"):
            order.append(dev)
        order.append(_DEV_DB_DEFAULT)
    seen: set[str] = set()
    for url in order:
        if url in seen:
            continue
        seen.add(url)
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            continue
        return url
    pytest.skip(
        "Create database warehouse_ledger_test and run: uv run alembic upgrade head "
        "(see .env.example). Tests must not wipe warehouse_ledger."
    )


@pytest.fixture(scope="session")
def database_url() -> str:
    return _pick_test_database_url()


@pytest.fixture()
def session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def reset_warehouse_tables(session_factory: sessionmaker[Session]) -> None:
    db = session_factory()
    try:
        db.execute(text("SET lock_timeout = '5s'"))
        db.execute(
            text(
                "TRUNCATE stock_movements, order_lines, payments, "
                "paystack_webhook_events, orders, products, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def client(
    reset_warehouse_tables: None,
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    db = session_factory()
    try:
        seed_demo_data(db)
    finally:
        db.close()

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    payload = response.json()
    token = payload["access_token"]
    assert isinstance(token, str)
    return token
