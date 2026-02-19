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

    # Fetch group for base currency
    group_result = await db.execute(select(Group.base_currency).where(Group.id == group_id))
    base_currency = group_result.scalar_one_or_none() or "SGD"

    # 1. Get Overall Totals (unchanged)
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

    if receipt_count == 0:
        return {
            "period": period.value,
            "total_spending": str(total_spending.quantize(Decimal("0.01"))),
            "receipt_count": 0,
            "spending_by_user": [],
            "base_currency": base_currency,
        }

    # 2. Fetch assignments and payments using shared calculation service
    from app.services.calculation_service import get_receipt_totals
    user_spending, user_paid, user_names_map = await get_receipt_totals(db, group_id, since=since)
    
    # Merge any existing names found during stats usage (though service returns them)
    user_names = user_names_map.copy()

    # 5. Build Result
    all_user_ids = set(user_spending.keys()) | set(user_paid.keys())
    spending_by_user = []
    
    for user_id in all_user_ids:
        spent = user_spending[user_id]
        paid = user_paid[user_id]
        balance = paid - spent
        
        spending_by_user.append({
            "user_id": str(user_id),
            "display_name": user_names.get(user_id, "Unknown"),
            "amount": str(spent.quantize(Decimal("0.01"))),
            "paid": str(paid.quantize(Decimal("0.01"))),
            "balance": str(balance.quantize(Decimal("0.01"))),
        })

    spending_by_user.sort(key=lambda x: Decimal(x["amount"]), reverse=True)

    return {
        "period": period.value,
        "total_spending": str(total_spending.quantize(Decimal("0.01"))),
        "receipt_count": receipt_count,
        "spending_by_user": spending_by_user,
        "base_currency": base_currency,
    }
