import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.calculation_service import get_group_financials


def make_db(assignment_rows=None, payment_rows=None, settlement_rows=None):
    """Return a mock AsyncSession whose execute() returns preset rows."""
    db = AsyncMock()
    results = []
    for rows in [assignment_rows or [], payment_rows or [], settlement_rows or []]:
        r = MagicMock()
        r.all.return_value = rows
        results.append(r)
    db.execute.side_effect = results
    return db


GROUP_ID = uuid.uuid4()
ALICE = uuid.uuid4()
BOB = uuid.uuid4()


@pytest.mark.asyncio
async def test_basic_spending_and_payment():
    """User who spent more than paid has negative net_balance."""
    db = make_db(
        assignment_rows=[(ALICE, Decimal("100.00"), Decimal("1.0"), "Alice")],
        payment_rows=[(ALICE, Decimal("50.00"), Decimal("1.0"), "Alice")],
    )
    result = await get_group_financials(db, GROUP_ID)
    assert result[ALICE]["spent"] == Decimal("100.00")
    assert result[ALICE]["paid"] == Decimal("50.00")
    assert result[ALICE]["net_balance"] == Decimal("-50.00")


@pytest.mark.asyncio
async def test_creditor_has_positive_balance():
    """User who paid more than spent has positive net_balance."""
    db = make_db(
        payment_rows=[(BOB, Decimal("100.00"), Decimal("1.0"), "Bob")],
    )
    result = await get_group_financials(db, GROUP_ID)
    assert result[BOB]["net_balance"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_settlement_adjusts_balance():
    """Completed settlement reduces debtor debt and creditor credit."""
    # Alice owes Bob 100. Settlement: Alice pays Bob 100.
    db = make_db(
        assignment_rows=[(ALICE, Decimal("100.00"), Decimal("1.0"), "Alice")],
        payment_rows=[(BOB, Decimal("100.00"), Decimal("1.0"), "Bob")],
        settlement_rows=[(ALICE, BOB, Decimal("100.00"))],
    )
    result = await get_group_financials(db, GROUP_ID)
    assert result[ALICE]["net_balance"] == Decimal("0.00")
    assert result[BOB]["net_balance"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_exchange_rate_applied():
    """share_amount and payment are multiplied by receipt exchange_rate."""
    db = make_db(
        assignment_rows=[(ALICE, Decimal("50.00"), Decimal("1.3"), "Alice")],
        payment_rows=[(ALICE, Decimal("50.00"), Decimal("1.3"), "Alice")],
    )
    result = await get_group_financials(db, GROUP_ID)
    assert result[ALICE]["spent"] == Decimal("65.00")
    assert result[ALICE]["paid"] == Decimal("65.00")
    assert result[ALICE]["net_balance"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_display_name_captured():
    db = make_db(
        assignment_rows=[(ALICE, Decimal("10.00"), Decimal("1.0"), "Alice")],
    )
    result = await get_group_financials(db, GROUP_ID)
    assert result[ALICE]["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_empty_group_returns_empty_dict():
    db = make_db()
    result = await get_group_financials(db, GROUP_ID)
    assert result == {}
