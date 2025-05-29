#!/usr/bin/env python3
"""
Complete Order Line Items Import - Clear and import all order_line_items
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

def export_all_order_line_items():
    """Export all order_line_items from local database"""
    print("📤 Exporting all order_line_items from local database...")
    
    export_dir = Path("complete_export")
    export_dir.mkdir(exist_ok=True)
    export_file = export_dir / "all_order_line_items.csv"
    
    copy_query = """
    COPY (
        SELECT * FROM order_line_items
        ORDER BY order_id, uid
    ) TO STDOUT WITH CSV HEADER;
    """
    
    try:
        with open(export_file, 'w') as f:
            result = subprocess.run(
                f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=600
            )
        
        if result.returncode == 0 and os.path.getsize(export_file) > 10:
            print(f"✅ All order_line_items exported ({os.path.getsize(export_file) / (1024*1024):.1f} MB)")
            return export_file
        else:
            print(f"❌ Export failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Export error: {e}")
        return None

def import_all_order_line_items(export_file):
    """Import all order_line_items to production"""
    print("📥 Importing all order_line_items to production...")
    
    copy_query = "COPY order_line_items FROM STDIN WITH CSV HEADER;"
    
    try:
        with open(export_file, 'r') as f:
            result = subprocess.run(
                f'psql "{PROXY_DB_URL}" -c "{copy_query}"',
                shell=True, stdin=f, capture_output=True, text=True, timeout=1200
            )
        
        if result.returncode == 0:
            print("✅ All order_line_items imported successfully")
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
        
        # Count in local
        local_result = subprocess.run(
            f'psql "{LOCAL_DB_URL}" -c "SELECT COUNT(*) FROM order_line_items;" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if prod_result.returncode == 0 and local_result.returncode == 0:
            prod_count = int(prod_result.stdout.strip())
            local_count = int(local_result.stdout.strip())
            
            print(f"📊 Production: {prod_count:,} order_line_items")
            print(f"📊 Local: {local_count:,} order_line_items")
            
            if prod_count == local_count:
                print("🎉 PERFECT MATCH - Import successful!")
                return True
            else:
                print(f"⚠️ Mismatch - {local_count - prod_count:,} missing")
                return False
        else:
            print("❌ Could not verify counts")
            return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    print("🎯 COMPLETE ORDER LINE ITEMS IMPORT")
    print("=" * 50)
    print("Strategy: Clear production table and import all data fresh")
    
    # Ensure proxy is running
    if not ensure_proxy_running():
        return False
    
    # Clear production table
    if not clear_order_line_items():
        return False
    
    # Export all data
    export_file = export_all_order_line_items()
    if not export_file:
        return False
    
    # Import all data
    success = import_all_order_line_items(export_file)
    
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
            print("\n🎉 COMPLETE ORDER LINE ITEMS IMPORT SUCCESSFUL!")
            print("🔄 Production database now has complete order line items data")
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
        print("Production database contains complete order history with line items")
    else:
        print("\n❌ Import had issues - check output above") 