# Backend Restart Required

## ❗ Action Needed

The backend uvicorn server needs to be **completely restarted** to clear cached environment variables.

### Why?

Python cached the old `ANTHROPIC_API_KEY` environment variable in memory. Even though we removed it from `.env`, the running process still has it.

### How to Fix:

**In the terminal running uvicorn:**

1. Press `Ctrl+C` to stop the server
2. Run again:
   ```bash
   uvicorn app.main:app --reload
   ```

The server should start successfully this time!

---

## ✅ What I Fixed

1. **Removed "failed" status** - It wasn't in the database enum yet, causing errors
   - Reverted to "processing" for failed OCR attempts
   - Removed from Python enum
   - Removed from frontend colors

2. **Environment variable issue** - Needs manual restart to clear cache

---

## After Restart

Once uvicorn restarts, you should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Then try uploading a receipt - Gemini OCR should work! 🎯

---

## If Still Getting anthrop ic_api_key Error

Make sure `.env` looks like this (no ANTHROPIC_API_KEY line):

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
DATABASE_URL=...
DIRECT_DATABASE_URL=...
GOOGLE_API_KEY=AIzaSyA3jkEYFHZI3VBwWKKUo3mh58LwjO4Z-MM  ✅
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_CLAIMS_EMAIL=
```

If the line is still there, remove it and restart again.
