# Standardize Financial Calculations

**Date:** 2026-02-20
**Status:** Approved

## Problem

Three services currently perform overlapping financial calculations with inconsistencies:

- `calculation_service.py` — shared `get_receipt_totals()` for assignments + payments (with optional period filter)
- `stats_service.py` — calls `get_receipt_totals()` but runs its own `SUM(receipt.total)` query; ignores `Settlement` records; has its own period filter
- `settlement_service.py` — calls `get_receipt_totals()` (all-time) + separately queries `Settlement` table + greedy algorithm

This causes the stats page balance to differ from the settlements page balance (no Settlement records included), inconsistent sign conventions, and duplicated query logic.

## Goal

Single source of truth for all financial calculations. Stats and settlement pages show the same balance.

## Design

### Approach: Expand `calculation_service.py`

`get_receipt_totals()` is replaced by `get_group_financials()` — a unified function that fetches assignments, payments, and settlements in one pass, returning a complete per-user financial picture.

### New Interface: `get_group_financials()`

```python
async def get_group_financials(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> dict[uuid.UUID, dict]:
```

Returns a dict keyed by `user_id`. Each entry:

| Field | Source | Meaning |
|---|---|---|
| `spent` | `SUM(line_item_assignment.share_amount * receipt.exchange_rate)` | Total assigned to user |
| `paid` | `SUM(payment.amount * receipt.exchange_rate)` | Total user paid on receipts |
| `settled_out` | `SUM(settlement.amount)` where user is `from_user` and `is_settled=True` | User paid off debts |
| `settled_in` | `SUM(settlement.amount)` where user is `to_user` and `is_settled=True` | User received payments |
| `net_balance` | `paid − spent + settled_out − settled_in` | Net position |
| `display_name` | `User.display_name` via join | |

**Sign convention:** positive `net_balance` = owed by others (creditor); negative = owes others (debtor).

No period filter — all figures are all-time.

### Changes to `stats_service.py`

- Remove `Period` enum, `get_period_start()`, and the `since` parameter
- Remove the separate `SUM(receipt.total)` query
- `total_spending` = sum of all users' `spent` values (total assigned amounts)
- Balance per user taken directly from `net_balance` (now includes settlements)
- Response shape unchanged

### Changes to `settlement_service.py`

- Remove `get_receipt_totals()` call and the separate `Settlement` query
- Call `get_group_financials()` instead
- Update greedy algorithm sign check: `net_balance < 0` = debtor, `net_balance > 0` = creditor
- Response shape unchanged

### Frontend Changes

- `stats/page.tsx`: remove period selector UI and period state
- No changes needed to the settlements page

### What Gets Deleted

- `get_receipt_totals()` from `calculation_service.py`
- `Period` enum and `get_period_start()` from `stats_service.py`
- Period selector from `stats/page.tsx`

## Non-Goals

- No changes to the greedy debt-simplification algorithm logic
- No changes to API response shapes
- No database schema changes
