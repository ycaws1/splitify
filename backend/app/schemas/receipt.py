import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ReceiptCreate(BaseModel):
    image_url: str
    currency: str | None = None


class LineItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    amount: Decimal


class LineItemInput(LineItemCreate):
    pass


class LineItemUpdate(BaseModel):
    description: str | None = None
    quantity: Decimal | None = None
    amount: Decimal | None = None


class ManualReceiptCreate(BaseModel):
    merchant_name: str
    currency: str = "SGD"
    exchange_rate: Decimal = Decimal("1")
    receipt_date: date | None = None
    tax: Decimal | None = None
    service_charge: Decimal | None = None
    items: list[LineItemInput]


class LineItemAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_item_id: uuid.UUID
    user_id: uuid.UUID
    share_amount: Decimal


class LineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    sort_order: int
    assignments: list[LineItemAssignmentResponse] = []


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    group_id: uuid.UUID
    uploaded_by: uuid.UUID
    image_url: str
    merchant_name: str | None
    receipt_date: date | None
    currency: str
    exchange_rate: Decimal
    subtotal: Decimal | None
    tax: Decimal | None
    service_charge: Decimal | None
    total: Decimal | None
    status: str
    version: int
    created_at: datetime
    raw_llm_response: dict | None = None
    line_items: list[LineItemResponse] = []


class ReceiptUpdate(BaseModel):
    merchant_name: str | None = None
    receipt_date: date | None = None
    currency: str | None = None
    exchange_rate: Decimal | None = None
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
    currency: str
    exchange_rate: Decimal
    status: str
    created_at: datetime
