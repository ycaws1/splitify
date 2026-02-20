import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment, Settlement
from app.models.user import User


async def get_group_financials(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> dict[uuid.UUID, dict]:
    """
    Returns complete per-user financial picture for a group (all-time).
    Keys per user: spent, paid, settled_out, settled_in, net_balance, display_name.
    net_balance = paid - spent + settled_out - settled_in.
    Positive net_balance = owed by others; negative = owes others.
    """
    assignments_result = await db.execute(
        select(
            LineItemAssignment.user_id,
            LineItemAssignment.share_amount,
            Receipt.exchange_rate,
            User.display_name,
        )
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .outerjoin(User, User.id == LineItemAssignment.user_id)
        .where(Receipt.group_id == group_id)
    )

    payments_result = await db.execute(
        select(
            Payment.paid_by,
            Payment.amount,
            Receipt.exchange_rate,
            User.display_name,
        )
        .select_from(Payment)
        .join(Receipt, Receipt.id == Payment.receipt_id)
        .outerjoin(User, User.id == Payment.paid_by)
        .where(Receipt.group_id == group_id)
    )

    settlements_result = await db.execute(
        select(Settlement.from_user, Settlement.to_user, Settlement.amount)
        .where(
            Settlement.group_id == group_id,
            Settlement.is_settled == True,
        )
    )

    financials: dict = defaultdict(lambda: {
        "spent": Decimal("0"),
        "paid": Decimal("0"),
        "settled_out": Decimal("0"),
        "settled_in": Decimal("0"),
        "display_name": None,
    })

    for user_id, share, rate, name in assignments_result.all():
        effective_rate = rate if rate is not None else Decimal("1")
        financials[user_id]["spent"] += share * effective_rate
        if name:
            financials[user_id]["display_name"] = name

    for user_id, amount, rate, name in payments_result.all():
        effective_rate = rate if rate is not None else Decimal("1")
        financials[user_id]["paid"] += amount * effective_rate
        if name and not financials[user_id]["display_name"]:
            financials[user_id]["display_name"] = name

    # Settlements are recorded in the group's base currency directly — no exchange rate needed.
    for from_user, to_user, amount in settlements_result.all():
        financials[from_user]["settled_out"] += amount
        financials[to_user]["settled_in"] += amount

    for data in financials.values():
        data["net_balance"] = (
            data["paid"] - data["spent"] + data["settled_out"] - data["settled_in"]
        )

    return dict(financials)
