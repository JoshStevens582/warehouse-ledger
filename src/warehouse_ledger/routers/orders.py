from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from warehouse_ledger.auth import get_current_user, require_roles
from warehouse_ledger.config import get_settings
from warehouse_ledger.db import get_db
from warehouse_ledger.models import (
    Order,
    OrderStatus,
    Payment,
    PaystackWebhookEvent,
    User,
    UserRole,
)
from warehouse_ledger.paystack import initialize_transaction
from warehouse_ledger.schemas import CheckoutResponse, OrderCreate, OrderRead, PaymentRead
from warehouse_ledger.services.orders import create_order
from warehouse_ledger.services.paystack_events import apply_charge_success, new_event_id

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=201)
def post_order(
    payload: OrderCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.supervisor, UserRole.picker))],
) -> OrderRead:
    try:
        order = create_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OrderRead.model_validate(order)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> OrderRead:
    order = db.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.lines)))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderRead.model_validate(order)


@router.post("/{order_id}/checkout", response_model=CheckoutResponse)
async def start_checkout(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CheckoutResponse:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in {OrderStatus.draft, OrderStatus.pending_payment}:
        raise HTTPException(status_code=400, detail="Order is not open for payment")
    reference = order.paystack_reference or f"wh-{order_id}-{secrets.token_hex(6)}"
    order.paystack_reference = reference
    order.status = OrderStatus.pending_payment
    db.commit()
    settings = get_settings()
    base = settings.checkout_callback_url.rstrip("/")
    callback_url = f"{base}/?warehouse_order={order_id}"
    try:
        data = await initialize_transaction(
            email=order.customer_email,
            amount=order.total_amount,
            reference=reference,
            currency=order.currency,
            callback_url=callback_url,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CheckoutResponse(authorization_url=data["authorization_url"], reference=reference)


@router.post("/{order_id}/record-test-payment")
def record_test_payment(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.supervisor))],
) -> dict[str, str]:
    """Local dev: pretend Paystack webhook arrived (use after Paystack Success)."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.paystack_reference:
        raise HTTPException(
            status_code=400,
            detail="Run Pay with Paystack first so this order has a reference",
        )
    event_id = new_event_id()
    db.add(
        PaystackWebhookEvent(
            event_id=event_id,
            event_type="charge.success",
            reference=order.paystack_reference,
        )
    )
    db.commit()
    amount_minor = int(order.total_amount * 100)
    status = apply_charge_success(
        db,
        reference=order.paystack_reference,
        amount_minor=amount_minor,
        currency=order.currency,
    )
    return {"status": status}


@router.get("/{order_id}/payments", response_model=list[PaymentRead])
def list_payments(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.supervisor))],
) -> list[PaymentRead]:
    rows = db.scalars(select(Payment).where(Payment.order_id == order_id))
    return [PaymentRead.model_validate(p) for p in rows]
