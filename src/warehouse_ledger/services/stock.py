from sqlalchemy import func, select
from sqlalchemy.orm import Session

from warehouse_ledger.models import Product, StockMovement


def shelf_quantity(db: Session, product_id: int) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity_delta), 0)).where(
            StockMovement.product_id == product_id
        )
    )
    return int(total or 0)


def list_products_with_totals(db: Session) -> list[tuple[Product, int]]:
    rows = db.scalars(select(Product).order_by(Product.sku)).all()
    return [(p, shelf_quantity(db, p.id)) for p in rows]
