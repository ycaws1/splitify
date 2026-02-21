import uuid
import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Date, DateTime, Integer, Numeric, ForeignKey,
    Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReceiptStatus(str, enum.Enum):
    processing = "processing"
    extracted = "extracted"
    confirmed = "confirmed"
    failed = "failed"


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("1"))
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    service_charge: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[ReceiptStatus] = mapped_column(
        SAEnum(ReceiptStatus), nullable=False, default=ReceiptStatus.processing
    )
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    line_items: Mapped[list["LineItem"]] = relationship(back_populates="receipt", lazy="selectin", order_by="LineItem.sort_order", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(cascade="all, delete-orphan", lazy="noload")
    uploader: Mapped["User"] = relationship(lazy="selectin")


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("receipts.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    receipt: Mapped["Receipt"] = relationship(back_populates="line_items")
    assignments: Mapped[list["LineItemAssignment"]] = relationship(back_populates="line_item", lazy="selectin", cascade="all, delete-orphan")


class LineItemAssignment(Base):
    __tablename__ = "line_item_assignments"
    __table_args__ = (UniqueConstraint("line_item_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("line_items.id"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    line_item: Mapped["LineItem"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(lazy="selectin")
