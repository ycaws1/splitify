# Stats Page Enhancement - Paid & Owed Information

## ✅ Feature Implemented

Added comprehensive financial breakdown to the stats page showing:
- **Spent** - How much each member consumed/was assigned
- **Paid** - How much each member actually paid for receipts  
- **Balance** - The difference (positive = owed by others, negative = they owe)

## 🎨 User Interface

### New Display Format

Each member card now shows:
```
┌─────────────────────────────────────┐
│ Member Name                         │
│                                     │
│ Spent    Paid      Balance          │
│ $50.00   $75.00    +$25.00         │
│                                     │
│ ✓ Owed $25.00 by others            │
└─────────────────────────────────────┘
```

### Color Coding
- **Green (Emerald)**: Positive balance = owed money by others
- **Red (Rose)**: Negative balance = owes money
- **Gray**: Balanced = all settled up
- **Paid amounts**: Always shown in green

### Balance Messages
- **Positive**: "✓ Owed $X.XX by others"
- **Negative**: "↓ Owes $X.XX"
- **Zero**: "✓ All settled up"

## 🔧 Technical Implementation

### Backend Changes
**File**: `/backend/app/services/stats_service.py`

Added queries to calculate:
1. **Per-user spending**: Sum of line item assignments (what they consumed)
2. **Per-user payments**: Sum of payments made (what they paid)
3. **Balance calculation**: `paid - spent`

The stats now include exchange rate conversion to ensure all amounts are in the group's base currency.

**Response format**:
```json
{
  "period": "1mo",
  "total_spending": "150.00",
  "receipt_count": 5,
  "spending_by_user": [
    {
      "user_id": "...",
      "display_name": "Alice",
      "amount": "50.00",     // What they spent
      "paid": "75.00",       // What they paid
      "balance": "25.00"     // paid - spent
    }
  ]
}
```

### Frontend Changes
**File**: `/frontend/src/app/groups/[id]/stats/page.tsx`

Updated to:
- Display 3 columns per member (Spent, Paid, Balance)
- Color-code balances based on positive/negative/zero
- Show explanatory text for each balance state
- Changed section title from "Spending by Member" to "Member Breakdown"

## 💡 Use Cases

This enhancement helps answer:

1. **"Who owes what?"** - Quickly see negative balances
2. **"Who is owed money?"** - Quickly see positive balances  
3. **"Who paid for receipts?"** - See the "Paid" column
4. **"Who consumed what?"** - See the "Spent" column
5. **"Is everyone settled?"** - Look for zero balances

## 📊 Example Scenarios

### Scenario 1: Someone paid for everyone
```
Alice
Spent: $20.00
Paid: $80.00
Balance: +$60.00
✓ Owed $60.00 by others
```

### Scenario 2: Someone owes money
```
Bob
Spent: $50.00
Paid: $30.00
Balance: -$20.00
↓ Owes $20.00
```

### Scenario 3: All settled
```
Charlie
Spent: $40.00
Paid: $40.00
Balance: $0.00
✓ All settled up
```

## 🎯 Files Modified

### Backend (1 file)
- `/backend/app/services/stats_service.py` - Added payment tracking and balance calculation

### Frontend (1 file)
- `/frontend/src/app/groups/[id]/stats/page.tsx` - Enhanced UI to show paid/owed/balance

## ✨ Benefits

1. **Complete financial visibility** - See the full picture, not just spending
2. **Easy settlement tracking** - Know who owes whom at a glance
3. **Fair tracking** - Distinguish between consumption and payment
4. **Period-specific** - Works with all time periods (24h, 30 days, 1 year)
5. **Multi-currency aware** - All amounts converted to base currency

---

**Status**: ✅ Feature complete and ready to use!
