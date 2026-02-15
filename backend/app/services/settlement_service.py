import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment, Settlement
from app.models.user import User


async def calculate_balances(db: AsyncSession, group_id: uuid.UUID) -> dict:
    """
    Calculate net balances for a group.
    Returns dict with:
      - balances: simplified list of debts
      - total_assigned: total amount assigned across all receipts
      - total_paid: total payments recorded
    """
    # Get receipt IDs for this group (select only id column)
    receipts_result = await db.execute(
        select(Receipt.id).where(Receipt.group_id == group_id)
    )
    receipt_ids = list(receipts_result.scalars().all())

    if not receipt_ids:
        return {"balances": [], "total_assigned": Decimal("0"), "total_paid": Decimal("0")}

    # Select assignments with exchange rate from receipt
    assignments_result = await db.execute(
        select(LineItemAssignment.user_id, LineItemAssignment.share_amount, Receipt.exchange_rate)
        .join(LineItem, LineItem.id == LineItemAssignment.line_item_id)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .where(LineItem.receipt_id.in_(receipt_ids))
    )
    assignments = assignments_result.all()

    # Select payments with exchange rate from receipt
    payments_result = await db.execute(
        select(Payment.paid_by, Payment.amount, Receipt.exchange_rate)
        .join(Receipt, Receipt.id == Payment.receipt_id)
        .where(Payment.receipt_id.in_(receipt_ids))
    )
    payments = payments_result.all()

    settlements_result = await db.execute(
        select(Settlement.from_user, Settlement.to_user, Settlement.amount)
        .where(
            Settlement.group_id == group_id,
            Settlement.is_settled == True,
        )
    )
    settlements = settlements_result.all()

    # Convert amounts to base currency using exchange_rate
    total_assigned = sum((share * rate for _, share, rate in assignments), Decimal("0"))
    total_paid = sum((amt * rate for _, amt, rate in payments), Decimal("0"))

    # Calculate net: positive = owes money, negative = is owed
    net = defaultdict(Decimal)

    for user_id, share_amount, rate in assignments:
        net[user_id] += share_amount * rate

    for paid_by, amount, rate in payments:
        net[paid_by] -= amount * rate

    for from_user, to_user, amount in settlements:
        net[from_user] -= amount
        net[to_user] += amount

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

    return {
        "balances": result,
        "total_assigned": total_assigned.quantize(Decimal("0.01")),
        "total_paid": total_paid.quantize(Decimal("0.01")),
    }
