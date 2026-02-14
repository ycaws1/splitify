import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, GroupMember, GroupRole
from app.models.user import User


async def create_group(db: AsyncSession, name: str, user: User) -> Group:
    group = Group(name=name, created_by=user.id)
    db.add(group)
    await db.flush()

    member = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.owner)
    db.add(member)
    await db.commit()
    await db.refresh(group)
    return group


async def list_user_groups(db: AsyncSession, user_id: uuid.UUID) -> list[Group]:
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list(result.scalars().all())


async def get_group(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


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
