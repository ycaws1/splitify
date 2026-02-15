# Gemini Model Quota Limits

## ⚠️ Important: Free Tier Quota Differences

Different Gemini models have **very different** free tier quotas!

### Gemini Free Tier Comparison

| Model | Requests Per Day | Requests Per Minute | Best For |
|-------|------------------|---------------------|----------|
| **gemini-1.5-flash** ✅ | **1,500** | 15 | **Production use** |
| gemini-2.5-flash | 20 | 2 | Testing only |
| gemini-1.5-pro | 50 | 2 | High-quality tasks |
| gemini-2.0-flash-exp | Varies | Varies | Experimental |

### What Happened?

You hit the quota limit for `gemini-2.5-flash`:
- ❌ **Only 20 requests per day**
- ❌ **You've used all 20** (testing multiple models)
- ⏰ **Resets in 24 hours**

### Current Setting: ✅ gemini-1.5-flash

**Why This Model?**
- ✅ **1,500 requests per day** - Perfect for development
- ✅ **15 requests per minute** - Fast enough
- ✅ **Excellent vision capabilities** - Great for OCR
- ✅ **Stable and tested** - Not experimental
- ✅ **FREE** - No billing required

### When to Use Other Models

**gemini-1.5-pro**:
- Need highest accuracy
- Only 50 requests/day limit
- Slower but more accurate

**gemini-2.5-flash**:
- Latest features
- Only 20/day limit - **not practical**
- Wait until quota increases

**gemini-2.0-flash-exp**:
- Testing new features
- Experimental/unstable
- Quotas may change

---

## 💡 Recommendation

**Stick with `gemini-1.5-flash`** for your receipt OCR:
- Proven to work well
- High quotas
- Fast responses
- Perfect balance

---

## How to Monitor Usage

Visit: https://ai.dev/rate-limit

You can see:
- Current usage for each model
- Remaining quota
- When it resets

---

## Current Status

✅ **Model**: `gemini-1.5-flash`
✅ **Quota**: 1,500 requests/day
✅ **Status**: Ready to use!

Try uploading a receipt now - it should work! 🎯
