import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, noload

from app.models.receipt import Receipt, LineItem, LineItemAssignment, ReceiptStatus
from app.models.group import GroupMember
from app.models.user import User
from app.utils.currency_utils import compute_shares


def _receipt_load_options():
    """Eager-load line_items -> assignments -> user in a single joined query."""
    return [
        joinedload(Receipt.line_items)
            .joinedload(LineItem.assignments)
            .joinedload(LineItemAssignment.user),
        joinedload(Receipt.uploader),
    ]


async def create_receipt(
    db: AsyncSession, group_id: uuid.UUID, image_url: str, user: User, currency: str | None = None
) -> Receipt:
    receipt = Receipt(
        group_id=group_id,
        uploaded_by=user.id,
        image_url=image_url,
        status=ReceiptStatus.processing,
        currency=currency if currency else "SGD",
    )
    db.add(receipt)
    await db.commit()
    result = await db.execute(
        select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt.id)
    )
    return result.unique().scalar_one()


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
                shares = compute_shares(li.amount, member_ids, seed=str(li.id))
                for uid, share in shares.items():
                    db.add(LineItemAssignment(
                        line_item_id=li.id,
                        user_id=uid,
                        share_amount=share,
                    ))

    await db.commit()
    result = await db.execute(
        select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt.id)
    )
    return result.unique().scalar_one()


async def list_receipts(db: AsyncSession, group_id: uuid.UUID) -> list[Receipt]:
    result = await db.execute(
        select(Receipt)
        .options(noload(Receipt.line_items), noload(Receipt.uploader))
        .where(Receipt.group_id == group_id)
        .order_by(Receipt.created_at.desc())
    )
    return list(result.scalars().all())


async def list_processing_receipts(db: AsyncSession, user_id: uuid.UUID) -> list[Receipt]:
    """List all processing/failed receipts across all groups the user belongs to."""
    from app.models.group import GroupMember, Group
    result = await db.execute(
        select(Receipt, Group.name.label("group_name"))
        .options(noload(Receipt.line_items), noload(Receipt.uploader))
        .join(Group, Group.id == Receipt.group_id)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            GroupMember.user_id == user_id,
            Receipt.status.in_(["processing", "failed"]),
        )
        .order_by(Receipt.created_at.desc())
    )
    return result.all()


async def get_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> Receipt | None:
    result = await db.execute(
        select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt_id)
    )
    return result.unique().scalar_one_or_none()


from app.services.exchange_rate_service import get_exchange_rate
from app.models.group import Group

async def update_receipt(
    db: AsyncSession, receipt_id: uuid.UUID, data: dict, expected_version: int | None
) -> Receipt | None:
    """Update receipt with optimistic locking. Returns None if version conflict."""
    # Check if currency is changing
    if "currency" in data:
        # We need the group's base currency to calculate exchange rate
        start_receipt = await get_receipt(db, receipt_id)
        if not start_receipt:
            return None
        
        # Avoid redundant update if currency is same
        if start_receipt.currency != data["currency"]:
            group_result = await db.execute(select(Group).where(Group.id == start_receipt.group_id))
            group = group_result.scalar_one()
            
            # Update exchange rate
            try:
                new_rate = await get_exchange_rate(data["currency"], group.base_currency)
                data["exchange_rate"] = new_rate
            except Exception:
                # Fallback or log error? For now, keep old rate or default 1?
                # Best to fail loud or default 1 if service down.
                # But here valid currency is expected.
                pass

    stmt = update(Receipt).where(Receipt.id == receipt_id)
    
    if expected_version is not None:
        stmt = stmt.where(Receipt.version == expected_version)
        values = {**data, "version": expected_version + 1}
    else:
        # Force update: verify receipt exists first (implicit in update count, but returning deals with it)
        # Just increment version atomically
        values = {**data, "version": Receipt.version + 1}

    result = await db.execute(
        stmt.values(**values).returning(Receipt.id)
    )
    updated_id = result.scalar_one_or_none()
    if not updated_id:
        return None
    await db.commit()
    return await get_receipt(db, receipt_id)


