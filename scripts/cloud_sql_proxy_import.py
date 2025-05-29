#!/usr/bin/env python3
"""
Cloud SQL Proxy Import - Direct database import via Cloud SQL Proxy
This bypasses network connectivity issues by using Google Cloud SQL Proxy
"""
import subprocess
import time
import tempfile
import os
import sys
import json
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Production database details
CLOUD_SQL_CONNECTION_NAME = "nytex-business-systems:us-central1:nytex-main-db"
LOCAL_PROXY_PORT = 5433  # Use different port to avoid conflicts
PROXY_DB_URL = f"postgresql://nytex_user:NytexSecure2024!@localhost:{LOCAL_PROXY_PORT}/nytex_dashboard"

def start_cloud_sql_proxy():
    """Start Cloud SQL Proxy in background"""
    print("🔌 Starting Cloud SQL Proxy...")
    
    # Check if cloud_sql_proxy is installed
    check_proxy = subprocess.run("which cloud_sql_proxy", shell=True, capture_output=True)
    if check_proxy.returncode != 0:
        print("❌ cloud_sql_proxy not found!")
        print("💡 Install with: curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64")
        print("💡 Or use: gcloud auth application-default login")
        return None
    
    # Start proxy
    proxy_cmd = f"cloud_sql_proxy -instances={CLOUD_SQL_CONNECTION_NAME}=tcp:{LOCAL_PROXY_PORT}"
    
    try:
        proxy_process = subprocess.Popen(
            proxy_cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Wait a bit for proxy to start
        time.sleep(3)
        
        # Check if proxy is running
        if proxy_process.poll() is None:
            print(f"✅ Cloud SQL Proxy started on port {LOCAL_PROXY_PORT}")
            return proxy_process
        else:
            stdout, stderr = proxy_process.communicate()
            print(f"❌ Proxy failed to start:")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting proxy: {str(e)}")
        return None

def test_proxy_connection():
    """Test connection through proxy"""
    print("🧪 Testing proxy connection...")
    
    test_cmd = f'psql "{PROXY_DB_URL}" -c "SELECT version();" --quiet'
    
    try:
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Proxy connection successful!")
            return True
        else:
            print(f"❌ Proxy connection failed:")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Proxy connection timeout")
        return False
    except Exception as e:
        print(f"❌ Proxy connection error: {str(e)}")
        return False

def import_via_proxy():
    """Import all data via Cloud SQL Proxy"""
    
    # Get the exported SQL files from our previous successful export
    temp_dir = None
    sql_files = []
    
    # Look for recent temp directory with exports (they might still exist)
    # Or re-export quickly
    print("📁 Looking for SQL exports...")
    
    # We need to re-export since temp files are cleaned up
    # Use a persistent directory
    export_dir = Path("temp_exports")
    export_dir.mkdir(exist_ok=True)
    
    # Tables to export/import - only the ones that failed
    tables = [
        'orders', 'order_line_items', 'catalog_location_availability', 'inventory_counts'
    ]
    
    print("📥 Re-exporting tables...")
    local_db_url = "postgresql://joshgoble:@localhost:5432/square_data_sync"
    
    for table in tables:
        export_file = export_dir / f"{table}.sql"
        
        export_cmd = f"""pg_dump "{local_db_url}" \
            --table=public.{table} \
            --data-only \
            --inserts \
            --no-owner \
            --no-privileges \
            --file="{export_file}" """
        
        print(f"   🔄 Exporting {table}...")
        result = subprocess.run(export_cmd, shell=True, capture_output=True)
        
        if result.returncode == 0:
            sql_files.append((table, export_file))
            print(f"   ✅ {table} exported")
        else:
            print(f"   ❌ {table} failed: {result.stderr.decode()[:100]}")
    
    if not sql_files:
        print("❌ No SQL files available for import!")
        return False
    
    # Import each file
    print(f"\n📤 Importing {len(sql_files)} tables via proxy...")
    
    successful_imports = []
    failed_imports = []
    
    for table, sql_file in sql_files:
        print(f"🔄 Importing {table}...")
        
        import_cmd = f'psql "{PROXY_DB_URL}" --file="{sql_file}" --quiet'
        
        try:
            # Use longer timeout for large tables
            timeout = 600 if table in ['orders', 'order_line_items', 'catalog_location_availability', 'inventory_counts'] else 120
            result = subprocess.run(import_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                print(f"   ✅ {table} imported successfully")
                successful_imports.append(table)
            else:
                print(f"   ❌ {table} failed:")
                print(f"      {result.stderr[:100]}")
                failed_imports.append(table)
                
        except subprocess.TimeoutExpired:
            print(f"   ⏱️ {table} timed out (timeout: {timeout}s)")
            failed_imports.append(table)
        except Exception as e:
            print(f"   ❌ {table} error: {str(e)}")
            failed_imports.append(table)
    
    # Results
    print(f"\n" + "=" * 50)
    print(f"🎯 PROXY IMPORT RESULTS")
    print(f"=" * 50)
    
    if successful_imports:
        print(f"\n✅ SUCCESSFUL IMPORTS ({len(successful_imports)} tables):")
        for table in successful_imports:
            print(f"   {table}")
    
    if failed_imports:
        print(f"\n❌ FAILED IMPORTS ({len(failed_imports)} tables):")
        for table in failed_imports:
            print(f"   {table}")
    
    success_rate = len(successful_imports) / len(sql_files) * 100 if sql_files else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")
    
    # Cleanup
    print(f"\n🧹 Cleaning up export files...")
    for table, sql_file in sql_files:
        try:
            os.remove(sql_file)
        except:
            pass
    
    try:
        export_dir.rmdir()
    except:
        pass
    
    return success_rate >= 80

def stop_proxy(proxy_process):
    """Stop the Cloud SQL Proxy"""
    if proxy_process:
        print("🛑 Stopping Cloud SQL Proxy...")
        try:
            # Kill the process group
            os.killpg(os.getpgid(proxy_process.pid), subprocess.signal.SIGTERM)
            proxy_process.wait(timeout=5)
            print("✅ Proxy stopped")
        except:
            # Force kill if needed
            try:
                os.killpg(os.getpgid(proxy_process.pid), subprocess.signal.SIGKILL)
                print("✅ Proxy force stopped")
            except:
                print("⚠️ Could not stop proxy - may need manual cleanup")

def main():
    """Main execution"""
    print("🎯 CLOUD SQL PROXY IMPORT")
    print("=" * 50)
    print("Strategy: Use Cloud SQL Proxy for direct database access")
    
    proxy_process = None
    
    try:
        # Start proxy
        proxy_process = start_cloud_sql_proxy()
        if not proxy_process:
            print("❌ Failed to start Cloud SQL Proxy")
            return False
        
        # Test connection
        if not test_proxy_connection():
            print("❌ Proxy connection test failed")
            return False
        
        # Import data
        success = import_via_proxy()
        
        if success:
            print(f"\n🎉 CLOUD SQL PROXY IMPORT COMPLETED!")
            print(f"🔄 Next step: python scripts/compare_local_vs_production.py")
        else:
            print(f"\n⚠️ Cloud SQL Proxy import had issues")
        
        return success
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Import interrupted by user")
        return False
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False
    
    finally:
        # Always try to stop proxy
        stop_proxy(proxy_process)

if __name__ == "__main__":
    success = main() 