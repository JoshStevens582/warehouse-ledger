from __future__ import annotations

import asyncio
import logging

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_ledger.config import get_settings
from warehouse_ledger.models import Payment

logger = logging.getLogger(__name__)


async def enqueue_payment_receipt(payment_id: int) -> None:
    """Queue the receipt job. A Redis outage does not undo the payment."""
    if payment_id <= 0:
        return
    try:
        redis = await asyncio.wait_for(
            create_pool(RedisSettings.from_dsn(get_settings().redis_url)),
            timeout=2,
        )
    except Exception as exc:
        logger.warning(
            "Receipt job was not queued for payment %s (%s)",
            payment_id,
            type(exc).__name__,
        )
        return
    try:
        await redis.enqueue_job("send_payment_receipt", payment_id)
    except Exception as exc:
        logger.warning(
            "Receipt job was not queued for payment %s (%s)",
            payment_id,
            type(exc).__name__,
        )
    finally:
        await redis.close()


async def queue_receipt_for_reference(db: Session, reference: str) -> None:
    payment = db.scalar(select(Payment).where(Payment.paystack_reference == reference))
    if payment is None or payment.receipt_sent_at is not None:
        return
    await enqueue_payment_receipt(payment.id)
