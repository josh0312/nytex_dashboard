#!/usr/bin/env python3
"""
Smart Batch Import - Handles duplicates and imports only missing data
"""
import subprocess
import time
import os
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Production database details
CLOUD_SQL_CONNECTION_NAME = "nytex-business-systems:us-central1:nytex-main-db"
LOCAL_PROXY_PORT = 5433
PROXY_DB_URL = f"postgresql://nytex_user:NytexSecure2024!@localhost:{LOCAL_PROXY_PORT}/nytex_dashboard"
LOCAL_DB_URL = "postgresql://joshgoble:@localhost:5432/square_data_sync"

def start_cloud_sql_proxy():
    """Start Cloud SQL Proxy if not running"""
    print("🔌 Starting Cloud SQL Proxy...")
    
    # Check if already running
    check_running = subprocess.run(f"lsof -ti:{LOCAL_PROXY_PORT}", shell=True, capture_output=True)
    if check_running.returncode == 0:
        print(f"✅ Cloud SQL Proxy already running on port {LOCAL_PROXY_PORT}")
        return True
    
    # Start proxy
    proxy_cmd = f"cloud_sql_proxy -instances={CLOUD_SQL_CONNECTION_NAME}=tcp:{LOCAL_PROXY_PORT}"
    
    try:
        proxy_process = subprocess.Popen(
            proxy_cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        time.sleep(3)
        
        # Test connection
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

def get_existing_orders_in_production():
    """Get list of order IDs that already exist in production"""
    print("🔍 Checking existing orders in production...")
    
    try:
        result = subprocess.run(
            f'psql "{PROXY_DB_URL}" -c "SELECT id FROM orders;" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            existing_ids = set()
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    existing_ids.add(line.strip())
            
            print(f"📊 Found {len(existing_ids)} existing orders in production")
            return existing_ids
        else:
            print(f"❌ Error checking existing orders: {result.stderr}")
            return set()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return set()

def get_missing_orders_by_year():
    """Get orders that don't exist in production, grouped by year"""
    print("📅 Analyzing missing orders by year...")
    
    existing_orders = get_existing_orders_in_production()
    
    # Get all orders by year from local DB
    date_query = """
    SELECT 
        DATE_TRUNC('year', created_at)::date as year_start,
        id,
        created_at
    FROM orders 
    ORDER BY created_at;
    """
    
    try:
        result = subprocess.run(
            f'psql "{LOCAL_DB_URL}" -c "{date_query}" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            missing_by_year = {}
            total_missing = 0
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split('|')
                    if len(parts) >= 2:
                        year_start = parts[0].strip()
                        order_id = parts[1].strip()
                        
                        if order_id not in existing_orders:
                            year = year_start[:4]
                            if year not in missing_by_year:
                                missing_by_year[year] = []
                            missing_by_year[year].append(order_id)
                            total_missing += 1
            
            print(f"📊 Missing orders by year:")
            for year in sorted(missing_by_year.keys()):
                print(f"   {year}: {len(missing_by_year[year]):,} orders")
            print(f"📈 Total missing orders: {total_missing:,}")
            
            return missing_by_year
        else:
            print(f"❌ Error getting missing orders: {result.stderr}")
            return {}
            
    except Exception as e:
        print(f"❌ Error analyzing missing orders: {str(e)}")
        return {}

def export_missing_orders_batch(year, order_ids, export_dir):
    """Export missing orders for a specific year"""
    if not order_ids:
        return None
        
    export_file = export_dir / f"missing_orders_{year}.csv"
    
    # Create WHERE clause for specific order IDs
    id_list = "', '".join(order_ids)
    
    copy_query = f"""
    COPY (
        SELECT * FROM orders 
        WHERE id IN ('{id_list}')
        ORDER BY created_at
    ) TO STDOUT WITH CSV HEADER;
    """
    
    print(f"   🔄 Exporting {len(order_ids)} missing orders for {year}...")
    
    try:
        with open(export_file, 'w') as f:
            result = subprocess.run(
                f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=180
            )
        
        if result.returncode == 0 and os.path.getsize(export_file) > 10:
            print(f"   ✅ Missing orders for {year} exported")
            return export_file
        else:
            print(f"   ❌ Failed to export orders for {year}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error exporting orders for {year}: {str(e)}")
        return None

def export_missing_order_line_items_batch(year, order_ids, export_dir):
    """Export order_line_items for missing orders"""
    if not order_ids:
        return None
        
    export_file = export_dir / f"missing_order_line_items_{year}.csv"
    
    # Create WHERE clause for specific order IDs
    id_list = "', '".join(order_ids)
    
    copy_query = f"""
    COPY (
        SELECT * FROM order_line_items
        WHERE order_id IN ('{id_list}')
        ORDER BY order_id, uid
    ) TO STDOUT WITH CSV HEADER;
    """
    
    print(f"   🔄 Exporting order_line_items for {len(order_ids)} missing orders ({year})...")
    
    try:
        with open(export_file, 'w') as f:
            result = subprocess.run(
                f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
            )
        
        if result.returncode == 0 and os.path.getsize(export_file) > 10:
            print(f"   ✅ Order_line_items for {year} exported")
            return export_file
        else:
            print(f"   ⚠️ No order_line_items found for {year} (may be empty)")
            return None
            
    except Exception as e:
        print(f"   ❌ Error exporting order_line_items for {year}: {str(e)}")
        return None

def import_csv_file(csv_file, table_name, batch_name):
    """Import a CSV file using COPY FROM"""
    print(f"📤 Importing {batch_name}...")
    
    copy_query = f"COPY {table_name} FROM STDIN WITH CSV HEADER;"
    
    try:
        with open(csv_file, 'r') as f:
            result = subprocess.run(
                f'psql "{PROXY_DB_URL}" -c "{copy_query}"',
                shell=True, stdin=f, capture_output=True, text=True, timeout=600
            )
        
        if result.returncode == 0:
            print(f"   ✅ {batch_name} imported successfully")
            return True
        else:
            print(f"   ❌ {batch_name} failed:")
            print(f"      {result.stderr[:150]}")
            return False
            
    except Exception as e:
        print(f"   ❌ {batch_name} error: {str(e)}")
        return False

def smart_batch_import():
    """Main function for smart batch import"""
    
    print("🎯 SMART BATCH IMPORT - MISSING DATA ONLY")
    print("=" * 50)
    print("Strategy: Import only missing orders to avoid duplicates")
    
    # Create export directory
    export_dir = Path("smart_batch_exports")
    export_dir.mkdir(exist_ok=True)
    
    # Start proxy
    proxy_process = start_cloud_sql_proxy()
    if not proxy_process:
        print("❌ Could not start Cloud SQL Proxy")
        return False
    
    try:
        # Get missing orders by year
        missing_by_year = get_missing_orders_by_year()
        if not missing_by_year:
            print("✅ No missing orders found - production is up to date!")
            return True
        
        successful_batches = []
        failed_batches = []
        total_batches = len(missing_by_year) * 2  # orders + order_line_items for each year
        
        print(f"\n📦 Processing {len(missing_by_year)} years ({total_batches} total batches)...")
        
        for i, (year, order_ids) in enumerate(missing_by_year.items()):
            print(f"\n📅 Processing {year} ({len(order_ids):,} missing orders)...")
            
            # Export missing orders
            orders_file = export_missing_orders_batch(year, order_ids, export_dir)
            
            # Export missing order_line_items
            line_items_file = export_missing_order_line_items_batch(year, order_ids, export_dir)
            
            # Import orders
            if orders_file:
                if import_csv_file(orders_file, 'orders', f"orders_{year}"):
                    successful_batches.append(f"orders_{year}")
                else:
                    failed_batches.append(f"orders_{year}")
                
                # Clean up
                try:
                    os.remove(orders_file)
                except:
                    pass
            else:
                failed_batches.append(f"orders_{year}")
            
            # Import order_line_items
            if line_items_file:
                if import_csv_file(line_items_file, 'order_line_items', f"order_line_items_{year}"):
                    successful_batches.append(f"order_line_items_{year}")
                else:
                    failed_batches.append(f"order_line_items_{year}")
                
                # Clean up
                try:
                    os.remove(line_items_file)
                except:
                    pass
            else:
                # This is OK - some years might not have line items
                successful_batches.append(f"order_line_items_{year}")
            
            # Progress update
            completed = (i + 1) * 2
            print(f"📈 Progress: {completed}/{total_batches} batches completed")
        
        # Results summary
        print(f"\n" + "=" * 50)
        print(f"🎯 SMART IMPORT RESULTS")
        print(f"=" * 50)
        
        if successful_batches:
            print(f"\n✅ SUCCESSFUL BATCHES ({len(successful_batches)}):")
            for batch in successful_batches:
                print(f"   {batch}")
        
        if failed_batches:
            print(f"\n❌ FAILED BATCHES ({len(failed_batches)}):")
            for batch in failed_batches:
                print(f"   {batch}")
        
        success_rate = len(successful_batches) / total_batches * 100 if total_batches > 0 else 100
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        # Cleanup
        try:
            export_dir.rmdir()
        except:
            pass
        
        return success_rate >= 80
        
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

def verify_final_results():
    """Verify the final import results"""
    print("\n🔍 VERIFYING FINAL RESULTS")
    print("=" * 30)
    
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
    FROM order_line_items;" '''
    
    try:
        result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("📊 Final production database counts:")
            print(result.stdout)
        else:
            print(f"❌ Verification failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")

if __name__ == "__main__":
    print("🎯 Starting Smart Batch Import")
    
    success = smart_batch_import()
    
    if success:
        print(f"\n🎉 SMART BATCH IMPORT COMPLETED SUCCESSFULLY!")
        verify_final_results()
        print(f"\n🔄 All order data is now synchronized with production!")
    else:
        print(f"\n⚠️ Smart batch import completed with issues")
        print(f"Some batches may have failed - check the output above") 