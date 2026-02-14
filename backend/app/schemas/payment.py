import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    paid_by: uuid.UUID
    amount: Decimal


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    receipt_id: uuid.UUID
    paid_by: uuid.UUID
    amount: Decimal
    created_at: datetime


class BalanceEntry(BaseModel):
    from_user_id: uuid.UUID
    from_user_name: str
    to_user_id: uuid.UUID
    to_user_name: str
    amount: Decimal


class BalancesResponse(BaseModel):
    balances: list[BalanceEntry]


class SettleRequest(BaseModel):
    from_user: uuid.UUID
    to_user: uuid.UUID
    amount: Decimal
