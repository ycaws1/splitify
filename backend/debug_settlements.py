import asyncio
import sys
from decimal import Decimal
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.models.receipt import Receipt, LineItem, LineItemAssignment
from app.models.payment import Payment, Settlement
from app.models.user import User
from app.models.group import Group

from sqlalchemy.orm import aliased

TARGET_GROUP_NAME = "Trip to Danang"

async def debug_group_finances():
    async with async_session_factory() as db:
        print("\n--- FINDING GROUP ---")
        groups = (await db.scalars(select(Group))).all()
        target_group = None
        for g in groups:
            print(f"Found Group: {g.name} ({g.id})")
            if g.name == TARGET_GROUP_NAME:
                target_group = g
        
        if not target_group:
            if groups:
                target_group = groups[0]
                print(f"Target group '{TARGET_GROUP_NAME}' not found, defaulting to first group: {target_group.name}")
            else:
                print("No groups found.")
                return

        group_id = target_group.id
        print(f"\n--- Debugging Group: {target_group.name} ({group_id}) ---\n")
        print(f"Base Currency: {target_group.base_currency}")

        # 2. Check Settlements
        print("\n--- SETTLEMENTS ---")
        u2 = aliased(User)
        settlements = (await db.execute(
            select(Settlement, User.display_name.label("from_name"), u2.display_name.label("to_name"))
            .join(User, User.id == Settlement.from_user)
            .join(u2, u2.id == Settlement.to_user)
            .where(Settlement.group_id == group_id)
        )).all()
        
        if not settlements:
            print("No settlements found.")
        else:
            total_settled = Decimal("0")
            for s, from_n, to_n in settlements:
                status = "SETTLED" if s.is_settled else "PENDING"
                print(f"[{status}] {from_n} -> {to_n}: {s.amount} (ID: {s.id})")
                if s.is_settled:
                    total_settled += s.amount
            print(f"Total Settled Amount: {total_settled}")

        # 3. Check Receipts totals
        print("\n--- RECEIPTS TOTALS ---")
        receipts = (await db.scalars(
            select(Receipt).where(Receipt.group_id == group_id)
        )).all()
        
        total_receipts_amount = Decimal("0")
        for r in receipts:
            print(f"Receipt {r.id} | Total: {r.total} | {r.merchant_name} | Rate: {r.exchange_rate}")
            total_receipts_amount += (r.total or 0) * r.exchange_rate
        print(f"Total Receipts Value (in base): {total_receipts_amount}")

        # 4. Check Payments
        print("\n--- PAYMENTS ---")
        payments = (await db.execute(
            select(Payment, User.display_name)
            .join(User, User.id == Payment.paid_by)
            .where(Payment.receipt_id.in_([r.id for r in receipts]))
        )).all()
        
        total_payments = Decimal("0")
        for p, name in payments:
            rate = next((r.exchange_rate for r in receipts if r.id == p.receipt_id), Decimal("1"))
            amt_base = p.amount * rate
            print(f"Payment by {name}: {p.amount} (Rate: {rate}) -> {amt_base} base")
            total_payments += amt_base
        print(f"Total Payments Value (in base): {total_payments}")

if __name__ == "__main__":
    asyncio.run(debug_group_finances())
