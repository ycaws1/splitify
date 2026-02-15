# Storage Setup Progress

## ✅ Completed Steps

1. **Storage Bucket Created** ✓
   - Bucket name: `receipts`
   - Public access: Enabled
   - File size limit: 10 MB
   - Allowed types: Images (JPEG, PNG, WebP, HEIC)

2. **Setup Script Created** ✓
   - Location: `backend/setup_storage.py`
   - Can be run anytime to verify/create bucket
   - Usage: `python setup_storage.py`

## ⚠️ Next Step Required

### Fix: "new row violates row-level security policy"

**Problem**: The storage bucket exists, but Row Level Security (RLS) policies are blocking uploads.

**Solution**: Run SQL commands in Supabase Dashboard

### 🚀 Quick Fix (2 minutes)

1. Open: https://supabase.com/dashboard
2. Select your project
3. Go to: **SQL Editor** > **New query**
4. Copy & paste this SQL:

```sql
-- Enable RLS
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Allow public reads
CREATE POLICY "Public Access to Receipts"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'receipts');

-- Allow authenticated uploads
CREATE POLICY "Authenticated Upload to Receipts"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'receipts');

-- Allow authenticated updates
CREATE POLICY "Authenticated Update Receipts"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'receipts');

-- Allow authenticated deletes
CREATE POLICY "Authenticated Delete Receipts"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'receipts');
```

5. Click **"Run"** (or press `Cmd + Enter`)
6. Should see: `Success. No rows returned`

### After Running SQL

✅ Receipt uploads will work  
✅ No more RLS errors  
✅ Images publicly accessible  
✅ Only authenticated users can upload/delete  

## Why Migration Didn't Work

Alembic migrations can't modify the `storage.objects` table because:
- It's owned by Supabase's internal system
- Your database user doesn't have ownership permissions
- RLS policies must be managed through Supabase Dashboard or SQL Editor

## Files Created

- ✅ `backend/setup_storage.py` - Bucket setup script
- ✅ `STORAGE_SETUP.md` - General setup guide
- ✅ `STORAGE_COMPLETE.md` - Bucket creation confirmation
- ✅ `FIX_RLS_ERROR.md` - Detailed policy setup instructions
- ✅ This file - Progress tracker

## Testing After Setup

1. Refresh your app
2. Navigate to any group
3. Click "Add Receipt" > "Upload Photo"
4. Select/capture an image
5. Should upload successfully!
6. AI will extract receipt items automatically

---

**Status**: Bucket ✅ | Policies ⚠️ (requires SQL command above)  
**Estimated Time to Fix**: 2 minutes  
**See**: `FIX_RLS_ERROR.md` for detailed instructions
