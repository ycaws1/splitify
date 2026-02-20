import uuid
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt
from app.models.group import Group
from app.services.calculation_service import get_group_financials


async def get_group_stats(db: AsyncSession, group_id: uuid.UUID) -> dict:
    group_result = await db.execute(select(Group.base_currency).where(Group.id == group_id))
    base_currency = group_result.scalar_one_or_none() or "SGD"

    receipt_count_result = await db.execute(
        select(func.count(Receipt.id)).where(Receipt.group_id == group_id)
    )
    receipt_count = receipt_count_result.scalar_one()

    financials = await get_group_financials(db, group_id)

    total_spending = sum((data["spent"] for data in financials.values()), Decimal("0"))

    spending_by_user = [
        {
            "user_id": str(user_id),
            "display_name": data["display_name"] or "Unknown",
            "amount": str(data["spent"].quantize(Decimal("0.01"))),
            "paid": str(data["paid"].quantize(Decimal("0.01"))),
            "balance": str(data["net_balance"].quantize(Decimal("0.01"))),
        }
        for user_id, data in financials.items()
    ]
    spending_by_user.sort(key=lambda x: Decimal(x["amount"]), reverse=True)

    return {
        "total_spending": str(total_spending.quantize(Decimal("0.01"))),
        "receipt_count": receipt_count,
        "spending_by_user": spending_by_user,
        "base_currency": base_currency,
    }
