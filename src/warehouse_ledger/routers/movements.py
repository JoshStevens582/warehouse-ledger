from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_ledger.auth import get_current_user, require_roles
from warehouse_ledger.db import get_db
from warehouse_ledger.models import Product, StockMovement, User, UserRole
from warehouse_ledger.schemas import MovementCreate, MovementRead
from warehouse_ledger.services.stock import shelf_quantity

router = APIRouter(prefix="/movements", tags=["movements"])


@router.get("/recent", response_model=list[MovementRead])
def recent_movements(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[MovementRead]:
    rows = db.scalars(
        select(StockMovement).order_by(StockMovement.created_at.desc()).limit(15)
    )
    return [MovementRead.model_validate(r) for r in rows]


@router.get("", response_model=list[MovementRead])
def list_movements(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.supervisor))],
) -> list[MovementRead]:
    rows = db.scalars(select(StockMovement).order_by(StockMovement.created_at.desc()).limit(200))
    return [MovementRead.model_validate(r) for r in rows]


@router.post("", response_model=MovementRead, status_code=201)
def record_movement(
    payload: MovementCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.receiver, UserRole.picker))],
) -> MovementRead:
    if payload.quantity_delta == 0:
        raise HTTPException(status_code=400, detail="quantity_delta cannot be zero")
    if user.role == UserRole.receiver and payload.quantity_delta < 0:
        raise HTTPException(status_code=403, detail="Receiver can only add deliveries")
    if user.role == UserRole.picker and payload.quantity_delta > 0:
        raise HTTPException(status_code=403, detail="Picker can only record picks")
    if user.role == UserRole.picker and payload.order_id is None:
        raise HTTPException(status_code=400, detail="Pick requires order_id")
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.quantity_delta < 0:
        on_hand = shelf_quantity(db, payload.product_id)
        if on_hand + payload.quantity_delta < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough on shelf (have {on_hand}, pick {abs(payload.quantity_delta)})",
            )
    movement = StockMovement(
        product_id=payload.product_id,
        quantity_delta=payload.quantity_delta,
        note=payload.note,
        order_id=payload.order_id,
        created_by=user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return MovementRead.model_validate(movement)
