#!/usr/bin/env python3
"""
Final Order Line Items Import - Import only missing order_line_items
"""
import subprocess
import time
import os
import sys
from pathlib import Path

# Production database details
CLOUD_SQL_CONNECTION_NAME = "nytex-business-systems:us-central1:nytex-main-db"
LOCAL_PROXY_PORT = 5433
PROXY_DB_URL = f"postgresql://nytex_user:NytexSecure2024!@localhost:{LOCAL_PROXY_PORT}/nytex_dashboard"
LOCAL_DB_URL = "postgresql://joshgoble:@localhost:5432/square_data_sync"

def start_cloud_sql_proxy():
    """Start Cloud SQL Proxy if not running"""
    print("🔌 Starting Cloud SQL Proxy...")
    
    check_running = subprocess.run(f"lsof -ti:{LOCAL_PROXY_PORT}", shell=True, capture_output=True)
    if check_running.returncode == 0:
        print(f"✅ Cloud SQL Proxy already running on port {LOCAL_PROXY_PORT}")
        return True
    
    proxy_cmd = f"cloud_sql_proxy -instances={CLOUD_SQL_CONNECTION_NAME}=tcp:{LOCAL_PROXY_PORT}"
    
    try:
        proxy_process = subprocess.Popen(
            proxy_cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        time.sleep(3)
        
        test_cmd = f'psql "{PROXY_DB_URL}" -c "SELECT 1;" --quiet'
        test_result = subprocess.run(test_cmd, shell=True, capture_output=True, timeout=10)
        
        if test_result.returncode == 0:
            print(f"✅ Cloud SQL Proxy started successfully")
            return proxy_process
        else:
            print(f"❌ Proxy connection test failed")
            return None
            
    except Exception as e:
        print(f"❌ Error starting proxy: {str(e)}")
        return None

def get_existing_order_line_items_in_production():
    """Get list of order_line_item UIDs that already exist in production"""
    print("🔍 Checking existing order_line_items in production...")
    
    try:
        result = subprocess.run(
            f'psql "{PROXY_DB_URL}" -c "SELECT uid FROM order_line_items;" -t',
            shell=True, capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            existing_uids = set()
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    existing_uids.add(line.strip())
            
            print(f"📊 Found {len(existing_uids)} existing order_line_items in production")
            return existing_uids
        else:
            print(f"❌ Error checking existing order_line_items: {result.stderr}")
            return set()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return set()

def get_missing_order_line_items():
    """Get order_line_items that don't exist in production"""
    print("📅 Analyzing missing order_line_items...")
    
    existing_uids = get_existing_order_line_items_in_production()
    
    # Get all order_line_items from local DB
    query = """
    SELECT 
        oli.uid,
        oli.order_id,
        o.created_at
    FROM order_line_items oli
    JOIN orders o ON oli.order_id = o.id
    ORDER BY o.created_at, oli.uid;
    """
    
    try:
        result = subprocess.run(
            f'psql "{LOCAL_DB_URL}" -c "{query}" -t',
            shell=True, capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            missing_uids = []
            total_checked = 0
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split('|')
                    if len(parts) >= 1:
                        uid = parts[0].strip()
                        total_checked += 1
                        
                        if uid not in existing_uids:
                            missing_uids.append(uid)
            
            print(f"📊 Missing order_line_items: {len(missing_uids):,} out of {total_checked:,} total")
            return missing_uids
        else:
            print(f"❌ Error getting missing order_line_items: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"❌ Error analyzing missing order_line_items: {str(e)}")
        return []

def export_missing_order_line_items(missing_uids, export_dir):
    """Export missing order_line_items"""
    if not missing_uids:
        return None
        
    export_file = export_dir / "missing_order_line_items.csv"
    
    # Split into chunks of 1000 to avoid command line length limits
    chunk_size = 1000
    chunks = [missing_uids[i:i + chunk_size] for i in range(0, len(missing_uids), chunk_size)]
    
    print(f"   🔄 Exporting {len(missing_uids):,} missing order_line_items in {len(chunks)} chunks...")
    
    try:
        # Export first chunk with header
        if chunks:
            first_chunk = chunks[0]
            uid_list = "', '".join(first_chunk)
            
            copy_query = f"""
            COPY (
                SELECT * FROM order_line_items
                WHERE uid IN ('{uid_list}')
                ORDER BY order_id, uid
            ) TO STDOUT WITH CSV HEADER;
            """
            
            with open(export_file, 'w') as f:
                result = subprocess.run(
                    f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                    shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
                )
                
                if result.returncode != 0:
                    print(f"   ❌ Failed to export first chunk: {result.stderr[:100]}")
                    return None
        
        # Export remaining chunks without header
        for i, chunk in enumerate(chunks[1:], 1):
            uid_list = "', '".join(chunk)
            
            copy_query = f"""
            COPY (
                SELECT * FROM order_line_items
                WHERE uid IN ('{uid_list}')
                ORDER BY order_id, uid
            ) TO STDOUT WITH CSV;
            """
            
            with open(export_file, 'a') as f:  # Append mode
                result = subprocess.run(
                    f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                    shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
                )
                
                if result.returncode != 0:
                    print(f"   ⚠️ Failed to export chunk {i}: {result.stderr[:100]}")
            
            if i % 10 == 0:
                print(f"      📦 Exported {i}/{len(chunks)-1} additional chunks")
        
        if os.path.exists(export_file) and os.path.getsize(export_file) > 10:
            print(f"   ✅ Missing order_line_items exported")
            return export_file
        else:
            print(f"   ❌ Export file is empty or missing")
            return None
            
    except Exception as e:
        print(f"   ❌ Error exporting order_line_items: {str(e)}")
        return None

def import_csv_file(csv_file, table_name):
    """Import a CSV file using COPY FROM"""
    print(f"📤 Importing missing order_line_items...")
    
    copy_query = f"COPY {table_name} FROM STDIN WITH CSV HEADER;"
    
    try:
        with open(csv_file, 'r') as f:
            result = subprocess.run(
                f'psql "{PROXY_DB_URL}" -c "{copy_query}"',
                shell=True, stdin=f, capture_output=True, text=True, timeout=1200  # 20 minutes
            )
        
        if result.returncode == 0:
            print(f"   ✅ Missing order_line_items imported successfully")
            return True
        else:
            print(f"   ❌ Import failed:")
            print(f"      {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Import error: {str(e)}")
        return False

def final_order_line_items_import():
    """Main function for final order_line_items import"""
    
    print("🎯 FINAL ORDER LINE ITEMS IMPORT")
    print("=" * 50)
    print("Strategy: Import only missing order_line_items to complete sync")
    
    export_dir = Path("final_line_items_export")
    export_dir.mkdir(exist_ok=True)
    
    # Start proxy
    proxy_process = start_cloud_sql_proxy()
    if not proxy_process:
        print("❌ Could not start Cloud SQL Proxy")
        return False
    
    try:
        # Get missing order_line_items
        missing_uids = get_missing_order_line_items()
        if not missing_uids:
            print("✅ No missing order_line_items found - production is complete!")
            return True
        
        # Export missing order_line_items
        export_file = export_missing_order_line_items(missing_uids, export_dir)
        
        if not export_file:
            print("❌ Failed to export missing order_line_items")
            return False
        
        # Import missing order_line_items
        success = import_csv_file(export_file, 'order_line_items')
        
        # Clean up
        try:
            os.remove(export_file)
            export_dir.rmdir()
        except:
            pass
        
        if success:
            print(f"\n🎉 FINAL IMPORT COMPLETED SUCCESSFULLY!")
            print(f"📊 Imported {len(missing_uids):,} missing order_line_items")
            return True
        else:
            print(f"\n⚠️ Final import failed")
            return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False
    
    finally:
        # Stop proxy
        if proxy_process and hasattr(proxy_process, 'pid'):
            try:
                os.killpg(os.getpgid(proxy_process.pid), subprocess.signal.SIGTERM)
                print("✅ Cloud SQL Proxy stopped")
            except:
                print("⚠️ Could not stop proxy cleanly")

def verify_final_counts():
    """Verify the final counts in production"""
    print("\n🔍 VERIFYING FINAL PRODUCTION COUNTS")
    print("=" * 40)
    
    # Start proxy for verification
    proxy_process = start_cloud_sql_proxy()
    
    try:
        verify_cmd = f'''psql "{PROXY_DB_URL}" -c "
        SELECT 
            'orders' as table_name, 
            COUNT(*) as count,
            MIN(created_at::date) as earliest,
            MAX(created_at::date) as latest
        FROM orders
        UNION ALL
        SELECT 
            'order_line_items',
            COUNT(*),
            MIN((SELECT created_at FROM orders WHERE orders.id = order_line_items.order_id)::date),
            MAX((SELECT created_at FROM orders WHERE orders.id = order_line_items.order_id)::date)
        FROM order_line_items
        ORDER BY table_name;" '''
        
        result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("📊 Final production database counts:")
            print(result.stdout)
            
            # Also get local counts for comparison
            local_cmd = f'''psql "{LOCAL_DB_URL}" -c "
            SELECT 
                'orders' as table_name, 
                COUNT(*) as count
            FROM orders
            UNION ALL
            SELECT 
                'order_line_items',
                COUNT(*)
            FROM order_line_items
            ORDER BY table_name;" '''
            
            local_result = subprocess.run(local_cmd, shell=True, capture_output=True, text=True, timeout=30)
            if local_result.returncode == 0:
                print("\n📊 Local database counts for comparison:")
                print(local_result.stdout)
        else:
            print(f"❌ Verification failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
    finally:
        if proxy_process and hasattr(proxy_process, 'pid'):
            try:
                os.killpg(os.getpgid(proxy_process.pid), subprocess.signal.SIGTERM)
            except:
                pass

if __name__ == "__main__":
    print("🎯 Starting Final Order Line Items Import")
    
    success = final_order_line_items_import()
    
    if success:
        verify_final_counts()
        print(f"\n🎉 ALL ORDER DATA IS NOW SYNCHRONIZED!")
        print(f"🔄 Production database now contains complete order history")
    else:
        print(f"\n⚠️ Final import had issues - some order_line_items may be missing") 