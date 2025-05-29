#!/usr/bin/env python3
"""
Batch Import for Large Tables - Split orders and order_line_items by date ranges
This approach handles the timeout issues by importing data in smaller chunks
"""
import subprocess
import time
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Production database details
CLOUD_SQL_CONNECTION_NAME = "nytex-business-systems:us-central1:nytex-main-db"
LOCAL_PROXY_PORT = 5433
PROXY_DB_URL = f"postgresql://nytex_user:NytexSecure2024!@localhost:{LOCAL_PROXY_PORT}/nytex_dashboard"
LOCAL_DB_URL = "postgresql://joshgoble:@localhost:5432/square_data_sync"

def start_cloud_sql_proxy():
    """Start Cloud SQL Proxy in background"""
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
        
        # Wait for proxy to start
        time.sleep(3)
        
        # Test connection
        test_cmd = f'psql "{PROXY_DB_URL}" -c "SELECT 1;" --quiet'
        test_result = subprocess.run(test_cmd, shell=True, capture_output=True, timeout=10)
        
        if test_result.returncode == 0:
            print(f"✅ Cloud SQL Proxy started successfully on port {LOCAL_PROXY_PORT}")
            return proxy_process
        else:
            print(f"❌ Proxy connection test failed")
            return None
            
    except Exception as e:
        print(f"❌ Error starting proxy: {str(e)}")
        return None

