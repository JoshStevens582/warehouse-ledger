from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from warehouse_ledger.models import Order, OrderLine, Payment, Receipt
from warehouse_ledger.timeutil import utc_now


class ReceiptNotReady(Exception):
    """The payment row is not visible yet. The worker retries this."""

    def __init__(self, payment_id: int) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} is not ready for a receipt")


def render_receipt(payment: Payment) -> str:
    order = payment.order
    if order is None:
        raise ReceiptNotReady(payment.id)
    lines = [
        f"Receipt for order {order.id}",
        f"Reference {payment.paystack_reference}",
        f"{payment.currency} {payment.amount:.2f}",
    ]
    for line in order.lines:
        sku = line.product.sku if line.product is not None else str(line.product_id)
        lines.append(f"{sku} x {line.quantity} @ {line.unit_price:.2f}")
    return "\n".join(lines)


def write_payment_receipt(db: Session, payment_id: int) -> str:
    """Write one receipt. Returns written, duplicate, or missing."""
    if payment_id <= 0:
        return "missing"
    payment = db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .options(
            selectinload(Payment.order)
            .selectinload(Order.lines)
            .selectinload(OrderLine.product)
        )
    )
    if payment is None:
        return "missing"
    existing = db.scalar(select(Receipt).where(Receipt.payment_id == payment_id))
    if existing is not None:
        if payment.receipt_sent_at is None:
            payment.receipt_sent_at = utc_now()
            db.commit()
        return "duplicate"
    payment.receipt_sent_at = utc_now()
    db.add(
        Receipt(
            payment_id=payment.id,
            order_id=payment.order_id,
            body=render_receipt(payment),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "duplicate"
    return "written"
