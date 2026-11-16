from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_ledger.auth import hash_password
from warehouse_ledger.models import Product, User, UserRole


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(Product.id).where(Product.sku == "BOX-7A")) is not None:
        return

    users = [
        ("receiver@example.com", "receiver123", UserRole.receiver),
        ("picker@example.com", "picker123", UserRole.picker),
        ("supervisor@example.com", "supervisor123", UserRole.supervisor),
    ]
    for email, password, role in users:
        if db.scalar(select(User).where(User.email == email)) is None:
            db.add(User(email=email, password_hash=hash_password(password), role=role))
    if db.scalar(select(Product).where(Product.sku == "BOX-7A")) is None:
        db.add(Product(sku="BOX-7A", name="Medium carton"))
    db.commit()
