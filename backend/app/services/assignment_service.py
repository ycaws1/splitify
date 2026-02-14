import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment


async def bulk_assign(
    db: AsyncSession,
    receipt_id: uuid.UUID,
    assignments: list[dict],
    expected_version: int,
) -> list[LineItemAssignment] | None:
    """
    Replace all assignments for the given receipt.
    Each assignment: {line_item_id, user_ids}
    Splits each line item amount equally among assigned users.
    Uses optimistic locking on receipt version.
    Returns None if version conflict.
    """
    # Version check
    result = await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.version == expected_version)
        .values(version=expected_version + 1)
        .returning(Receipt.id)
    )
    if not result.scalar_one_or_none():
        return None  # version conflict

    # Delete existing assignments for this receipt's line items
    line_item_ids = [a["line_item_id"] for a in assignments]
    if line_item_ids:
        await db.execute(
            delete(LineItemAssignment).where(
                LineItemAssignment.line_item_id.in_(line_item_ids)
            )
        )

    # Fetch line items to get amounts
    result = await db.execute(
        select(LineItem).where(LineItem.receipt_id == receipt_id)
    )
    line_items_map = {li.id: li for li in result.scalars().all()}

    new_assignments = []
    for a in assignments:
        li = line_items_map.get(a["line_item_id"])
        if not li or not a["user_ids"]:
            continue

        num_users = len(a["user_ids"])
        share = (li.amount / Decimal(num_users)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        for user_id in a["user_ids"]:
            assignment = LineItemAssignment(
                line_item_id=a["line_item_id"],
                user_id=user_id,
                share_amount=share,
            )
            db.add(assignment)
            new_assignments.append(assignment)

    await db.commit()
    return new_assignments


async def get_assignments(db: AsyncSession, receipt_id: uuid.UUID) -> list[LineItemAssignment]:
    result = await db.execute(
        select(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .where(LineItem.receipt_id == receipt_id)
    )
    return list(result.scalars().all())
