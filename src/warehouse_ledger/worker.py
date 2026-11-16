from __future__ import annotations

import logging
from datetime import UTC, datetime

from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_ledger.config import get_settings
from warehouse_ledger.db import SessionLocal
from warehouse_ledger.models import Payment

logger = logging.getLogger(__name__)


async def send_payment_receipt(ctx: dict[str, object], payment_id: int) -> None:
    del ctx
    db: Session = SessionLocal()
    try:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id))
        if payment is None or payment.receipt_sent_at is not None:
            return
        logger.info(
            "Receipt queued for order %s ref %s amount %s %s",
            payment.order_id,
            payment.paystack_reference,
            payment.amount,
            payment.currency,
        )
        payment.receipt_sent_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


class WorkerSettings:
    functions = [send_payment_receipt]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
