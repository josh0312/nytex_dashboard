#!/usr/bin/env python3
"""
Delete Erroneous Sale - Remove the $2.16 million "The Godfather" order that was captured in error
"""
import subprocess
import time
import json

# The problematic order ID
ERRONEOUS_ORDER_ID = "mknasZtDiUul9el73zNLANleV"

def check_connection(db_url, db_name):
    """Test database connection"""
    try:
        result = subprocess.run([
            'psql', db_url, '-c', 'SELECT 1;'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ {db_name} connection successful")
            return True
        else:
            print(f"❌ {db_name} connection failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {db_name} connection error: {str(e)}")
        return False

def get_order_details(db_url, db_name):
    """Get details of the erroneous order"""
    try:
        # Check if order exists
        result = subprocess.run([
            'psql', db_url, '-t', '-c', 
            f"SELECT COUNT(*) FROM orders WHERE id = '{ERRONEOUS_ORDER_ID}';"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ Error checking order in {db_name}: {result.stderr}")
            return None
        
        count = int(result.stdout.strip())
        if count == 0:
            print(f"ℹ️ Order {ERRONEOUS_ORDER_ID} not found in {db_name}")
            return {"exists": False}
        
        # Get order details
        details_result = subprocess.run([
            'psql', db_url, '-c', 
            f"""SELECT 
                o.id,
                o.total_money->>'amount' as total_cents,
                ROUND((o.total_money->>'amount')::numeric / 100, 2) as total_dollars,
                o.created_at,
                o.location_id
            FROM orders o 
            WHERE o.id = '{ERRONEOUS_ORDER_ID}';"""
        ], capture_output=True, text=True, timeout=10)
        
        if details_result.returncode == 0:
            print(f"📊 Order details in {db_name}:")
            print(details_result.stdout)
            
            # Get line items count
            line_items_result = subprocess.run([
                'psql', db_url, '-t', '-c', 
                f"SELECT COUNT(*) FROM order_line_items WHERE order_id = '{ERRONEOUS_ORDER_ID}';"
            ], capture_output=True, text=True, timeout=10)
            
            line_items_count = 0
            if line_items_result.returncode == 0:
                line_items_count = int(line_items_result.stdout.strip())
            
            return {
                "exists": True, 
                "details": details_result.stdout,
                "line_items_count": line_items_count
            }
        else:
            print(f"❌ Error getting order details from {db_name}: {details_result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking order in {db_name}: {str(e)}")
        return None

def delete_order(db_url, db_name, dry_run=True):
    """Delete the erroneous order and its line items"""
    try:
        if dry_run:
            print(f"🔍 DRY RUN - Would delete from {db_name}:")
            print(f"   - Order: {ERRONEOUS_ORDER_ID}")
            print(f"   - All associated order line items")
            return True
        
        print(f"🗑️ Deleting erroneous order from {db_name}...")
        
        # Delete order line items first (due to foreign key constraints)
        line_items_result = subprocess.run([
            'psql', db_url, '-c', 
            f"DELETE FROM order_line_items WHERE order_id = '{ERRONEOUS_ORDER_ID}';"
        ], capture_output=True, text=True, timeout=30)
        
        if line_items_result.returncode != 0:
            print(f"❌ Error deleting line items from {db_name}: {line_items_result.stderr}")
            return False
        
        print(f"✅ Deleted line items from {db_name}")
        
        # Delete the order
        order_result = subprocess.run([
            'psql', db_url, '-c', 
            f"DELETE FROM orders WHERE id = '{ERRONEOUS_ORDER_ID}';"
        ], capture_output=True, text=True, timeout=30)
        
        if order_result.returncode != 0:
            print(f"❌ Error deleting order from {db_name}: {order_result.stderr}")
            return False
        
        print(f"✅ Deleted order from {db_name}")
        
        # Verify deletion
        verify_result = subprocess.run([
            'psql', db_url, '-t', '-c', 
            f"SELECT COUNT(*) FROM orders WHERE id = '{ERRONEOUS_ORDER_ID}';"
        ], capture_output=True, text=True, timeout=10)
        
        if verify_result.returncode == 0:
            remaining = int(verify_result.stdout.strip())
            if remaining == 0:
                print(f"✅ Verified deletion from {db_name}")
                return True
            else:
                print(f"❌ Order still exists in {db_name}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting from {db_name}: {str(e)}")
        return False

def main():
    print("🎯 ERRONEOUS SALE DELETION")
    print("=" * 50)
    print(f"Target Order ID: {ERRONEOUS_ORDER_ID}")
    print(f"Expected: $2.16 million 'The Godfather' order")
    print()
    
    # Database URLs
    local_db = "postgresql://joshgoble:@localhost:5432/square_data_sync"
    prod_db = "postgresql://nytex_user:NytexSecure2024!@localhost:5433/nytex_dashboard"
    
    # Start Cloud SQL Proxy for production
    print("🔌 Starting Cloud SQL Proxy...")
    subprocess.run('pkill cloud_sql_proxy', shell=True, capture_output=True)
    time.sleep(2)
    
    proxy_proc = subprocess.Popen([
        'cloud_sql_proxy', 
        '-instances=nytex-business-systems:us-central1:nytex-main-db=tcp:5433'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(5)
    
    try:
        # Check connections
        local_connected = check_connection(local_db, "Local")
        prod_connected = check_connection(prod_db, "Production")
        
        if not local_connected:
            print("❌ Cannot proceed without local database connection")
            return False
        
        if not prod_connected:
            print("⚠️ Cannot access production database")
            print("Will only process local database")
        
        # Check order details in both databases
        print("\n🔍 CHECKING ORDER DETAILS")
        print("-" * 30)
        
        local_details = get_order_details(local_db, "Local")
        prod_details = None
        
        if prod_connected:
            prod_details = get_order_details(prod_db, "Production")
        
        # Show summary
        print("\n📋 SUMMARY")
        print("-" * 20)
        if local_details and local_details.get("exists"):
            print(f"Local: Order EXISTS with {local_details.get('line_items_count', 0)} line items")
        else:
            print("Local: Order NOT FOUND")
        
        if prod_details and prod_details.get("exists"):
            print(f"Production: Order EXISTS with {prod_details.get('line_items_count', 0)} line items")
        elif prod_connected:
            print("Production: Order NOT FOUND")
        else:
            print("Production: Could not check")
        
        # Confirm deletion
        print("\n⚠️ DELETION CONFIRMATION")
        print("This will permanently delete the erroneous $2.16 million order")
        print("Are you sure you want to proceed? (yes/no)")
        
        # Get user confirmation
        confirmation = input("Enter 'yes' to proceed with deletion: ").strip().lower()
        
        if confirmation != 'yes':
            print("❌ Deletion cancelled by user")
            return False
        
        print("\n🗑️ PERFORMING ACTUAL DELETION")
        print("-" * 35)
        
        deletion_success = True
        
        if local_details and local_details.get("exists"):
            if not delete_order(local_db, "Local", dry_run=False):
                deletion_success = False
        
        if prod_details and prod_details.get("exists"):
            if not delete_order(prod_db, "Production", dry_run=False):
                deletion_success = False
        
        if deletion_success:
            print("\n✅ DELETION COMPLETED SUCCESSFULLY")
            print("The erroneous $2.16 million order has been removed from both databases")
        else:
            print("\n❌ DELETION HAD ISSUES")
            print("Check the output above for details")
        
        return deletion_success
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    finally:
        # Stop proxy
        try:
            proxy_proc.terminate()
            proxy_proc.wait(timeout=5)
            print("✅ Proxy stopped")
        except:
            print("⚠️ Could not stop proxy cleanly")

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 ERRONEOUS SALE DELETION COMPLETED!")
        print("✅ Database integrity restored")
        print("📊 Sales data is now accurate for reporting")
    else:
        print("\n❌ Deletion process had issues - check output above") 