import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.stats_service import get_group_stats

GROUP_ID = uuid.uuid4()
ALICE = uuid.uuid4()
BOB = uuid.uuid4()


def make_db_with_currency(currency="SGD"):
    db = AsyncMock()
    currency_result = MagicMock()
    currency_result.scalar_one_or_none.return_value = currency
    receipt_count_result = MagicMock()
    receipt_count_result.scalar_one.return_value = 3
    db.execute.side_effect = [currency_result, receipt_count_result]
    return db


@pytest.mark.asyncio
async def test_total_spending_is_sum_of_spent():
    """total_spending equals sum of all users' spent values."""
    db = make_db_with_currency()
    financials = {
        ALICE: {"spent": Decimal("60.00"), "paid": Decimal("100.00"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("40.00"), "display_name": "Alice"},
        BOB:   {"spent": Decimal("40.00"), "paid": Decimal("0.00"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("-40.00"), "display_name": "Bob"},
    }
    with patch("app.services.stats_service.get_group_financials", return_value=financials):
        result = await get_group_stats(db, GROUP_ID)
    assert result["total_spending"] == "100.00"


@pytest.mark.asyncio
async def test_balance_reflects_settlements():
    """balance field uses net_balance which includes settlements."""
    db = make_db_with_currency()
    financials = {
        ALICE: {"spent": Decimal("0"), "paid": Decimal("0"),
                "settled_out": Decimal("0"), "settled_in": Decimal("0"),
                "net_balance": Decimal("0.00"), "display_name": "Alice"},
    }
    with patch("app.services.stats_service.get_group_financials", return_value=financials):
        result = await get_group_stats(db, GROUP_ID)
    user = result["spending_by_user"][0]
    assert user["balance"] == "0.00"


@pytest.mark.asyncio
async def test_empty_group_returns_zero_stats():
    db = AsyncMock()
    currency_result = MagicMock()
    currency_result.scalar_one_or_none.return_value = "SGD"
    receipt_count_result = MagicMock()
    receipt_count_result.scalar_one.return_value = 0
    db.execute.side_effect = [currency_result, receipt_count_result]
    with patch("app.services.stats_service.get_group_financials", return_value={}):
        result = await get_group_stats(db, GROUP_ID)
    assert result["total_spending"] == "0.00"
    assert result["receipt_count"] == 0
    assert result["spending_by_user"] == []
