import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.calculation_service import get_group_financials


async def calculate_balances(db: AsyncSession, group_id: uuid.UUID) -> dict:
    """
    Calculate net balances and produce the minimal set of debt transfers.
    net_balance from get_group_financials():
      positive = owed by others (creditor)
      negative = owes others (debtor)
    """
    financials = await get_group_financials(db, group_id)

    if not financials:
        return {"balances": [], "total_assigned": Decimal("0"), "total_paid": Decimal("0")}

    total_assigned = sum((data["spent"] for data in financials.values()), Decimal("0"))
    total_paid = sum((data["paid"] for data in financials.values()), Decimal("0"))

    debtors = []   # [user_id, amount_owed, name]
    creditors = [] # [user_id, amount_credit, name]

    for user_id, data in financials.items():
        bal = data["net_balance"]
        name = data["display_name"] or "Unknown"
        if bal < 0:
            debtors.append([user_id, -bal, name])
        elif bal > 0:
            creditors.append([user_id, bal, name])

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    result = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amount, debtor_name = debtors[i]
        creditor_id, credit_amount, creditor_name = creditors[j]
        transfer = min(debt_amount, credit_amount)
        if transfer > Decimal("0.01"):
            result.append({
                "from_user_id": debtor_id,
                "from_user_name": debtor_name,
                "to_user_id": creditor_id,
                "to_user_name": creditor_name,
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
