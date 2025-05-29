#!/usr/bin/env python3
"""
Verify Production Status - Check what data we actually have
"""
import subprocess
import time
import os

# Production database details
CLOUD_SQL_CONNECTION_NAME = "nytex-business-systems:us-central1:nytex-main-db"
LOCAL_PROXY_PORT = 5433
PROXY_DB_URL = f"postgresql://nytex_user:NytexSecure2024!@localhost:{LOCAL_PROXY_PORT}/nytex_dashboard"
LOCAL_DB_URL = "postgresql://joshgoble:@localhost:5432/square_data_sync"

def ensure_proxy_running():
    """Make sure Cloud SQL Proxy is running"""
    check_running = subprocess.run(f"lsof -ti:{LOCAL_PROXY_PORT}", shell=True, capture_output=True)
    if check_running.returncode == 0:
        print(f"✅ Cloud SQL Proxy already running on port {LOCAL_PROXY_PORT}")
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

def run_query(db_url, query, description):
    """Run a query and return results"""
    print(f"🔍 {description}...")
    
    try:
        result = subprocess.run(
            f'psql "{db_url}" -c "{query}" -t',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"   ❌ Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None

def main():
    print("🎯 PRODUCTION STATUS VERIFICATION")
    print("=" * 50)
    
    # Ensure proxy is running
    if not ensure_proxy_running():
        return
    
    # Test basic connection
    test_result = run_query(PROXY_DB_URL, "SELECT 1 as test;", "Testing connection")
    if test_result is None:
        print("❌ Cannot connect to production database")
        return
    print("✅ Connection successful")
    
    # Check what tables exist
    tables_query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('orders', 'order_line_items')
    ORDER BY table_name;
    """
    
    tables_result = run_query(PROXY_DB_URL, tables_query, "Checking if tables exist")
    if tables_result:
        existing_tables = [line.strip() for line in tables_result.split('\n') if line.strip()]
        print(f"📊 Existing tables: {existing_tables}")
    else:
        print("❌ Could not check tables")
        return
    
    # Get table counts
    if 'orders' in existing_tables:
        orders_count = run_query(PROXY_DB_URL, "SELECT COUNT(*) FROM orders;", "Counting orders")
        if orders_count:
            print(f"📈 Orders in production: {orders_count.strip()}")
    
    if 'order_line_items' in existing_tables:
        line_items_count = run_query(PROXY_DB_URL, "SELECT COUNT(*) FROM order_line_items;", "Counting order_line_items")
        if line_items_count:
            print(f"📈 Order_line_items in production: {line_items_count.strip()}")
        
        # Check table structure
        structure_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'order_line_items' 
        AND table_schema = 'public'
        ORDER BY ordinal_position;
        """
        
        structure_result = run_query(PROXY_DB_URL, structure_query, "Checking order_line_items structure")
        if structure_result:
            print("📋 Order_line_items columns:")
            for line in structure_result.split('\n'):
                if line.strip():
                    print(f"   {line.strip()}")
        
        # Check primary key
        pk_query = """
        SELECT constraint_name, column_name
        FROM information_schema.key_column_usage
        WHERE table_name = 'order_line_items'
        AND table_schema = 'public';
        """
        
        pk_result = run_query(PROXY_DB_URL, pk_query, "Checking primary key constraints")
        if pk_result:
            print("🔑 Primary key info:")
            for line in pk_result.split('\n'):
                if line.strip():
                    print(f"   {line.strip()}")
    
    # Compare with local
    print(f"\n📊 LOCAL DATABASE COMPARISON:")
    local_orders = run_query(LOCAL_DB_URL, "SELECT COUNT(*) FROM orders;", "Local orders count")
    local_line_items = run_query(LOCAL_DB_URL, "SELECT COUNT(*) FROM order_line_items;", "Local order_line_items count")
    
    if local_orders:
        print(f"📈 Local orders: {local_orders.strip()}")
    if local_line_items:
        print(f"📈 Local order_line_items: {local_line_items.strip()}")
    
    # Summary
    print(f"\n🎯 SUMMARY:")
    try:
        prod_orders = int(orders_count.strip()) if orders_count else 0
        prod_line_items = int(line_items_count.strip()) if line_items_count else 0
        local_orders_num = int(local_orders.strip()) if local_orders else 0
        local_line_items_num = int(local_line_items.strip()) if local_line_items else 0
        
        print(f"Orders: {prod_orders:,} / {local_orders_num:,} ({100*prod_orders/local_orders_num:.1f}%)")
        print(f"Order Line Items: {prod_line_items:,} / {local_line_items_num:,} ({100*prod_line_items/local_line_items_num:.1f}%)")
        
        if prod_orders == local_orders_num and prod_line_items == local_line_items_num:
            print("🎉 Production database is FULLY SYNCHRONIZED!")
        else:
            print("⚠️ Production database needs more data")
            
    except:
        print("❌ Could not calculate percentages")

if __name__ == "__main__":
    main() 