import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment, Settlement
from app.models.user import User


async def calculate_balances(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_names: dict[uuid.UUID, str] | None = None,
) -> dict:
    """
    Calculate net balances for a group.
    Tax and service charge are stored as line items with assignments (same as regular items),
    so no separate distribution is needed — all charges flow through LineItemAssignment.
    Pass user_names to skip the user lookup query (saves a DB round trip).
    """
    # Fetch receipts-related totals from shared service (since=None for all time)
    from app.services.calculation_service import get_receipt_totals
    spending, paid, user_names_map = await get_receipt_totals(db, group_id, since=None)
    
    # Update local map if provided, otherwise rely on service return (but service return is partial)
    if user_names is None:
        user_names = {}
    # Merge service found names into user_names
    for uid, name in user_names_map.items():
        if uid not in user_names:
            user_names[uid] = name

    settlements_result = await db.execute(
        select(Settlement.from_user, Settlement.to_user, Settlement.amount)
        .where(
            Settlement.group_id == group_id,
            Settlement.is_settled == True,
        )
        .distinct()
    )

    settlements = settlements_result.all()

    if not spending and not paid:
        return {"balances": [], "total_assigned": Decimal("0"), "total_paid": Decimal("0")}

    net = defaultdict(Decimal)

    # 1. Assignments (spending) -> User owes money (negative net)
    # Wait, original logic: 
    # net[user_id] += share_amount * rate
    # debtors = positive net?
    # Let's check original logic lines 74-78:
    # if amount > 0: debtors.append...
    # So POSITIVE net means you are a DEBTOR (you OWE money)?
    # Let's re-read original lines 57-58:
    # for ... assignments: net[user_id] += share
    # So if I spent 50, my net is +50.
    # If I PAID 50 (lines 64-65): net[paid_by] -= amount
    # So if I spent 50 and paid 0, net is +50. I am a DEBTOR. Correct.
    # If I spent 0 and paid 50, net is -50. I am a CREDITOR. Correct.
    
    for user_id, amount in spending.items():
        net[user_id] += amount
        
    for user_id, amount in paid.items():
        net[user_id] -= amount
        
    total_assigned = sum(spending.values())
    total_paid = sum(paid.values())

    # 3. Settled amounts
    for from_user, to_user, amount in settlements:
        net[from_user] -= amount
        net[to_user] += amount

    debtors = []
    creditors = []
    for user_id, amount in net.items():
        if amount > 0:
            debtors.append([user_id, amount])
        elif amount < 0:
            creditors.append([user_id, -amount])

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    # Resolve user names: use provided map or fetch from DB
    users_map: dict = user_names or {}
    if not users_map:
        all_user_ids = list(net.keys())
        if all_user_ids:
            users_result = await db.execute(
                select(User.id, User.display_name).where(User.id.in_(all_user_ids))
            )
            users_map = {uid: name for uid, name in users_result.all()}

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
