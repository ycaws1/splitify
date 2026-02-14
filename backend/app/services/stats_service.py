import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.user import User


class Period(str, Enum):
    day = "1d"
    month = "1mo"
    year = "1yr"


def get_period_start(period: Period) -> datetime:
    now = datetime.now(timezone.utc)
    if period == Period.day:
        return now - timedelta(days=1)
    elif period == Period.month:
        return now - timedelta(days=30)
    else:
        return now - timedelta(days=365)


async def get_group_stats(db: AsyncSession, group_id: uuid.UUID, period: Period) -> dict:
    since = get_period_start(period)

    # Total spending
    total_result = await db.execute(
        select(func.sum(Receipt.total))
        .where(Receipt.group_id == group_id, Receipt.created_at >= since)
    )
    total_spending = total_result.scalar() or Decimal("0")

    # Receipt count
    count_result = await db.execute(
        select(func.count(Receipt.id))
        .where(Receipt.group_id == group_id, Receipt.created_at >= since)
    )
    receipt_count = count_result.scalar() or 0

    # Spending per user
    receipts_result = await db.execute(
        select(Receipt.id).where(
            Receipt.group_id == group_id, Receipt.created_at >= since
        )
    )
    receipt_ids = [r for r in receipts_result.scalars().all()]

    per_user = defaultdict(Decimal)
    if receipt_ids:
        assignments_result = await db.execute(
            select(LineItemAssignment.user_id, func.sum(LineItemAssignment.share_amount))
            .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
            .where(LineItem.receipt_id.in_(receipt_ids))
            .group_by(LineItemAssignment.user_id)
        )
        for user_id, amount in assignments_result.all():
            per_user[user_id] = amount

    # Fetch user names
    user_ids = list(per_user.keys())
    users_map = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u.display_name for u in users_result.scalars().all()}

    spending_by_user = [
        {"user_id": str(uid), "display_name": users_map.get(uid, "Unknown"), "amount": str(amt)}
        for uid, amt in per_user.items()
    ]

    return {
        "period": period.value,
        "total_spending": str(total_spending),
        "receipt_count": receipt_count,
        "spending_by_user": spending_by_user,
    }
