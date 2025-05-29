#!/usr/bin/env python3
"""
Deduplicated Order Line Items Import - Export unique order_line_items only
"""
import subprocess
import time
import os
from pathlib import Path

# Production database details
CLOUD_SQL_CONNECTION_NAME = "nytex-business-systems:us-central1:nytex-main-db"
LOCAL_PROXY_PORT = 5433
PROXY_DB_URL = f"postgresql://nytex_user:NytexSecure2024!@localhost:{LOCAL_PROXY_PORT}/nytex_dashboard"
LOCAL_DB_URL = "postgresql://joshgoble:@localhost:5432/square_data_sync"

def ensure_proxy_running():
    """Make sure Cloud SQL Proxy is running"""
    check_running = subprocess.run(f"lsof -ti:{LOCAL_PROXY_PORT}", shell=True, capture_output=True)
    if check_running.returncode == 0:
        print(f"✅ Cloud SQL Proxy already running")
        return True
    
    print("🔌 Starting Cloud SQL Proxy...")
    proxy_cmd = f"cloud_sql_proxy -instances={CLOUD_SQL_CONNECTION_NAME}=tcp:{LOCAL_PROXY_PORT}"
    
    try:
        subprocess.Popen(
            proxy_cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        time.sleep(3)
        print("✅ Cloud SQL Proxy started")
        return True
    except Exception as e:
        print(f"❌ Failed to start proxy: {e}")
        return False

def analyze_duplicates():
    """Analyze the duplicate situation"""
    print("🔍 Analyzing duplicate UIDs...")
    
    try:
        result = subprocess.run(
            f'psql "{LOCAL_DB_URL}" -c "SELECT COUNT(*) as total_records, COUNT(DISTINCT uid) as unique_uids, COUNT(*) - COUNT(DISTINCT uid) as duplicates FROM order_line_items;" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            parts = result.stdout.strip().split('|')
            total = int(parts[0].strip())
            unique = int(parts[1].strip())
            duplicates = int(parts[2].strip())
            
            print(f"📊 Total records: {total:,}")
            print(f"📊 Unique UIDs: {unique:,}")
            print(f"📊 Duplicates: {duplicates:,}")
            
            return total, unique, duplicates
        else:
            print(f"❌ Error: {result.stderr}")
            return None, None, None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None, None, None

def clear_order_line_items():
    """Clear all order_line_items from production"""
    print("🗑️ Clearing order_line_items table in production...")
    
    try:
        result = subprocess.run(
            f'psql "{PROXY_DB_URL}" -c "TRUNCATE TABLE order_line_items CASCADE;"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Order_line_items table cleared")
            return True
        else:
            print(f"❌ Failed to clear table: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error clearing table: {e}")
        return False

def export_unique_order_line_items():
    """Export unique order_line_items from local database (deduplicating on uid)"""
    print("📤 Exporting unique order_line_items (removing duplicates)...")
    
    export_dir = Path("deduplicated_export")
    export_dir.mkdir(exist_ok=True)
    export_file = export_dir / "unique_order_line_items.csv"
    
    # Use DISTINCT ON to get unique records by uid, keeping the first occurrence
    copy_query = """
    COPY (
        SELECT DISTINCT ON (uid) *
        FROM order_line_items
        ORDER BY uid, order_id
    ) TO STDOUT WITH CSV HEADER;
    """
    
    try:
        with open(export_file, 'w') as f:
            result = subprocess.run(
                f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=600
            )
        
        if result.returncode == 0 and os.path.getsize(export_file) > 10:
            print(f"✅ Unique order_line_items exported ({os.path.getsize(export_file) / (1024*1024):.1f} MB)")
            
            # Count lines to verify
            with open(export_file, 'r') as f:
                line_count = sum(1 for line in f) - 1  # Subtract header
            print(f"📊 Exported {line_count:,} unique records")
            
            return export_file
        else:
            print(f"❌ Export failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Export error: {e}")
        return None

def import_unique_order_line_items(export_file):
    """Import unique order_line_items to production"""
    print("📥 Importing unique order_line_items to production...")
    
    copy_query = "COPY order_line_items FROM STDIN WITH CSV HEADER;"
    
    try:
        with open(export_file, 'r') as f:
            result = subprocess.run(
                f'psql "{PROXY_DB_URL}" -c "{copy_query}"',
                shell=True, stdin=f, capture_output=True, text=True, timeout=1200
            )
        
        if result.returncode == 0:
            print("✅ Unique order_line_items imported successfully")
            return True
        else:
            print(f"❌ Import failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def verify_import():
    """Verify the import was successful"""
    print("🔍 Verifying import...")
    
    try:
        # Count in production
        prod_result = subprocess.run(
            f'psql "{PROXY_DB_URL}" -c "SELECT COUNT(*) FROM order_line_items;" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        # Count unique in local for comparison
        local_result = subprocess.run(
            f'psql "{LOCAL_DB_URL}" -c "SELECT COUNT(DISTINCT uid) FROM order_line_items;" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if prod_result.returncode == 0 and local_result.returncode == 0:
            prod_count = int(prod_result.stdout.strip())
            local_unique_count = int(local_result.stdout.strip())
            
            print(f"📊 Production: {prod_count:,} order_line_items")
            print(f"📊 Local unique: {local_unique_count:,} order_line_items")
            
            if prod_count == local_unique_count:
                print("🎉 PERFECT MATCH - Import successful!")
                return True
            else:
                print(f"⚠️ Mismatch - {local_unique_count - prod_count:,} difference")
                return False
        else:
            print("❌ Could not verify counts")
            return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    print("🎯 DEDUPLICATED ORDER LINE ITEMS IMPORT")
    print("=" * 50)
    print("Strategy: Export unique records only and import to production")
    
    # Ensure proxy is running
    if not ensure_proxy_running():
        return False
    
    # Analyze duplicates
    total, unique, duplicates = analyze_duplicates()
    if total is None:
        return False
    
    print(f"\n⚠️ Found {duplicates:,} duplicate records")
    print(f"✅ Will import {unique:,} unique records")
    
    # Clear production table
    if not clear_order_line_items():
        return False
    
    # Export unique data
    export_file = export_unique_order_line_items()
    if not export_file:
        return False
    
    # Import unique data
    success = import_unique_order_line_items(export_file)
    
    # Clean up
    try:
        os.remove(export_file)
        export_file.parent.rmdir()
    except:
        pass
    
    if success:
        # Verify
        verify_success = verify_import()
        
        if verify_success:
            print("\n🎉 DEDUPLICATED ORDER LINE ITEMS IMPORT SUCCESSFUL!")
            print("🔄 Production database now has unique order line items data")
            print(f"📊 Removed {duplicates:,} duplicate records during import")
            return True
        else:
            print("\n⚠️ Import completed but verification shows issues")
            return False
    else:
        print("\n❌ Import failed")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n✅ ALL ORDER DATA IS NOW SYNCHRONIZED!")
        print("Production database contains complete and clean order history")
    else:
        print("\n❌ Import had issues - check output above") 