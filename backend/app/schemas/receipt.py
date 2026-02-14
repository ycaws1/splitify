import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ReceiptCreate(BaseModel):
    image_url: str


class LineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    sort_order: int


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    group_id: uuid.UUID
    uploaded_by: uuid.UUID
    image_url: str
    merchant_name: str | None
    receipt_date: date | None
    currency: str
    subtotal: Decimal | None
    tax: Decimal | None
    service_charge: Decimal | None
    total: Decimal | None
    status: str
    version: int
    created_at: datetime
    line_items: list[LineItemResponse] = []


class ReceiptUpdate(BaseModel):
    merchant_name: str | None = None
    receipt_date: date | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    service_charge: Decimal | None = None
    total: Decimal | None = None
    version: int  # required for optimistic locking


class ReceiptListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    merchant_name: str | None
    total: Decimal | None
    status: str
    created_at: datetime
