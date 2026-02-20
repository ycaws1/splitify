import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import pytest

from app.services.settlement_service import calculate_balances

GROUP_ID = uuid.uuid4()
ALICE = uuid.uuid4()
BOB = uuid.uuid4()
CHARLIE = uuid.uuid4()


@pytest.mark.asyncio
async def test_simple_debt_resolution():
    """Alice owes Bob: produces one transfer Alice -> Bob."""
    db = AsyncMock()
    financials = {
        ALICE: {"spent": Decimal("100"), "paid": Decimal("0"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("-100"), "display_name": "Alice"},
        BOB:   {"spent": Decimal("0"), "paid": Decimal("100"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("100"), "display_name": "Bob"},
    }
    with patch("app.services.settlement_service.get_group_financials", return_value=financials):
        result = await calculate_balances(db, GROUP_ID)
    assert len(result["balances"]) == 1
    transfer = result["balances"][0]
    assert transfer["from_user_id"] == ALICE
    assert transfer["to_user_id"] == BOB
    assert transfer["amount"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_settlement_reduces_debt():
    """Completed settlement (reflected in net_balance) produces no remaining transfer."""
    db = AsyncMock()
    financials = {
        ALICE: {"spent": Decimal("100"), "paid": Decimal("0"),
                "settled_out": Decimal("100"), "settled_in": Decimal("0"),
                "net_balance": Decimal("0"),   # 0 - 100 + 100 - 0 = 0
                "display_name": "Alice"},
        BOB:   {"spent": Decimal("0"), "paid": Decimal("100"),
                "settled_out": Decimal("0"), "settled_in": Decimal("100"),
                "net_balance": Decimal("0"),   # 100 - 0 + 0 - 100 = 0
                "display_name": "Bob"},
    }
    with patch("app.services.settlement_service.get_group_financials", return_value=financials):
        result = await calculate_balances(db, GROUP_ID)
    assert result["balances"] == []


@pytest.mark.asyncio
async def test_totals_returned():
    """total_assigned and total_paid are sums across all users."""
    db = AsyncMock()
    financials = {
        ALICE: {"spent": Decimal("60"), "paid": Decimal("100"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("40"), "display_name": "Alice"},
        BOB:   {"spent": Decimal("40"), "paid": Decimal("0"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("-40"), "display_name": "Bob"},
    }
    with patch("app.services.settlement_service.get_group_financials", return_value=financials):
        result = await calculate_balances(db, GROUP_ID)
    assert result["total_assigned"] == Decimal("100.00")
    assert result["total_paid"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_empty_group():
    db = AsyncMock()
    with patch("app.services.settlement_service.get_group_financials", return_value={}):
        result = await calculate_balances(db, GROUP_ID)
    assert result == {"balances": [], "total_assigned": Decimal("0"), "total_paid": Decimal("0")}
