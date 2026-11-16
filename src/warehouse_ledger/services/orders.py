from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from warehouse_ledger.models import Order, OrderLine, OrderStatus, Product
from warehouse_ledger.schemas import OrderCreate


def create_order(db: Session, payload: OrderCreate) -> Order:
    order = Order(
        customer_email=payload.customer_email,
        status=OrderStatus.pending_payment,
        total_amount=Decimal("0"),
    )
    db.add(order)
    db.flush()
    total = Decimal("0")
    for line in payload.lines:
        product = db.get(Product, line.product_id)
        if product is None:
            raise ValueError(f"Unknown product {line.product_id}")
        db.add(
            OrderLine(
                order_id=order.id,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
        )
        total += line.unit_price * line.quantity
    order.total_amount = total
    db.commit()
    return db.scalars(
        select(Order).where(Order.id == order.id).options(selectinload(Order.lines))
    ).one()
