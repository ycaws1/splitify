"""
Supabase Storage Setup Script

This script automatically creates the necessary storage buckets for the Splitify app.
Run this after applying database migrations to ensure all infrastructure is ready.

Usage:
    python setup_storage.py
"""
import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env file")

# Sometimes the key is truncated - let's validate it looks correct
if len(SUPABASE_SERVICE_ROLE_KEY) < 30:
    print("⚠️  WARNING: SUPABASE_SERVICE_ROLE_KEY seems too short.")
    print("   Please copy the full key from your Supabase Dashboard:")
    print("   Settings > API > service_role key (secret)")
    print()


def create_receipts_bucket_http():
    """Create the 'receipts' storage bucket using HTTP API"""
    bucket_name = "receipts"
    
    print(f"Setting up storage bucket: {bucket_name}")
    print(f"Supabase URL: {SUPABASE_URL}")
    print()
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json"
    }
    
    # Storage API endpoint
    storage_url = f"{SUPABASE_URL}/storage/v1/bucket"
    
    try:
        # Check if bucket exists
        print("Checking existing buckets...")
        with httpx.Client() as client:
            response = client.get(storage_url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                buckets = response.json()
                existing = any(b.get("name") == bucket_name for b in buckets)
                
                if existing:
                    print(f"✓ Bucket '{bucket_name}' already exists!")
                    return True
            else:
                print(f"⚠️  Could not list buckets (HTTP {response.status_code})")
                print(f"   Response: {response.text}")
        
        # Create the bucket
        print(f"Creating bucket '{bucket_name}'...")
        bucket_config = {
            "id": bucket_name,
            "name": bucket_name,
            "public": True,  # Public access for receipts
            "file_size_limit": 10485760,  # 10 MB
            "allowed_mime_types": [
                "image/jpeg",
                "image/jpg",
                "image/png",
                "image/webp",
                "image/heic",
                "image/heif"
            ]
        }
        
        with httpx.Client() as client:
            response = client.post(
                storage_url,
                headers=headers,
                json=bucket_config,
                timeout=10.0
            )
            
            if response.status_code in [200, 201]:
                print(f"✓ Created bucket '{bucket_name}' successfully!")
                print(f"  - Public access: enabled")
                print(f"  - File size limit: 10 MB")
                print(f"  - Allowed types: JPEG, PNG, WebP, HEIC")
                return True
            else:
                print(f"✗ Failed to create bucket (HTTP {response.status_code})")
                print(f"   Response: {response.text}")
                
                if "already exists" in response.text.lower():
                    print(f"✓ Bucket '{bucket_name}' already exists!")
                    return True
                    
                return False
                
    except httpx.RequestError as e:
        print(f"✗ Connection error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def setup_storage_policies():
    """Set up RLS policies for storage bucket"""
    print("\n" + "="*60)
    print("STORAGE POLICIES")
    print("="*60)
    print()
    print("⚠️  Storage policies need to be configured manually:")
    print()
    print("1. Go to your Supabase Dashboard")
    print("2. Navigate to: Storage > Policies")
    print("3. Create these policies for the 'receipts' bucket:")
    print()
    print("   Policy 1: Allow Public Reads")
    print("   - Operation: SELECT")
    print("   - Policy definition: bucket_id = 'receipts'")
    print()
    print("   Policy 2: Allow Authenticated Uploads")
    print("   - Operation: INSERT")
    print("   - Policy definition: bucket_id = 'receipts' AND auth.role() = 'authenticated'")
    print()
    print("   Policy 3: Allow Authenticated Deletes")
    print("   - Operation: DELETE") 
    print("   - Policy definition: bucket_id = 'receipts' AND auth.role() = 'authenticated'")
    print()


def main():
    """Main setup function"""
    print("="*60)
    print("SPLITIFY - SUPABASE STORAGE SETUP")
    print("="*60)
    print()
    
    try:
        success = create_receipts_bucket_http()
        
        if success:
            print("\n✅ Storage bucket setup complete!")
            print()
            setup_storage_policies()
            print("\n🎉 You can now upload receipt images through the app!")
            return 0
        else:
            raise Exception("Failed to create storage bucket")
            
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\n" + "="*60)
        print("MANUAL SETUP INSTRUCTIONS")
        print("="*60)
        print()
        print("1. Go to your Supabase Dashboard")
        print(f"   URL: {SUPABASE_URL.replace('/rest/v1', '')}")
        print()
        print("2. Navigate to Storage section")
        print()
        print("3. Click 'New bucket' and configure:")
        print("   - Name: receipts")
        print("   - Public: ✅ Enabled")
        print("   - File size limit: 10485760 (10 MB)")
        print("   - Allowed MIME types: image/*")
        print()
        print("4. Click 'Save'")
        print()
        setup_storage_policies()
        return 1


if __name__ == "__main__":
    exit(main())
