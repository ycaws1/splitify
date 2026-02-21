import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("receipts.id"), index=True, nullable=False)
    paid_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    receipt: Mapped["Receipt"] = relationship(back_populates="payments")
    payer: Mapped["User"] = relationship(lazy="selectin")

    @property
    def payer_name(self) -> str | None:
        return self.payer.display_name if self.payer else None


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True, nullable=False)
    from_user: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    to_user: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    debtor: Mapped["User"] = relationship(foreign_keys=[from_user], lazy="selectin")
    creditor: Mapped["User"] = relationship(foreign_keys=[to_user], lazy="selectin")
