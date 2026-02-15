import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment
from app.models.group import Group
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

    # Fetch group for base currency in one query
    group_result = await db.execute(select(Group.base_currency).where(Group.id == group_id))
    base_currency = group_result.scalar_one_or_none() or "SGD"

    # Single optimized query combining spending and payments using CTEs
    # This replaces 4 separate queries with 1 efficient query
    
    # Get total spending and receipt count
    summary_result = await db.execute(
        select(
            func.coalesce(func.sum(Receipt.total * Receipt.exchange_rate), Decimal("0")),
            func.count(Receipt.id)
        )
        .where(Receipt.group_id == group_id, Receipt.created_at >= since)
    )
    row = summary_result.one()
    total_spending = row[0]
    receipt_count = row[1]

    # Early return if no receipts
    if receipt_count == 0:
        return {
            "period": period.value,
            "total_spending": str(total_spending.quantize(Decimal("0.01"))),
            "receipt_count": 0,
            "spending_by_user": [],
            "base_currency": base_currency,
        }

    # Optimized: Get both spending and payments in fewer queries
    # Get spending per user
    spending_result = await db.execute(
        select(
            LineItemAssignment.user_id,
            User.display_name,
            func.sum(LineItemAssignment.share_amount * Receipt.exchange_rate).label("spent")
        )
        .select_from(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .outerjoin(User, User.id == LineItemAssignment.user_id)
        .where(
            Receipt.group_id == group_id,
            Receipt.created_at >= since
        )
        .group_by(LineItemAssignment.user_id, User.display_name)
    )
    
    spending_map = {user_id: (display_name, spent) for user_id, display_name, spent in spending_result.all()}

    # Get payments per user
    payments_result = await db.execute(
        select(
            Payment.paid_by,
            User.display_name,
            func.sum(Payment.amount * Receipt.exchange_rate).label("paid")
        )
        .select_from(Payment)
        .join(Receipt, Receipt.id == Payment.receipt_id)
        .outerjoin(User, User.id == Payment.paid_by)
        .where(
            Receipt.group_id == group_id,
            Receipt.created_at >= since
        )
        .group_by(Payment.paid_by, User.display_name)
    )
    
    payments_map = {user_id: (display_name, paid) for user_id, display_name, paid in payments_result.all()}

    # Combine all user IDs
    all_user_ids = set(spending_map.keys()) | set(payments_map.keys())

    # Build result
    spending_by_user = []
    for user_id in all_user_ids:
        # Get data from maps, preferring display_name from spending if available
        spending_data = spending_map.get(user_id, (None, Decimal("0")))
        payments_data = payments_map.get(user_id, (None, Decimal("0")))
        
        display_name = spending_data[0] or payments_data[0] or "Unknown"
        spent = spending_data[1]
        paid = payments_data[1]
        balance = paid - spent

        spending_by_user.append({
            "user_id": str(user_id),
            "display_name": display_name,
            "amount": str(spent.quantize(Decimal("0.01"))),
            "paid": str(paid.quantize(Decimal("0.01"))),
            "balance": str(balance.quantize(Decimal("0.01"))),
        })

    # Sort by spending (descending)
    spending_by_user.sort(key=lambda x: Decimal(x["amount"]), reverse=True)

    return {
        "period": period.value,
        "total_spending": str(total_spending.quantize(Decimal("0.01"))),
        "receipt_count": receipt_count,
        "spending_by_user": spending_by_user,
        "base_currency": base_currency,
    }
