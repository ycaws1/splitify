# ✅ Supabase Storage - Setup Complete!

The storage bucket **"receipts"** has been successfully created!

## What Was Set Up

✅ **Bucket Created**: `receipts`  
✅ **Public Access**: Enabled (images are publicly accessible via URL)  
✅ **File Size Limit**: 10 MB maximum  
✅ **Allowed File Types**: JPEG, PNG, WebP, HEIC images  

## ⚠️ Important: Storage Policies Required

The bucket exists, but you need to configure **storage policies** manually in your Supabase Dashboard to allow uploads:

### Required Policies

Go to: **Supabase Dashboard > Storage > Policies**  
Create these 3 policies for the 'receipts' bucket:

#### 1. Allow Public Reads
```
Operation: SELECT
Policy name: Allow public read access
Policy definition: bucket_id = 'receipts'
```

#### 2. Allow Authenticated Uploads  
```
Operation: INSERT
Policy name: Allow authenticated uploads
Policy definition: bucket_id = 'receipts' AND auth.role() = 'authenticated'
```

#### 3. Allow Authenticated Deletes
```
Operation: DELETE
Policy name: Allow authenticated deletes
Policy definition: bucket_id = 'receipts' AND auth.role() = 'authenticated'
```

## How to Access Supabase Dashboard

1. Go to: https://supabase.com/dashboard
2. Select your project: `tthsmlircdieqddkjgxk`
3. Navigate to: **Storage** > **Policies**
4. Click **"New Policy"** and configure each of the 3 policies above

## Testing

After setting up the policies:

1. Open your app
2. Navigate to a group
3. Click "Add Receipt" > "Upload Photo"
4. Take a photo or select an image
5. The "Bucket not found" error should be gone!

## Re-Running Setup

If you need to re-run the setup script:

```bash
cd backend
python setup_storage.py
```

The script will detect if the bucket already exists and skip recreation.

## Troubleshooting

### Still seeing "Bucket not found"?
- The bucket exists, but policies might be missing
- Follow the "Storage Policies Required" section above

### Upload fails with permission error?
- Check that all 3 storage policies are created
- Verify the user is logged in (authenticated)

### Files not accessible?
- Ensure "Allow public read access" policy is configured
- Verify bucket is set to public

---

**Last Updated**: Automatically created by setup_storage.py
