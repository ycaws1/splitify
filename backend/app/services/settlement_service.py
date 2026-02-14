import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment, Settlement
from app.models.user import User


async def calculate_balances(db: AsyncSession, group_id: uuid.UUID) -> list[dict]:
    """
    Calculate net balances for a group.
    Returns simplified list of {from_user_id, from_user_name, to_user_id, to_user_name, amount} debts.
    """
    # Get all receipts in the group
    receipts_result = await db.execute(
        select(Receipt).where(Receipt.group_id == group_id)
    )
    receipts = receipts_result.scalars().all()
    receipt_ids = [r.id for r in receipts]

    if not receipt_ids:
        return []

    # Get all assignments (what each user owes)
    assignments_result = await db.execute(
        select(LineItemAssignment)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .where(LineItem.receipt_id.in_(receipt_ids))
    )
    assignments = assignments_result.scalars().all()

    # Get all payments (what each user paid)
    payments_result = await db.execute(
        select(Payment).where(Payment.receipt_id.in_(receipt_ids))
    )
    payments = payments_result.scalars().all()

    # Get settled amounts
    settlements_result = await db.execute(
        select(Settlement).where(
            Settlement.group_id == group_id,
            Settlement.is_settled == True,
        )
    )
    settlements = settlements_result.scalars().all()

    # Calculate net: positive = owes money, negative = is owed
    net = defaultdict(Decimal)

    for a in assignments:
        net[a.user_id] += a.share_amount  # user owes this much

    for p in payments:
        net[p.paid_by] -= p.amount  # user paid this much

    for s in settlements:
        net[s.from_user] -= s.amount  # settled debt reduces what they owe
        net[s.to_user] += s.amount  # and reduces what they're owed

    # Simplify debts using greedy algorithm
    debtors = []  # (user_id, amount they owe)
    creditors = []  # (user_id, amount they're owed)

    for user_id, amount in net.items():
        if amount > 0:
            debtors.append([user_id, amount])
        elif amount < 0:
            creditors.append([user_id, -amount])

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    # Fetch user names
    all_user_ids = list(net.keys())
    users_map = {}
    if all_user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(all_user_ids)))
        users_map = {u.id: u.display_name for u in users_result.scalars().all()}

    result = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amount = debtors[i]
        creditor_id, credit_amount = creditors[j]

        transfer = min(debt_amount, credit_amount)
        if transfer > Decimal("0.01"):
            result.append({
                "from_user_id": debtor_id,
                "from_user_name": users_map.get(debtor_id, "Unknown"),
                "to_user_id": creditor_id,
                "to_user_name": users_map.get(creditor_id, "Unknown"),
                "amount": transfer.quantize(Decimal("0.01")),
            })

        debtors[i][1] -= transfer
        creditors[j][1] -= transfer

        if debtors[i][1] <= Decimal("0.01"):
            i += 1
        if creditors[j][1] <= Decimal("0.01"):
            j += 1

    return result
