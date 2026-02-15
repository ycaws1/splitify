"""
Supabase Storage Policies Setup Script

This script automatically creates RLS policies for the receipts storage bucket.
Run this after creating the storage bucket to enable uploads.

Usage:
    python setup_policies.py
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


def execute_sql(sql: str) -> bool:
    """Execute SQL using Supabase REST API with service role"""
    # Use PostgREST RPC to execute SQL
    # Note: This requires a custom RPC function in Supabase
    
    # Alternative: Use the pg-meta API endpoint
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(
                url,
                headers=headers,
                json={"query": sql},
                timeout=10.0
            )
            
            if response.status_code in [200, 201, 204]:
                return True
            else:
                print(f"   HTTP {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"   Error: {e}")
        return False


def create_policies_via_postgrest():
    """Create storage policies using direct PostgreSQL commands via PostgREST"""
    
    print("Setting up storage policies for 'receipts' bucket...")
    print()
    
    # Since we can't modify storage.objects directly, we'll use a different approach
    # We'll create the policies using the postgres connection string
    
    from sqlalchemy import create_engine, text
    
    # Get the direct database URL (not the pooler)
    db_url = os.getenv("DIRECT_DATABASE_URL")
    if not db_url:
        print("⚠️  DIRECT_DATABASE_URL not found in .env")
        print("   Using DATABASE_URL instead...")
        db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise ValueError("No database URL found in .env")
    
    # Convert asyncpg URL to psycopg2 for synchronous execution
    sync_db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        print("Connecting to database...")
        engine = create_engine(sync_db_url)
        
        success_count = 0
        total_policies = 4
        
        with engine.connect() as conn:
            # Enable RLS on storage.objects
            print("1. Enabling Row Level Security...")
            try:
                conn.execute(text("ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;"))
                conn.commit()
                print("   ✓ RLS enabled")
            except Exception as e:
                if "already has row level security enabled" in str(e).lower():
                    print("   ✓ RLS already enabled")
                elif "must be owner" in str(e).lower():
                    print("   ℹ RLS requires superuser (skipping - may already be enabled)")
                else:
                    print(f"   ⚠️  {e}")
            
            # Policy 1: Public reads
            print("\n2. Creating policy: Public Access...")
            try:
                # Try without IF NOT EXISTS first
                conn.execute(text("""
                    CREATE POLICY "Public Access to Receipts"
                    ON storage.objects FOR SELECT
                    TO public
                    USING (bucket_id = 'receipts');
                """))
                conn.commit()
                print("   ✓ Public read access enabled")
                success_count += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ✓ Policy already exists")
                    success_count += 1
                else:
                    print(f"   ✗ Failed: {e}")
            
            # Policy 2: Authenticated uploads
            print("\n3. Creating policy: Authenticated Uploads...")
            try:
                conn.execute(text("""
                    CREATE POLICY "Authenticated Upload to Receipts"
                    ON storage.objects FOR INSERT
                    TO authenticated
                    WITH CHECK (bucket_id = 'receipts');
                """))
                conn.commit()
                print("   ✓ Authenticated upload access enabled")
                success_count += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ✓ Policy already exists")
                    success_count += 1
                else:
                    print(f"   ✗ Failed: {e}")
            
            # Policy 3: Authenticated updates
            print("\n4. Creating policy: Authenticated Updates...")
            try:
                conn.execute(text("""
                    CREATE POLICY "Authenticated Update Receipts"
                    ON storage.objects FOR UPDATE
                    TO authenticated
                    USING (bucket_id = 'receipts');
                """))
                conn.commit()
                print("   ✓ Authenticated update access enabled")
                success_count += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ✓ Policy already exists")
                    success_count += 1
                else:
                    print(f"   ✗ Failed: {e}")
            
            # Policy 4: Authenticated deletes
            print("\n5. Creating policy: Authenticated Deletes...")
            try:
                conn.execute(text("""
                    CREATE POLICY "Authenticated Delete Receipts"
                    ON storage.objects FOR DELETE
                    TO authenticated
                    USING (bucket_id = 'receipts');
                """))
                conn.commit()
                print("   ✓ Authenticated delete access enabled")
                success_count += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ✓ Policy already exists")
                    success_count += 1
                else:
                    print(f"   ✗ Failed: {e}")
        
        print(f"\n✅ Policy setup completed! ({success_count}/{total_policies} policies active)")
        return success_count >= total_policies
        
    except Exception as e:
        print(f"\n❌ Failed to create policies: {e}")
        print("\nThis error usually means:")
        print("- The database user doesn't have SUPERUSER privileges")
        print("- The storage.objects table is owned by the postgres superuser")
        print("\nYou'll need to use the Supabase Dashboard UI instead.")
        return False


def main():
    """Main setup function"""
    print("="*60)
    print("SPLITIFY - STORAGE POLICIES SETUP")
    print("="*60)
    print()
    
    try:
        # Check if psycopg2 is installed
        try:
            import psycopg2
        except ImportError:
            print("⚠️  psycopg2 not installed. Installing...")
            import subprocess
            subprocess.check_call(["pip", "install", "psycopg2-binary"])
            print("✓ Installed psycopg2-binary")
            print()
        
        success = create_policies_via_postgrest()
        
        if success:
            print("\n" + "="*60)
            print("🎉 SUCCESS!")
            print("="*60)
            print("\nYou can now:")
            print("✅ Upload receipt photos in the app")
            print("✅ Images will be publicly accessible")
            print("✅ Only authenticated users can upload/delete")
            print("\nTest it:")
            print("1. Refresh your app")
            print("2. Go to any group")
            print("3. Click 'Add Receipt' > 'Upload Photo'")
            print("4. It should work!")
            return 0
        else:
            raise Exception("Policy creation failed - see errors above")
            
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\n" + "="*60)
        print("MANUAL SETUP REQUIRED")
        print("="*60)
        print("\nPlease use the Supabase Dashboard UI:")
        print("\n1. Go to: https://supabase.com/dashboard/project/tthsmlircdieqddkjgxk/storage/policies")
        print("\n2. Create 4 policies with expression: bucket_id = 'receipts'")
        print("   - SELECT for public")
        print("   - INSERT for authenticated")
        print("   - UPDATE for authenticated")
        print("   - DELETE for authenticated")
        print("\nSee FIX_RLS_ERROR.md for detailed instructions")
        return 1


if __name__ == "__main__":
    exit(main())
