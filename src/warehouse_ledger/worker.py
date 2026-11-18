from __future__ import annotations

from arq.connections import RedisSettings

from warehouse_ledger.config import get_settings
from warehouse_ledger.db import SessionLocal
from warehouse_ledger.services.receipts import ReceiptNotReady, write_payment_receipt


async def send_payment_receipt(ctx: dict[str, object], payment_id: int) -> str:
    """Write one receipt for a payment. ARQ retries when this raises."""
    del ctx
    db = SessionLocal()
    try:
        outcome = write_payment_receipt(db, payment_id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    if outcome == "missing":
        raise ReceiptNotReady(payment_id)
    return outcome


class WorkerSettings:
    functions = [send_payment_receipt]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = 3
    job_timeout = 30
