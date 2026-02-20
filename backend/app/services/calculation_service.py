import uuid
from collections import defaultdict
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment
from app.models.user import User

async def get_receipt_totals(
    db: AsyncSession, 
    group_id: uuid.UUID, 
    since: datetime | None = None
) -> tuple[dict[uuid.UUID, Decimal], dict[uuid.UUID, Decimal], dict[uuid.UUID, str]]:
    """
    Calculate spending (assignments) and payments (receipt payments) for a group.
    Returns:
        (spending_map, payment_map, user_names_map)
    where maps are user_id -> amount (Decimal).
    Amounts are converted to the receipt's base currency using the stored exchange rate.
    """
    
    # Base query filters
    assignment_filters = [Receipt.group_id == group_id]
    payment_filters = [Receipt.group_id == group_id]
    
    if since:
        assignment_filters.append(Receipt.created_at >= since)
        payment_filters.append(Receipt.created_at >= since)

    # 1. Fetch assignments (includes Tax / Service Charge line items)
    assignments_result = await db.execute(
        select(
            LineItemAssignment.user_id,
            LineItemAssignment.share_amount,
            Receipt.exchange_rate,
            User.display_name
        )
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .outerjoin(User, User.id == LineItemAssignment.user_id)
        .where(*assignment_filters)
    )

    # 2. Fetch Payments on Receipts
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
        .where(*payment_filters)
    )

    assignments = assignments_result.all()
    payments_data = payments_result.all()

    spending = defaultdict(Decimal)
    paid = defaultdict(Decimal)
    user_names = {}

    # Process Spending
    for user_id, share, rate, name in assignments:
        spending[user_id] += share * rate
        if name:
            user_names[user_id] = name

    # Process Payments
    for user_id, amount, rate, name in payments_data:
        paid[user_id] += amount * rate
        if name and user_id not in user_names:
            user_names[user_id] = name

    return spending, paid, user_names


from app.models.payment import Settlement as _Settlement  # avoid re-import clash

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
        select(_Settlement.from_user, _Settlement.to_user, _Settlement.amount)
        .where(
            _Settlement.group_id == group_id,
            _Settlement.is_settled == True,
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
        financials[user_id]["spent"] += share * rate
        if name:
            financials[user_id]["display_name"] = name

    for user_id, amount, rate, name in payments_result.all():
        financials[user_id]["paid"] += amount * rate
        if name and not financials[user_id]["display_name"]:
            financials[user_id]["display_name"] = name

    for from_user, to_user, amount in settlements_result.all():
        financials[from_user]["settled_out"] += amount
        financials[to_user]["settled_in"] += amount

    for data in financials.values():
        data["net_balance"] = (
            data["paid"] - data["spent"] + data["settled_out"] - data["settled_in"]
        )

    return dict(financials)
