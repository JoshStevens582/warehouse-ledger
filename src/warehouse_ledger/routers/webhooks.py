from __future__ import annotations

import json
from typing import Annotated, Any

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from warehouse_ledger.config import get_settings
from warehouse_ledger.db import get_db
from warehouse_ledger.models import Payment, PaystackWebhookEvent
from warehouse_ledger.paystack import verify_webhook_signature
from warehouse_ledger.services.paystack_events import apply_charge_success

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_paystack_signature: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    body = await request.body()
    if not verify_webhook_signature(body, x_paystack_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad signature")
    payload: dict[str, Any] = json.loads(body)
    event_id = int(payload["data"].get("id") or payload.get("id") or 0)
    if event_id == 0:
        raise HTTPException(status_code=400, detail="Missing event id")
    event_type = str(payload.get("event", ""))
    reference = None
    data = payload.get("data") or {}
    if isinstance(data, dict):
        reference = data.get("reference")

    try:
        db.add(
            PaystackWebhookEvent(
                event_id=event_id,
                event_type=event_type,
                reference=reference,
            )
        )
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}

    if event_type != "charge.success" or not reference:
        db.commit()
        return {"status": "ignored"}

    amount_minor = int(data.get("amount", 0)) if isinstance(data, dict) else 0
    currency = str(data.get("currency", "ZAR")) if isinstance(data, dict) else "ZAR"
    pay_status = apply_charge_success(
        db,
        reference=str(reference),
        amount_minor=amount_minor,
        currency=currency,
    )
    if pay_status == "ok":
        try:
            payment = db.scalar(
                select(Payment).where(Payment.paystack_reference == reference)
            )
            if payment is not None:
                redis = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
                await redis.enqueue_job("send_payment_receipt", payment.id)
                await redis.close()
        except Exception:
            pass
    return {"status": pay_status}
