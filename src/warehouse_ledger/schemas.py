from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from warehouse_ledger.models import OrderStatus, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    shelf_quantity: int

    model_config = {"from_attributes": True}


class MovementCreate(BaseModel):
    product_id: int
    quantity_delta: int = Field(description="Positive for delivery, negative for pick")
    note: str | None = None
    order_id: int | None = None


class MovementRead(BaseModel):
    id: int
    product_id: int
    quantity_delta: int
    note: str | None
    order_id: int | None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderLineCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class OrderCreate(BaseModel):
    customer_email: EmailStr
    lines: list[OrderLineCreate] = Field(min_length=1)


class OrderLineRead(BaseModel):
    product_id: int
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: int
    customer_email: str
    status: OrderStatus
    currency: str
    total_amount: Decimal
    paystack_reference: str | None
    lines: list[OrderLineRead]

    model_config = {"from_attributes": True}


class CheckoutResponse(BaseModel):
    authorization_url: str
    reference: str


class ReceiptRead(BaseModel):
    id: int
    order_id: int
    payment_id: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentRead(BaseModel):
    id: int
    order_id: int
    paystack_reference: str
    amount: Decimal
    currency: str
    recorded_at: datetime
    receipt_sent_at: datetime | None

    model_config = {"from_attributes": True}
