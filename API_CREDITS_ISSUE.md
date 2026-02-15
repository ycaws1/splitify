# Anthropic API Credits Issue

## ❌ Current Problem

```
Error code: 400 - Your credit balance is too low to access the Anthropic API. 
Please go to Plans & Billing to upgrade or purchase credits.
```

The Anthropic API key in your `.env` file has **run out of credits**.

## ✅ Solutions

### Option 1: Add Credits to Existing API Key (Recommended)

1. Go to: https://console.anthropic.com/settings/billing
2. Log in with the account associated with this API key:
   - Key starts with: `sk-ant-api03-4IPKRN1ff...`
3. Click **"Add Credits"** or **"Purchase Credits"**
4. Add at least $5-10 for testing
5. No code changes needed - just works immediately!

### Option 2: Use a Different API Key

If you have another Anthropic account with credits:

1. Get your API key from: https://console.anthropic.com/settings/keys
2. Copy the key (starts with `sk-ant-api03-...`)
3. Update `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR-NEW-KEY-HERE
   ```
4. Restart the backend server

### Option 3: Disable AI OCR (Manual Entry Only)

If you don't want to pay for OCR right now:

**Temporary workaround** - Comment out the background task:

Edit `/backend/app/api/receipts.py` line 44:
```python
# background_tasks.add_task(process_receipt_ocr, receipt.id)  # Disabled - no credits
```

**Impact**:
- ❌ Photo upload won't extract items automatically
- ✅ Manual entry still works perfectly
- ✅ No API costs

## Cost Information

**Anthropic Claude Pricing**:
- **Claude Sonnet 4**: ~$3 per 1M input tokens, ~$15 per 1M  output tokens
- **Typical receipt**: ~500 tokens input (image) + ~200 tokens output (JSON) = **~$0.01 per receipt**
- **$10 credit** = ~1000 receipt scans

**Very affordable** for personal use!

## What I Fixed

### 1. Added `failed` Status
**File**: `/backend/app/models/receipt.py`

Added `failed` status to `ReceiptStatus` enum so receipts that fail OCR show "Failed" instead of being stuck on "Processing".

**Before**:
```python
class ReceiptStatus(str, enum.Enum):
    processing = "processing"
    extracted = "extracted"
    confirmed = "confirmed"
```

**After**:
```python
class ReceiptStatus(str, enum.Enum):
    processing = "processing"
    extracted = "extracted"
    confirmed = "confirmed"
    failed = "failed"  # NEW
```

### 2. Better Error Logging (Already Done)
The error now shows clearly in logs:
```
ERROR: OCR processing failed for receipt <id>: Error code: 400 - 
{'type': 'error', 'error': {'message': 'Your credit balance is too low...'}}
```

## Testing After Fix

Once you add credits:

1. **Try uploading a new receipt**
2. Check logs - should see:
   ```
   INFO: Starting OCR for receipt...
   INFO: Fetched exchange rate: 1 MYR = 0.303 SGD
   INFO: Successfully processed receipt...
   ```
3. Receipt should extract automatically! ✅

## Current Status

- ✅ **Storage**: Working (bucket + policies created)
- ✅ **Upload**: Working (photo uploads successfully)
- ✅ **Exchange rates**: Fixed (auto-fetches real rates)
- ✅ **Error handling**: Fixed (shows "failed" status)
- ❌ **AI OCR**: Blocked (need API credits)

---

**Next Step**: Add credits to your Anthropic account or use manual entry for now!

**Estimated Cost**: $10 = ~1000 receipt scans (very affordable)
