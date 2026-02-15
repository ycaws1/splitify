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
            new_assignments.append(assignment)

    # Bulk insert all assignments in one operation
    if new_assignments:
        db.add_all(new_assignments)

    await db.commit()
    return new_assignments


async def toggle_assignment(
    db: AsyncSession,
    receipt_id: uuid.UUID,
    line_item_id: uuid.UUID,
    user_id: uuid.UUID,
    expected_version: int | None,
) -> dict | None:
    """
    Toggle a single assignment on/off efficiently.
    Returns dict with {assigned: bool, new_version: int} or None if version conflict.
    """
    # Version check and increment
    stmt = update(Receipt).where(Receipt.id == receipt_id)
    if expected_version is not None:
        stmt = stmt.where(Receipt.version == expected_version)
    
    # Increment version (blindly or conditionally)
    stmt = stmt.values(version=Receipt.version + 1).returning(Receipt.version)
    
    result = await db.execute(stmt)
    new_ver = result.scalar_one_or_none()
    
    if new_ver is None:
        return None  # version conflict or receipt not found

    # Check if assignment exists
    existing = await db.execute(
        select(LineItemAssignment).where(
            LineItemAssignment.line_item_id == line_item_id,
            LineItemAssignment.user_id == user_id,
        )
    )
    assignment = existing.scalar_one_or_none()

    if assignment:
        # Remove assignment
        await db.delete(assignment)
        await db.commit()
        return {"assigned": False, "new_version": new_ver}
    else:
        # Add assignment - need to calculate share amount
        line_item_result = await db.execute(
            select(LineItem).where(LineItem.id == line_item_id)
        )
        line_item = line_item_result.scalar_one_or_none()
        if not line_item:
            await db.rollback()
            return None

        # Count existing assignments to calculate new share
        count_result = await db.execute(
            select(LineItemAssignment).where(
                LineItemAssignment.line_item_id == line_item_id
            )
        )
        existing_assignments = list(count_result.scalars().all())
        num_users = len(existing_assignments) + 1  # +1 for the new user
        share = (line_item.amount / Decimal(num_users)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Update existing assignments with new share
        for existing_assignment in existing_assignments:
            existing_assignment.share_amount = share

        # Create new assignment
        new_assignment = LineItemAssignment(
            line_item_id=line_item_id,
            user_id=user_id,
            share_amount=share,
        )
        db.add(new_assignment)
        await db.commit()
        return {"assigned": True, "new_version": new_ver}


async def get_assignments(db: AsyncSession, receipt_id: uuid.UUID) -> list[LineItemAssignment]:
    result = await db.execute(
        select(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .where(LineItem.receipt_id == receipt_id)
    )
    return list(result.scalars().all())
