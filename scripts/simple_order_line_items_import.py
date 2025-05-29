#!/usr/bin/env python3
"""
Simple Order Line Items Import - Direct import of the cleaned CSV
"""
import subprocess
import time
import os

def main():
    print("🎯 SIMPLE ORDER LINE ITEMS IMPORT")
    print("=" * 50)
    
    # Kill existing proxy
    print("🔌 Restarting Cloud SQL Proxy...")
    subprocess.run('pkill cloud_sql_proxy', shell=True, capture_output=True)
    time.sleep(2)
    
    # Start fresh proxy
    proxy_proc = subprocess.Popen([
        'cloud_sql_proxy', 
        '-instances=nytex-business-systems:us-central1:nytex-main-db=tcp:5433'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(5)
    
    try:
        # Test connection
        print("🔍 Testing connection...")
        test_result = subprocess.run([
            'psql', 
            'postgresql://nytex_user:NytexSecure2024!@localhost:5433/nytex_dashboard', 
            '-c', 'SELECT 1;'
        ], capture_output=True, text=True, timeout=10)
        
        if test_result.returncode != 0:
            print(f"❌ Connection failed: {test_result.stderr}")
            return False
        
        print("✅ Connection successful")
        
        # Clear table
        print("🗑️ Clearing order_line_items table...")
        clear_result = subprocess.run([
            'psql', 
            'postgresql://nytex_user:NytexSecure2024!@localhost:5433/nytex_dashboard', 
            '-c', 'TRUNCATE TABLE order_line_items RESTART IDENTITY CASCADE;'
        ], capture_output=True, text=True, timeout=30)
        
        if clear_result.returncode != 0:
            print(f"❌ Clear failed: {clear_result.stderr}")
            return False
        
        print("✅ Table cleared")
        
        # Verify table is actually empty
        verify_result = subprocess.run([
            'psql', 
            'postgresql://nytex_user:NytexSecure2024!@localhost:5433/nytex_dashboard', 
            '-c', 'SELECT COUNT(*) FROM order_line_items;', 
            '-t'
        ], capture_output=True, text=True, timeout=10)
        
        if verify_result.returncode == 0:
            count = verify_result.stdout.strip()
            if count != '0':
                print(f"❌ Table not properly cleared - still has {count} records")
                return False
            print("✅ Verified table is empty")
        
        # Import data
        print("📥 Importing unique order line items...")
        
        if not os.path.exists('unique_order_line_items.csv'):
            print("❌ CSV file not found")
            return False
        
        with open('unique_order_line_items.csv', 'r') as f:
            import_result = subprocess.run([
                'psql', 
                'postgresql://nytex_user:NytexSecure2024!@localhost:5433/nytex_dashboard', 
                '-c', 'COPY order_line_items (order_id,uid,name,quantity,note,catalog_object_id,catalog_version,variation_name,item_type,base_price_money,gross_sales_money,total_tax_money,total_discount_money,total_money,applied_taxes,applied_discounts,modifiers,pricing_blocklists) FROM STDIN WITH CSV HEADER;'
            ], stdin=f, capture_output=True, text=True, timeout=600)
        
        if import_result.returncode != 0:
            print(f"❌ Import failed: {import_result.stderr}")
            return False
        
        print("✅ Import successful")
        
        # Verify count
        print("🔍 Verifying final count...")
        count_result = subprocess.run([
            'psql', 
            'postgresql://nytex_user:NytexSecure2024!@localhost:5433/nytex_dashboard', 
            '-c', 'SELECT COUNT(*) FROM order_line_items;', 
            '-t'
        ], capture_output=True, text=True, timeout=30)
        
        if count_result.returncode != 0:
            print(f"❌ Count check failed: {count_result.stderr}")
            return False
        
        final_count = count_result.stdout.strip()
        print(f"📊 Final count: {final_count}")
        
        # Also check local count for comparison
        local_result = subprocess.run([
            'psql',
            'postgresql://joshgoble:@localhost:5432/square_data_sync',
            '-c', 'SELECT COUNT(DISTINCT uid) FROM order_line_items;',
            '-t'
        ], capture_output=True, text=True, timeout=30)
        
        if local_result.returncode == 0:
            local_unique = local_result.stdout.strip()
            print(f"📊 Local unique: {local_unique}")
            
            if final_count == local_unique:
                print("🎉 PERFECT MATCH - All unique order line items imported!")
                return True
            else:
                print(f"⚠️ Counts don't match - production: {final_count}, local unique: {local_unique}")
                return False
        else:
            print("✅ Import completed but couldn't verify against local")
            return True
            
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
        print("\n🎉 ORDER LINE ITEMS IMPORT COMPLETED!")
        print("🔄 Production database now has complete order data")
    else:
        print("\n❌ Import had issues - check output above") 