async def delete_all_receipts(db: AsyncSession, group_id: uuid.UUID) -> int:
    """Delete all receipts in a group using efficient bulk operations."""
    from sqlalchemy import select, delete
    from app.models.receipt import Receipt, LineItem, LineItemAssignment
    from app.models.payment import Payment

    # 1. Gather receipt IDs
    result = await db.execute(select(Receipt.id).where(Receipt.group_id == group_id))
    receipt_ids = list(result.scalars().all())

    if not receipt_ids:
        return 0

    # 2. Gather line item IDs
    li_result = await db.execute(select(LineItem.id).where(LineItem.receipt_id.in_(receipt_ids)))
    line_item_ids = list(li_result.scalars().all())

    # 3. Bulk delete bottom-up to maintain foreign key integrity
    if line_item_ids:
        await db.execute(delete(LineItemAssignment).where(LineItemAssignment.line_item_id.in_(line_item_ids)))
        await db.execute(delete(LineItem).where(LineItem.receipt_id.in_(receipt_ids)))

    if receipt_ids:
        await db.execute(delete(Payment).where(Payment.receipt_id.in_(receipt_ids)))
        await db.execute(delete(Receipt).where(Receipt.id.in_(receipt_ids)))

    await db.commit()
    return len(receipt_ids)


async def delete_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> bool:
    from sqlalchemy import select, delete
    from app.models.receipt import Receipt, LineItem, LineItemAssignment
    from app.models.payment import Payment

    # 1. Gather line item IDs for this receipt
    li_result = await db.execute(select(LineItem.id).where(LineItem.receipt_id == receipt_id))
    line_item_ids = list(li_result.scalars().all())

    # 2. Bulk delete bottom-up to maintain foreign key integrity
    if line_item_ids:
        await db.execute(delete(LineItemAssignment).where(LineItemAssignment.line_item_id.in_(line_item_ids)))
        await db.execute(delete(LineItem).where(LineItem.receipt_id == receipt_id))

    await db.execute(delete(Payment).where(Payment.receipt_id == receipt_id))
    
    # 3. Delete receipt and check if it existed
    result = await db.execute(delete(Receipt).where(Receipt.id == receipt_id))
    if result.rowcount == 0:
        return False

    await db.commit()
    return True


async def add_line_item(db: AsyncSession, receipt_id: uuid.UUID, description: str, amount: Decimal, quantity: Decimal) -> LineItem:
    # Get receipt to check it exists
    result = await db.execute(select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt_id))
    receipt = result.unique().scalar_one_or_none()
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
        .options(joinedload(LineItem.assignments).joinedload(LineItemAssignment.user))
        .where(LineItem.id == item_id)
    )
    return result.unique().scalar_one()


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

async def bulk_update_receipt_items(
    db: AsyncSession, receipt_id: uuid.UUID, data: dict
) -> Receipt | None:
    from sqlalchemy import delete
    from decimal import Decimal
    
    result = await db.execute(select(Receipt).options(*_receipt_load_options()).where(Receipt.id == receipt_id))
    receipt = result.unique().scalar_one_or_none()
    if not receipt:
        return None

    existing_items = {str(item.id): item for item in receipt.line_items}
    incoming_items = data.get("items", [])
    incoming_ids = {str(item["id"]) for item in incoming_items if not str(item["id"]).startswith("temp-")}

    # Delete items missing from incoming
    items_to_delete = [uuid.UUID(item_id) for item_id in existing_items if item_id not in incoming_ids]
    if items_to_delete:
        await db.execute(delete(LineItemAssignment).where(LineItemAssignment.line_item_id.in_(items_to_delete)))
        await db.execute(delete(LineItem).where(LineItem.id.in_(items_to_delete)))

    # Process updates and creates
    max_sort = max([item.sort_order for item in receipt.line_items] + [0])
    
    for incoming in incoming_items:
        incoming_id = str(incoming["id"])
        qty = Decimal(str(incoming["quantity"]))
        amt = Decimal(str(incoming["amount"]))
        unit_price = amt / qty if qty else amt

        if incoming_id.startswith("temp-"):
            max_sort += 1
            new_item = LineItem(
                receipt_id=receipt_id,
                description=incoming["description"],
                quantity=qty,
                amount=amt,
                unit_price=unit_price,
                sort_order=max_sort
            )
            db.add(new_item)
        else:
            existing = existing_items.get(incoming_id)
            if existing:
                existing.description = incoming["description"]
                existing.quantity = qty
                existing.amount = amt
                existing.unit_price = unit_price

    # Update receipt totals and version
    receipt_updates = {"version": Receipt.version + 1}
    for field in ["subtotal", "tax", "service_charge", "total"]:
        if field in data and data[field] is not None:
            receipt_updates[field] = Decimal(str(data[field]))
        elif field in data:
            receipt_updates[field] = None
            
    await db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id)
        .values(**receipt_updates)
    )

    await db.commit()
    return await get_receipt(db, receipt_id)
