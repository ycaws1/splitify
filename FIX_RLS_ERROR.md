# Fix Storage Upload Error - UI Method

## ⚠️ SQL Editor Won't Work

The SQL Editor gives a permission error because the `storage.objects` table is owned by Supabase's internal `postgres` user. 

**Solution**: Use the Storage Policies UI instead (it has the right permissions).

---

## ✅ Correct Method: Storage Policies UI

### Step 1: Navigate to Storage Policies

1. Go to: https://supabase.com/dashboard/project/tthsmlircdieqddkjgxk
2. Click **"Storage"** in the left sidebar
3. Click **"Policies"** tab (near the top)
4. You should see the `storage.objects` table

### Step 2: Create Policy Templates

Supabase provides templates for common storage policies. Let's use them:

1. Click **"New Policy"** button
2. You'll see policy templates - click **"Get started quickly"**
3. Choose these templates:

---

### Policy 1: Public Read Access

1. Click **"New Policy"**
2. Select template: **"Allow public read access"** or create custom:
   - **Policy name**: `Public Access to Receipts`
   - **Allowed operation**: `SELECT`
   - **Target roles**: `public`
   - **USING expression**: 
     ```sql
     bucket_id = 'receipts'
     ```
3. Click **"Review"** then **"Save policy"**

---

### Policy 2: Authenticated Upload

1. Click **"New Policy"**
2. Select template: **"Allow authenticated uploads"** or create custom:
   - **Policy name**: `Authenticated Upload to Receipts`
   - **Allowed operation**: `INSERT`
   - **Target roles**: `authenticated`
   - **WITH CHECK expression**:
     ```sql
     bucket_id = 'receipts'
     ```
3. Click **"Review"** then **"Save policy"**

---

### Policy 3: Authenticated Update

1. Click **"New Policy"**
2. Create custom policy:
   - **Policy name**: `Authenticated Update Receipts`
   - **Allowed operation**: `UPDATE`
   - **Target roles**: `authenticated`
   - **USING expression**:
     ```sql
     bucket_id = 'receipts'
     ```
3. Click **"Review"** then **"Save policy"**

---

### Policy 4: Authenticated Delete

1. Click **"New Policy"**
2. Select template: **"Allow authenticated deletes"** or create custom:
   - **Policy name**: `Authenticated Delete Receipts`
   - **Allowed operation**: `DELETE`
   - **Target roles**: `authenticated`
   - **USING expression**:
     ```sql
     bucket_id = 'receipts'
     ```
3. Click **"Review"** then **"Save policy"**

---

## Quick Summary

You need to create **4 policies** on `storage.objects`:

| # | Operation | Role | Expression |
|---|-----------|------|------------|
| 1 | SELECT | public | `bucket_id = 'receipts'` |
| 2 | INSERT | authenticated | `bucket_id = 'receipts'` |
| 3 | UPDATE | authenticated | `bucket_id = 'receipts'` |
| 4 | DELETE | authenticated | `bucket_id = 'receipts'` |

All expressions are the same: just `bucket_id = 'receipts'`

---

## After Creating Policies

✅ Refresh your app  
✅ Try uploading a receipt photo  
✅ Should work without errors!  
✅ AI will extract items automatically  

---

## Visual Guide

When creating a policy, you'll see a form like:

```
Policy name: [Authenticated Upload to Receipts]

Allowed operation: [INSERT ▼]

Target roles: [authenticated ▼]

USING expression:
┌────────────────────────────────┐
│ bucket_id = 'receipts'         │
└────────────────────────────────┘

WITH CHECK expression:
┌────────────────────────────────┐
│ bucket_id = 'receipts'         │
└────────────────────────────────┘

[Review] [Save policy]
```

---

**Estimated Time**: 3-5 minutes total  
**Difficulty**: Easy - just fill in 4 forms with the same expression  

🎯 **Direct Link**: https://supabase.com/dashboard/project/tthsmlircdieqddkjgxk/storage/policies
