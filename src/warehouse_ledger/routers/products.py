from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from warehouse_ledger.auth import get_current_user, require_roles
from warehouse_ledger.db import get_db
from warehouse_ledger.models import Product, User, UserRole
from warehouse_ledger.schemas import ProductCreate, ProductRead
from warehouse_ledger.services.stock import list_products_with_totals

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
def list_products(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[ProductRead]:
    return [
        ProductRead(id=p.id, sku=p.sku, name=p.name, shelf_quantity=qty)
        for p, qty in list_products_with_totals(db)
    ]


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.supervisor))],
) -> ProductRead:
    product = Product(sku=payload.sku, name=payload.name)
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductRead(id=product.id, sku=product.sku, name=product.name, shelf_quantity=0)
