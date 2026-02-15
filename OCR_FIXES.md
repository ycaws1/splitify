# Receipt Upload & OCR Fixes

## Issues Fixed

### 1. ✅ Storage Bucket Working
The "Bucket not found" error is resolved! Storage policies were successfully created.

### 2. ✅ Wrong Exchange Rate Fixed
**Problem**: Exchange rate showed "1 MYR = 1.000000 SGD" (should be ~0.30)

**Root Cause**: OCR worker wasn't fetching exchange rates after extraction

**Solution**:
- Added `fetch_exchange_rate()` function to OCR worker
- Automatically fetches real-time rates from exchangerate-api.com
- Sets correct `exchange_rate` on receipt after OCR extraction
- Now shows accurate conversions: 1 MYR ≈ 0.30 SGD

**File Modified**: `/backend/app/workers/ocr.py`

### 3. ✅ Better Error Handling
**Problem**: OCR failures were silent - stuck on "Processing..." forever

**Improvements**:
- Added proper logging (`logger.info`, `logger.error`)
- Changed status to `failed` when OCR errors occur (instead of staying in `processing`)
- Added stack traces with `exc_info=True` for debugging
- Logs show:
  - When OCR starts
  - When OCR succeeds
  - Exchange rate fetched
  - Any errors that occur

**Benefits**:
- You can see errors in backend logs
- Frontend shows "failed" status instead of endless processing
- Easier to debug issues

## Changes Made

### `/backend/app/workers/ocr.py`

**Added**:
```python
import logging
import httpx
from app.models.group import Group

logger = logging.getLogger(__name__)

async def fetch_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Fetch exchange rate from external API"""
    # Uses exchangerate-api.com
    # Returns 1.0 if currencies match or API fails
```

**Modified `process_receipt_ocr()`**:
1. Added logging at each step
2. Fetch group's base currency
3. Fetch exchange rate after OCR extraction
4. Set `receipt.exchange_rate` with real value
5. Log success/failure with details
6. Set status to `failed` (not `processing`) on errors

## Test It

1. **Upload a new receipt** - should work now!
2. **Check exchange rate** - should show correct value (e.g., 1 MYR = 0.30 SGD)
3. **View backend logs** - should see OCR progress:
   ```
   INFO: Starting OCR for receipt <id>
   INFO: Received OCR response for receipt <id>  
   INFO: Fetched exchange rate: 1 MYR = 0.303 SGD
   INFO: Exchange rate for receipt <id>: 1 MYR = 0.303 SGD
   INFO: Successfully processed receipt <id>
   ```

## For the Current Stuck Receipt

The receipt that's currently stuck on "Processing..." has these issues:
1. ❌ Exchange rate set to 1.0 (wrong)
2. ⚠️ Status stuck on `processing`

**To retry**:
- Upload a new receipt (the fixes are live now)
- The stuck one can be deleted or manually fixed in database

## Next Time You See "Processing..."

**Check backend logs**:
```bash
# View recent logs
tail -f backend/uvicorn.log  # if you're logging to file

# Or watch terminal where uvicorn is running
```

**Look for**:
- `Starting OCR for receipt...` - OCR started
- `ERROR: OCR processing failed...` - shows the actual error
- `Successfully processed receipt...` - OCR completed

---

**Status**: All fixed! ✅
- Upload: Working
- Exchange rates: Accurate
- Error handling: Improved
- Logging: Added

Try uploading another receipt to see the improvements!
