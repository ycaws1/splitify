import uuid
from decimal import Decimal

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment


from app.utils.currency_utils import compute_shares


async def bulk_assign(
    db: AsyncSession,
    receipt_id: uuid.UUID,
    assignments: list[dict],
    expected_version: int | None = None,
) -> list[LineItemAssignment] | None:
    """
    Replace all assignments for the given receipt.
    Each assignment: {line_item_id, user_ids}
    Splits each line item amount exactly among assigned users (no rounding error).
    Uses optimistic locking on receipt version.
    Returns None if version conflict.
    """
    # Version check
    stmt = update(Receipt).where(Receipt.id == receipt_id)
    if expected_version is not None:
        stmt = stmt.where(Receipt.version == expected_version)
    stmt = stmt.values(version=Receipt.version + 1).returning(Receipt.id)

    result = await db.execute(stmt)
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

        shares = compute_shares(li.amount, a["user_ids"], seed=str(li.id))
        for user_id in a["user_ids"]:
            new_assignments.append(LineItemAssignment(
                line_item_id=a["line_item_id"],
                user_id=user_id,
                share_amount=shares[user_id],
            ))

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
    Recalculates all shares after every change so they always sum exactly to
    the line item amount.
    Returns dict with {assigned: bool, new_version: int, assignments: list} or None if version conflict.
    """
    # Version check and increment
    stmt = update(Receipt).where(Receipt.id == receipt_id)
    if expected_version is not None:
        stmt = stmt.where(Receipt.version == expected_version)
    stmt = stmt.values(version=Receipt.version + 1).returning(Receipt.version)

    result = await db.execute(stmt)
    new_ver = result.scalar_one_or_none()
    if new_ver is None:
        return None  # version conflict or receipt not found

    # Fetch line item amount
    line_item_result = await db.execute(
        select(LineItem).where(LineItem.id == line_item_id)
    )
    line_item = line_item_result.scalar_one_or_none()
    if not line_item:
        await db.rollback()
        return None

    # Fetch all current assignments for this line item
    current_result = await db.execute(
        select(LineItemAssignment).where(
            LineItemAssignment.line_item_id == line_item_id
        )
    )
    current_assignments = list(current_result.scalars().all())
    current_user_ids = {a.user_id for a in current_assignments}

    if user_id in current_user_ids:
        # Remove: delete this assignment
        for a in current_assignments:
            if a.user_id == user_id:
                await db.delete(a)
                break
        remaining = [a for a in current_assignments if a.user_id != user_id]
        assigned = False
    else:
        # Add: create new assignment (share_amount set below)
        new_assignment = LineItemAssignment(
            line_item_id=line_item_id,
            user_id=user_id,
            share_amount=Decimal("0"),  # placeholder, recalculated below
        )
        db.add(new_assignment)
        remaining = current_assignments + [new_assignment]
        assigned = True

    # Recompute shares for all remaining assignments so they sum exactly to amount
    all_user_ids = [a.user_id for a in remaining]
    shares = compute_shares(line_item.amount, all_user_ids, seed=str(line_item_id))
    for a in remaining:
        a.share_amount = shares[a.user_id]

    await db.commit()
    
    # Return the updated assignments for this line item so the frontend doesn't need to refetch
    updated_assignments = [
        {"id": a.id, "line_item_id": a.line_item_id, "user_id": a.user_id, "share_amount": a.share_amount}
        for a in remaining
    ]
    return {"assigned": assigned, "new_version": new_ver, "assignments": updated_assignments}


async def get_assignments(db: AsyncSession, receipt_id: uuid.UUID) -> list[LineItemAssignment]:
    result = await db.execute(
        select(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .where(LineItem.receipt_id == receipt_id)
    )
    return list(result.scalars().all())


from app.models.group import GroupMember

async def assign_all_to_all(
    db: AsyncSession,
    receipt_id: uuid.UUID,
    expected_version: int | None = None,
) -> list[LineItemAssignment] | None:
    """
    Assign ALL line items in the receipt to ALL group members.
    Splits amounts evenly using compute_shares.
    """
    # 1. Update Receipt Version (Optimistic Locking)
    stmt = update(Receipt).where(Receipt.id == receipt_id)
    if expected_version is not None:
        stmt = stmt.where(Receipt.version == expected_version)
    stmt = stmt.values(version=Receipt.version + 1).returning(Receipt.id, Receipt.group_id)
    
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        return None
    group_id = row.group_id

    # 2. Fetch all line items
    items_result = await db.execute(
        select(LineItem).where(LineItem.receipt_id == receipt_id)
    )
    line_items = items_result.scalars().all()
    if not line_items:
        await db.commit()
        return []

    # 3. Fetch all group members
    members_result = await db.execute(
        select(GroupMember.user_id).where(GroupMember.group_id == group_id)
    )
    member_ids = list(members_result.scalars().all())
    if not member_ids:
        await db.commit()
        return []

    # 4. Delete existing assignments for these items
    line_item_ids = [li.id for li in line_items]
    await db.execute(
        delete(LineItemAssignment).where(
            LineItemAssignment.line_item_id.in_(line_item_ids)
        )
    )

    # 5. Create new assignments
    new_assignments = []
    for li in line_items:
        shares = compute_shares(li.amount, member_ids, seed=str(li.id))
        for uid, share in shares.items():
            new_assignments.append(LineItemAssignment(
                line_item_id=li.id,
                user_id=uid,
                share_amount=share,
            ))
            
    if new_assignments:
        db.add_all(new_assignments)

    await db.commit()
    return new_assignments