def get_date_ranges_for_orders():
    """Get date ranges for batching orders by year"""
    print("📅 Analyzing order date ranges...")
    
    # Get min/max dates from orders table
    date_query = """
    SELECT 
        DATE_TRUNC('year', created_at)::date as year_start,
        COUNT(*) as order_count
    FROM orders 
    GROUP BY DATE_TRUNC('year', created_at)
    ORDER BY year_start;
    """
    
    try:
        result = subprocess.run(
            f'psql "{LOCAL_DB_URL}" -c "{date_query}" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            date_ranges = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split('|')
                    if len(parts) >= 2:
                        year_start = parts[0].strip()
                        count = int(parts[1].strip())
                        year_end = f"{int(year_start[:4]) + 1}-01-01"
                        date_ranges.append((year_start, year_end, count))
            
            print(f"📊 Found {len(date_ranges)} year ranges:")
            for start, end, count in date_ranges:
                print(f"   {start[:4]}: {count:,} orders")
            
            return date_ranges
        else:
            print(f"❌ Error getting date ranges: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"❌ Error analyzing dates: {str(e)}")
        return []

def export_orders_batch(start_date, end_date, batch_name, export_dir):
    """Export orders for a specific date range using COPY TO CSV"""
    export_file = export_dir / f"orders_{batch_name}.csv"
    
    # Use COPY TO export to CSV
    copy_query = f"""
    COPY (
        SELECT * FROM orders 
        WHERE created_at >= '{start_date}' AND created_at < '{end_date}'
        ORDER BY created_at
    ) TO STDOUT WITH CSV HEADER;
    """
    
    print(f"   🔄 Exporting orders {batch_name}...")
    
    try:
        # Run COPY query and save to file
        with open(export_file, 'w') as f:
            result = subprocess.run(
                f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=180
            )
        
        if result.returncode == 0:
            # Check if file has content
            if os.path.exists(export_file) and os.path.getsize(export_file) > 10:  # More than just header
                print(f"   ✅ Orders {batch_name} exported")
                return export_file
            else:
                print(f"   ⚠️ Orders {batch_name} exported but empty")
                return None
        else:
            print(f"   ❌ Orders {batch_name} failed: {result.stderr[:100]}")
            return None
            
    except Exception as e:
        print(f"   ❌ Orders {batch_name} error: {str(e)}")
        return None

def export_order_line_items_batch(start_date, end_date, batch_name, export_dir):
    """Export order_line_items for orders in a specific date range using COPY TO CSV"""
    export_file = export_dir / f"order_line_items_{batch_name}.csv"
    
    # Use COPY TO export to CSV
    copy_query = f"""
    COPY (
        SELECT oli.* FROM order_line_items oli
        JOIN orders o ON oli.order_id = o.id
        WHERE o.created_at >= '{start_date}' AND o.created_at < '{end_date}'
        ORDER BY o.created_at, oli.id
    ) TO STDOUT WITH CSV HEADER;
    """
    
    print(f"   🔄 Exporting order_line_items {batch_name}...")
    
    try:
        # Run COPY query and save to file
        with open(export_file, 'w') as f:
            result = subprocess.run(
                f'psql "{LOCAL_DB_URL}" -c "{copy_query}"',
                shell=True, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
            )
        
        if result.returncode == 0:
            # Check if file has content
            if os.path.exists(export_file) and os.path.getsize(export_file) > 10:  # More than just header
                print(f"   ✅ Order_line_items {batch_name} exported")
                return export_file
            else:
                print(f"   ⚠️ Order_line_items {batch_name} exported but empty")
                return None
        else:
            print(f"   ❌ Order_line_items {batch_name} failed: {result.stderr[:100]}")
            return None
            
    except Exception as e:
        print(f"   ❌ Order_line_items {batch_name} error: {str(e)}")
        return None

def import_batch_file(csv_file, table_name, batch_name):
    """Import a batch CSV file using COPY FROM"""
    print(f"📤 Importing {batch_name}...")
    
    # Use COPY FROM to import CSV
    copy_query = f"""
    COPY {table_name} FROM STDIN WITH CSV HEADER;
    """
    
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
            
    except subprocess.TimeoutExpired:
        print(f"   ⏱️ {batch_name} timed out")
        return False
    except Exception as e:
        print(f"   ❌ {batch_name} error: {str(e)}")
        return False

def batch_import_large_tables():
    """Main function to batch import orders and order_line_items"""
    
    print("🎯 BATCH IMPORT FOR LARGE TABLES")
    print("=" * 50)
    print("Strategy: Split by date ranges and import in batches")
    
    # Create export directory
    export_dir = Path("batch_exports")
    export_dir.mkdir(exist_ok=True)
    
    # Get date ranges
    date_ranges = get_date_ranges_for_orders()
    if not date_ranges:
        print("❌ Could not determine date ranges")
        return False
    
    # Start proxy
    proxy_process = start_cloud_sql_proxy()
    if not proxy_process:
        print("❌ Could not start Cloud SQL Proxy")
        return False
    
    try:
        successful_batches = []
        failed_batches = []
        total_batches = len(date_ranges) * 2  # orders + order_line_items for each year
        
        print(f"\n📦 Processing {len(date_ranges)} date ranges ({total_batches} total batches)...")
        
        for i, (start_date, end_date, order_count) in enumerate(date_ranges):
            year = start_date[:4]
            batch_name = f"{year}_{order_count}orders"
            
            print(f"\n📅 Processing {year} ({order_count:,} orders)...")
            
            # Export orders batch
            orders_file = export_orders_batch(start_date, end_date, batch_name, export_dir)
            
            # Export order_line_items batch
            line_items_file = export_order_line_items_batch(start_date, end_date, batch_name, export_dir)
            
            # Import orders batch
            if orders_file:
                if import_batch_file(orders_file, 'orders', f"orders_{batch_name}"):
                    successful_batches.append(f"orders_{batch_name}")
                else:
                    failed_batches.append(f"orders_{batch_name}")
                
                # Clean up
                try:
                    os.remove(orders_file)
                except:
                    pass
            else:
                failed_batches.append(f"orders_{batch_name}")
            
            # Import order_line_items batch
            if line_items_file:
                if import_batch_file(line_items_file, 'order_line_items', f"order_line_items_{batch_name}"):
                    successful_batches.append(f"order_line_items_{batch_name}")
                else:
                    failed_batches.append(f"order_line_items_{batch_name}")
                
                # Clean up
                try:
                    os.remove(line_items_file)
                except:
                    pass
            else:
                failed_batches.append(f"order_line_items_{batch_name}")
            
            # Progress update
            completed = (i + 1) * 2
            print(f"📈 Progress: {completed}/{total_batches} batches completed")
        
        # Results summary
        print(f"\n" + "=" * 50)
        print(f"🎯 BATCH IMPORT RESULTS")
        print(f"=" * 50)
        
        if successful_batches:
            print(f"\n✅ SUCCESSFUL BATCHES ({len(successful_batches)}):")
            for batch in successful_batches:
                print(f"   {batch}")
        
        if failed_batches:
            print(f"\n❌ FAILED BATCHES ({len(failed_batches)}):")
            for batch in failed_batches:
                print(f"   {batch}")
        
        success_rate = len(successful_batches) / total_batches * 100 if total_batches > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        # Cleanup
        try:
            export_dir.rmdir()
        except:
            pass
        
        return success_rate >= 90
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Import interrupted by user")
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

def verify_import_results():
    """Verify the import results by checking record counts"""
    print("\n🔍 VERIFYING IMPORT RESULTS")
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
    FROM order_line_items;" --quiet'''
    
    try:
        result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("📊 Production database counts:")
            print(result.stdout)
        else:
            print(f"❌ Verification failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")

if __name__ == "__main__":
    print("🎯 Starting Batch Import for Large Tables")
    
    success = batch_import_large_tables()
    
    if success:
        print(f"\n🎉 BATCH IMPORT COMPLETED SUCCESSFULLY!")
        verify_import_results()
        print(f"\n🔄 Next step: python scripts/compare_local_vs_production.py")
    else:
        print(f"\n⚠️ Batch import completed with issues")
        print(f"Some batches may have failed - check the output above") 