import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.receipt import Receipt, LineItem, LineItemAssignment, ReceiptStatus
from app.models.group import GroupMember
from app.models.user import User


def _receipt_load_options():
    """Eager-load line_items -> assignments for ReceiptResponse serialization."""
    return [
        selectinload(Receipt.line_items).selectinload(LineItem.assignments),
    ]


async def create_receipt(
    db: AsyncSession, group_id: uuid.UUID, image_url: str, user: User
) -> Receipt:
    receipt = Receipt(
        group_id=group_id,
        uploaded_by=user.id,
        image_url=image_url,
        status=ReceiptStatus.processing,
    )
    db.add(receipt)
    await db.commit()
    result = await db.execute(
        select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt.id)
    )
    return result.scalar_one()


async def create_manual_receipt(
    db: AsyncSession,
    group_id: uuid.UUID,
    user: User,
    merchant_name: str,
    currency: str,
    items: list[dict],
    receipt_date=None,
    tax: Decimal | None = None,
    service_charge: Decimal | None = None,
    exchange_rate: Decimal = Decimal("1"),
) -> Receipt:
    total = sum(Decimal(str(item["amount"])) for item in items)
    if tax:
        total += tax
    if service_charge:
        total += service_charge

    receipt = Receipt(
        group_id=group_id,
        uploaded_by=user.id,
        image_url="",
        merchant_name=merchant_name,
        receipt_date=receipt_date,
        currency=currency,
        exchange_rate=exchange_rate,
        subtotal=sum(Decimal(str(item["amount"])) for item in items),
        tax=tax,
        service_charge=service_charge,
        total=total,
        status=ReceiptStatus.confirmed,
    )
    db.add(receipt)
    await db.flush()

    sort = 0
    for item in items:
        qty = Decimal(str(item.get("quantity", 1)))
        amount = Decimal(str(item["amount"]))
        unit_price = amount / qty if qty else amount
        line_item = LineItem(
            receipt_id=receipt.id,
            description=item["description"],
            quantity=qty,
            unit_price=unit_price,
            amount=amount,
            sort_order=sort,
        )
        db.add(line_item)
        sort += 1

    # Fetch group members for auto-assigning tax/service charge
    shared_line_items: list[LineItem] = []

    if tax and tax > 0:
        li = LineItem(
            receipt_id=receipt.id,
            description="Tax",
            quantity=Decimal("1"),
            unit_price=tax,
            amount=tax,
            sort_order=sort,
        )
        db.add(li)
        shared_line_items.append(li)
        sort += 1

    if service_charge and service_charge > 0:
        li = LineItem(
            receipt_id=receipt.id,
            description="Service Charge",
            quantity=Decimal("1"),
            unit_price=service_charge,
            amount=service_charge,
            sort_order=sort,
        )
        db.add(li)
        shared_line_items.append(li)
        sort += 1

    if shared_line_items:
        await db.flush()  # ensure line item IDs are generated
        members_result = await db.execute(
            select(GroupMember.user_id).where(GroupMember.group_id == group_id)
        )
        member_ids = list(members_result.scalars().all())
        num_members = len(member_ids)
        if num_members > 0:
            for li in shared_line_items:
                share = (li.amount / Decimal(num_members)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                for uid in member_ids:
                    db.add(LineItemAssignment(
                        line_item_id=li.id,
                        user_id=uid,
                        share_amount=share,
                    ))

    await db.commit()
    result = await db.execute(
        select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt.id)
    )
    return result.scalar_one()


async def list_receipts(db: AsyncSession, group_id: uuid.UUID) -> list[Receipt]:
    result = await db.execute(
        select(Receipt)
        .where(Receipt.group_id == group_id)
        .order_by(Receipt.created_at.desc())
    )
    return list(result.scalars().all())


async def get_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> Receipt | None:
    result = await db.execute(
        select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt_id)
    )
    return result.scalar_one_or_none()


async def update_receipt(
    db: AsyncSession, receipt_id: uuid.UUID, data: dict, expected_version: int
) -> Receipt | None:
    """Update receipt with optimistic locking. Returns None if version conflict."""
    result = await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.version == expected_version)
        .values(**data, version=expected_version + 1)
        .returning(Receipt.id)
    )
    updated_id = result.scalar_one_or_none()
    if not updated_id:
        return None
    await db.commit()
    return await get_receipt(db, receipt_id)


async def delete_all_receipts(db: AsyncSession, group_id: uuid.UUID) -> int:
    """Delete all receipts in a group. Returns count deleted."""
    result = await db.execute(
        select(Receipt)
        .options(selectinload(Receipt.payments))
        .where(Receipt.group_id == group_id)
    )
    receipts = list(result.scalars().all())
    for r in receipts:
        await db.delete(r)
    await db.commit()
    return len(receipts)


async def delete_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Receipt)
        .options(selectinload(Receipt.payments))
        .where(Receipt.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        return False
    await db.delete(receipt)
    await db.commit()
    return True


async def add_line_item(db: AsyncSession, receipt_id: uuid.UUID, description: str, amount: Decimal, quantity: Decimal) -> LineItem:
    # Get receipt to check it exists
    result = await db.execute(select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        return None
    
    # Calculate sort order
    max_sort = 0
    if receipt.line_items:
        max_sort = max(li.sort_order for li in receipt.line_items) + 1
    
    qty = Decimal(str(quantity))
    amt = Decimal(str(amount))
    unit_price = amt / qty if qty else amt
    
    item = LineItem(
        receipt_id=receipt_id,
        description=description,
        quantity=qty,
        amount=amt,
        unit_price=unit_price,
        sort_order=max_sort
    )
    db.add(item)
    
    # Bump version
    receipt.version += 1
    
    await db.commit()
    await db.refresh(item)
    # create new item -> no assignments yet
    # prevent lazy loading error by setting explicit empty list
    item.assignments = [] 
    return item


async def update_line_item(db: AsyncSession, item_id: uuid.UUID, data: dict) -> LineItem | None:
    # First get the item with assignments loaded
    result = await db.execute(
        select(LineItem)
        .options(selectinload(LineItem.assignments))
        .where(LineItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
        
    # Update fields
    for k, v in data.items():
        if v is not None:
            # Handle decimals
            if k in ["amount", "quantity"] and v is not None:
                v = Decimal(str(v))
            setattr(item, k, v)
            
    # Recalculate unit price
    item.unit_price = item.amount / item.quantity if item.quantity else item.amount
    
    # Bump receipt version
    await db.execute(
        update(Receipt)
        .where(Receipt.id == item.receipt_id)
        .values(version=Receipt.version + 1)
    )
    
    await db.commit()
    
    # Re-fetch to ensure assignments are loaded and item is fresh
    result = await db.execute(
        select(LineItem)
        .options(selectinload(LineItem.assignments))
        .where(LineItem.id == item_id)
    )
    return result.scalar_one()


async def delete_line_item(db: AsyncSession, item_id: uuid.UUID) -> bool:
    result = await db.execute(select(LineItem).where(LineItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        return False
        
    receipt_id = item.receipt_id
    await db.delete(item)
    
    # Bump receipt version
    await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id)
        .values(version=Receipt.version + 1)
    )
    
    await db.commit()
    return True
