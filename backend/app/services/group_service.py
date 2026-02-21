import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.group import Group, GroupMember, GroupRole
from app.models.user import User


async def create_group(db: AsyncSession, name: str, user: User, base_currency: str = "SGD") -> Group:
    group = Group(name=name, created_by=user.id, base_currency=base_currency)
    db.add(group)
    await db.flush()

    member = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.owner)
    db.add(member)
    await db.commit()
    await db.refresh(group)
    return group


async def list_user_groups(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(
        select(Group.id, Group.name, Group.base_currency, Group.created_at)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return result.all()


async def get_group(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(
        select(Group)
        .where(Group.id == group_id)
        .options(joinedload(Group.members).joinedload(GroupMember.user))
    )
    return result.unique().scalar_one_or_none()


async def update_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: str | None = None,
    base_currency: str | None = None,
) -> Group | None:
    group = await db.get(Group, group_id)
    if not group:
        return None
    if name is not None:
        group.name = name.strip()
    if base_currency is not None:
        group.base_currency = base_currency.upper()
    await db.commit()
    await db.refresh(group)
    return group


async def delete_group(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.role == GroupRole.owner,
        )
    )
    if not result.scalar_one_or_none():
        raise ValueError("Only the group owner can delete this group")

    group = await db.get(Group, group_id)
    if not group:
        raise ValueError("Group not found")

    from app.services.receipt_service import delete_all_receipts
    from app.services.payment_service import clear_group_settlements
    from sqlalchemy import delete

    # Cascade clear heavy components
    await delete_all_receipts(db, group_id)
    await clear_group_settlements(db, group_id)

    # Bulk delete members then group to avoid ORM N+1 deletion loops
    await db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.commit()


async def join_group_by_code(db: AsyncSession, invite_code: str, user: User) -> Group:
    result = await db.execute(select(Group).where(Group.invite_code == invite_code))
    group = result.scalar_one_or_none()
    if not group:
        raise ValueError("Invalid invite code")

    existing = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return group  # already a member

    member = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.member)
    db.add(member)
    await db.commit()
    await db.refresh(group)
    return group


async def reset_group_data(db: AsyncSession, group_id: uuid.UUID) -> dict:
    from app.models.receipt import Receipt, LineItem, LineItemAssignment
    from app.models.payment import Payment, Settlement
    from sqlalchemy import delete

    # Get receipt IDs for this group first
    receipt_ids_result = await db.execute(
        select(Receipt.id).where(Receipt.group_id == group_id)
    )
    receipt_ids = [row[0] for row in receipt_ids_result.all()]
    count = len(receipt_ids)

    if receipt_ids:
        # Delete dependents explicitly before receipts to satisfy FK constraints.
        # (lazy="noload" on relationships means ORM cascade won't fire automatically.)
        line_item_ids_result = await db.execute(
            select(LineItem.id).where(LineItem.receipt_id.in_(receipt_ids))
        )
        line_item_ids = [row[0] for row in line_item_ids_result.all()]

        if line_item_ids:
            await db.execute(delete(LineItemAssignment).where(LineItemAssignment.line_item_id.in_(line_item_ids)))

        await db.execute(delete(Payment).where(Payment.receipt_id.in_(receipt_ids)))
        await db.execute(delete(LineItem).where(LineItem.receipt_id.in_(receipt_ids)))
        await db.execute(delete(Receipt).where(Receipt.id.in_(receipt_ids)))

    await db.execute(delete(Settlement).where(Settlement.group_id == group_id))

    await db.commit()

    return {
        "receipts_deleted": count,
        "settlements_deleted": 0,  # not tracking separately
    }
