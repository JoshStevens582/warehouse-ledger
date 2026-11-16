from __future__ import annotations

import secrets
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_ledger.models import Order, OrderStatus, Payment


def apply_charge_success(
    db: Session,
    *,
    reference: str,
    amount_minor: int,
    currency: str,
) -> str:
    """Mark order paid from charge.success. PaystackWebhookEvent row should exist."""
    order = db.scalar(select(Order).where(Order.paystack_reference == reference))
    if order is None:
        return "no_order"

    if order.status == OrderStatus.paid:
        return "already_paid"

    existing = db.scalar(select(Payment).where(Payment.paystack_reference == reference))
    if existing is not None:
        return "already_paid"

    amount = Decimal(amount_minor) / Decimal(100)
    payment = Payment(
        order_id=order.id,
        paystack_reference=reference,
        amount=amount,
        currency=currency or order.currency,
    )
    order.status = OrderStatus.paid
    db.add(payment)
    db.commit()
    return "ok"


def new_event_id() -> int:
    return secrets.randbelow(2_000_000_000) + 1