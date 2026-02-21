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
            Receipt.id.label("receipt_id"),
            Receipt.exchange_rate,
            LineItem.id.label("line_item_id"),
            LineItem.amount.label("amount"),
            LineItemAssignment.user_id,
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

    receipts_data = {}

    for row in assignments_result.all():
        rid = row.receipt_id
        lid = row.line_item_id
        uid = row.user_id
        
        if rid not in receipts_data:
            receipts_data[rid] = {
                "exchange_rate": row.exchange_rate if row.exchange_rate is not None else Decimal("1"),
                "line_items": {}
            }
            
        if lid not in receipts_data[rid]["line_items"]:
            receipts_data[rid]["line_items"][lid] = {
                "amount": row.amount,
                "user_ids": []
            }
            
        receipts_data[rid]["line_items"][lid]["user_ids"].append(uid)
        
        if row.display_name and not financials[uid]["display_name"]:
            financials[uid]["display_name"] = row.display_name

    from app.utils.currency_utils import compute_receipt_shares
    
    # Track unrounded exact fractions for the entire group
    group_exact_totals = {}
    total_group_cents = 0

    for rid, r_data in receipts_data.items():
        line_items_list = list(r_data["line_items"].values())
        rate = r_data["exchange_rate"]
        
        # Calculate exactly how many cents this receipt adds to the group total
        # We need this to distribute remainder pennies later
        receipt_cents = 0
        
        for item in line_items_list:
            amount = item["amount"]
            user_ids = item["user_ids"]
            n_users = len(user_ids)
            if n_users == 0: continue
            
            # Exact fractional split * exchange rate
            exact_share = (amount / Decimal(n_users)) * rate
            
            for uid in user_ids:
                if uid not in group_exact_totals:
                    group_exact_totals[uid] = Decimal("0")
                group_exact_totals[uid] += exact_share
            
            receipt_cents += int((amount * rate * Decimal("100")).to_integral_value(rounding="ROUND_DOWN"))
            
        total_group_cents += receipt_cents
        
    # Distribute group-level remaining cents perfectly among the users
    if group_exact_totals:
        base_user_cents = {}
        total_base_cents = 0
        all_users = list(group_exact_totals.keys())
        
        for uid in all_users:
            cents_exact = group_exact_totals[uid] * Decimal("100")
            base_cents = int(cents_exact.to_integral_value(rounding="ROUND_DOWN"))
            base_user_cents[uid] = base_cents
            total_base_cents += base_cents

        extra_count = total_group_cents - total_base_cents
        
        # We don't need a deterministic hash here because order doesn't matter
        # as much when it's done once per group, but we can just use the UUID string
        sorted_ids = sorted(all_users, key=str)
        
        for i, uid in enumerate(sorted_ids):
            cents = base_user_cents[uid] + (1 if i < extra_count else 0)
            financials[uid]["spent"] += Decimal(cents) / Decimal("100")

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
