import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User


async def create_receipt(
    db: AsyncSession, group_id: uuid.UUID, image_url: str, user: User
) -> Receipt:
    receipt = Receipt(
        group_id=group_id,
        uploaded_by=user.id,
        image_url=image_url,
        status=ReceiptStatus.processing,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return receipt


async def list_receipts(db: AsyncSession, group_id: uuid.UUID) -> list[Receipt]:
    result = await db.execute(
        select(Receipt)
        .where(Receipt.group_id == group_id)
        .order_by(Receipt.created_at.desc())
    )
    return list(result.scalars().all())


async def get_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> Receipt | None:
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
    return result.scalar_one_or_none()


async def update_receipt(
    db: AsyncSession, receipt_id: uuid.UUID, data: dict, expected_version: int
) -> Receipt | None:
    """Update receipt with optimistic locking. Returns None if version conflict."""
    result = await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.version == expected_version)
        .values(**data, version=expected_version + 1)
        .returning(Receipt)
    )
    await db.commit()
    row = result.scalar_one_or_none()
    return row
