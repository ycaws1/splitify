# Storage Setup Guide

## Automatic Setup (Recommended)

The easiest way to set up the Supabase storage bucket is to run the automated setup script:

```bash
cd backend
python setup_storage.py
```

This script will:
- ✅ Create the 'receipts' storage bucket
- ✅ Configure it for public access
- ✅ Set file size limits (10 MB max)
- ✅ Restrict to image file types only
- ✅ Verify the setup

## Manual Setup (Alternative)

If the automated script doesn't work, follow these steps in your Supabase Dashboard:

1. Navigate to **Storage** section
2. Click **"New bucket"**
3. Configure the bucket:
   - **Name**: `receipts`
   - **Public bucket**: ✅ Enabled
   - **File size limit**: `10485760` (10 MB)
   - **Allowed MIME types**: 
     - `image/jpeg`
     - `image/jpg`
     - `image/png`
     - `image/webp`
     - `image/heic`
4. Click **"Save"**

### Storage Policies

After creating the bucket, set up these RLS policies:

**Policy 1: Allow Public Reads**
- Target: `SELECT`
- Policy name: `Allow public read access`
- Definition: 
  ```sql
  bucket_id = 'receipts'
  ```

**Policy 2: Allow Authenticated Uploads**
- Target: `INSERT`
- Policy name: `Allow authenticated uploads`
- Definition:
  ```sql
  bucket_id = 'receipts' AND auth.role() = 'authenticated'
  ```

**Policy 3: Allow Authenticated Deletes**
- Target: `DELETE`
- Policy name: `Allow authenticated deletes`  
- Definition:
  ```sql
  bucket_id = 'receipts' AND auth.role() = 'authenticated'
  ```

## Verification

After setup, verify by:

1. Trying to upload a receipt photo in the app
2. The error "Bucket not found" should not appear
3. You should see the upload progress

## Troubleshooting

### "Bucket not found" error persists
- Run `python setup_storage.py` to verify setup
- Check Supabase Dashboard > Storage to confirm bucket exists
- Verify bucket name is exactly `receipts` (case-sensitive)

### Upload fails with permission error
- Check storage policies are correctly configured
- Ensure user is authenticated before uploading
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`

### File size limit errors
- Images larger than 10 MB will be rejected
- Consider compressing images on the frontend before upload
- Adjust file size limit in bucket settings if needed

## Integration with Alembic

To run storage setup automatically with database migrations, you can add it to your deployment script:

```bash
#!/bin/bash
# deploy.sh

# Run database migrations
alembic upgrade head

# Setup storage
python setup_storage.py

# Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
