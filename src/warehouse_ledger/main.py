import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from warehouse_ledger.config import get_settings
from warehouse_ledger.db import SessionLocal, get_db
from warehouse_ledger.models import StockMovement
from warehouse_ledger.routers import auth, movements, orders, products, webhooks
from warehouse_ledger.seed import seed_demo_data


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if os.environ.get("WAREHOUSE_LEDGER_TESTING") != "1":
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()
    yield


app = FastAPI(title="Warehouse Ledger", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(movements.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")


@app.get("/api/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str | int]:
    raw = get_settings().database_url.replace("postgresql+psycopg", "postgresql")
    parsed = urlparse(raw)
    movement_rows = db.scalar(select(func.count()).select_from(StockMovement)) or 0
    return {
        "status": "ok",
        "database_host": parsed.hostname or "",
        "database_port": parsed.port or 5432,
        "database_name": (parsed.path or "").lstrip("/"),
        "stock_movement_rows": movement_rows,
    }