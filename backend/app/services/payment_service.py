import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, Settlement


async def record_payment(
    db: AsyncSession, receipt_id: uuid.UUID, paid_by: uuid.UUID, amount: Decimal
) -> Payment:
    payment = Payment(receipt_id=receipt_id, paid_by=paid_by, amount=amount)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def settle_debt(
    db: AsyncSession, group_id: uuid.UUID, from_user: uuid.UUID, to_user: uuid.UUID, amount: Decimal
) -> Settlement:
    settlement = Settlement(
        group_id=group_id,
        from_user=from_user,
        to_user=to_user,
        amount=amount,
        is_settled=True,
        settled_at=datetime.now(timezone.utc),
    )
    db.add(settlement)
    await db.commit()
    await db.refresh(settlement)
    return settlement
