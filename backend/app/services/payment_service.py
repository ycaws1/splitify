import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, Settlement


async def get_receipt_payments(db: AsyncSession, receipt_id: uuid.UUID) -> list[dict]:
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(
        select(Payment, User.display_name)
        .join(User, User.id == Payment.paid_by)
        .where(Payment.receipt_id == receipt_id)
        .order_by(Payment.created_at)
    )
    return [
        {
            "id": p.id, "receipt_id": p.receipt_id, "paid_by": p.paid_by,
            "payer_name": name, "amount": p.amount, "created_at": p.created_at,
        }
        for p, name in result.all()
    ]


async def _get_receipt_total_and_paid(db: AsyncSession, receipt_id: uuid.UUID, exclude_payment_id: uuid.UUID | None = None) -> tuple[Decimal, Decimal]:
    from sqlalchemy import select, func
    from app.models.receipt import Receipt

    result = await db.execute(select(Receipt.total).where(Receipt.id == receipt_id))
    receipt_total = result.scalar_one_or_none() or Decimal("0")

    query = select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(Payment.receipt_id == receipt_id)
    if exclude_payment_id:
        query = query.where(Payment.id != exclude_payment_id)
    result = await db.execute(query)
    total_paid = result.scalar_one()

    return receipt_total, total_paid


async def record_payment(
    db: AsyncSession, receipt_id: uuid.UUID, paid_by: uuid.UUID, amount: Decimal
) -> Payment:
    receipt_total, total_paid = await _get_receipt_total_and_paid(db, receipt_id)
    if total_paid + amount > receipt_total:
        remaining = receipt_total - total_paid
        raise ValueError(f"Payment of {amount} exceeds remaining amount of {remaining}")

    payment = Payment(receipt_id=receipt_id, paid_by=paid_by, amount=amount)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def update_payment(
    db: AsyncSession, payment_id: uuid.UUID, paid_by: uuid.UUID, amount: Decimal
) -> Payment | None:
    from sqlalchemy import select
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        return None

    receipt_total, total_paid = await _get_receipt_total_and_paid(db, payment.receipt_id, exclude_payment_id=payment_id)
    if total_paid + amount > receipt_total:
        remaining = receipt_total - total_paid
        raise ValueError(f"Payment of {amount} exceeds remaining amount of {remaining}")

    payment.paid_by = paid_by
    payment.amount = amount
    await db.commit()
    await db.refresh(payment)
    return payment


async def delete_payment(db: AsyncSession, payment_id: uuid.UUID) -> bool:
    from sqlalchemy import select
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        return False
    await db.delete(payment)
    await db.commit()
    return True


async def clear_group_settlements(db: AsyncSession, group_id: uuid.UUID) -> int:
    from sqlalchemy import select, delete
    result = await db.execute(
        delete(Settlement).where(Settlement.group_id == group_id)
    )
    await db.commit()
    return result.rowcount


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
