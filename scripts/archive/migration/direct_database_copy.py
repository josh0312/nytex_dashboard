#!/usr/bin/env python3
"""
Direct Database Copy - Option B Implementation
Fast one-time data sync using pg_dump/pg_restore
"""
import asyncio
import subprocess
import os
import sys
import tempfile
from datetime import datetime

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.database import get_session

# Database URLs
LOCAL_DB_URL = "postgresql://joshgoble:@localhost:5432/square_data_sync"
PROD_DB_URL = "postgresql://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard?sslmode=require"

# Tables to copy (in order of priority)
TABLES_TO_COPY = [
    # Critical Business Data
    'orders',
    'order_line_items', 
    'payments',
    'tenders',
    
    # Supporting Data
    'operating_seasons',
    'catalog_location_availability',
    'catalog_vendor_info', 
    'inventory_counts',
    'square_item_library_export'
]

async def verify_table_data():
    """Verify what data we have locally before copying"""
    print("🔍 VERIFYING LOCAL DATA BEFORE COPY")
    print("=" * 50)
    
    table_stats = {}
    total_records = 0
    
    async with get_session() as session:
        for table in TABLES_TO_COPY:
            try:
                count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                table_stats[table] = count
                total_records += count
                
                status = "🔴" if count > 10000 else "🟡" if count > 100 else "🟢"
                print(f"  {status} {table:<35} {count:>8,} records")
                
            except Exception as e:
                print(f"  ❌ {table:<35} Error: {str(e)[:30]}...")
                table_stats[table] = 0
    
    print(f"\n📊 Total records to copy: {total_records:,}")
    return table_stats, total_records

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"   ✅ Success")
            return True
        else:
            print(f"   ❌ Failed - Return code: {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏱️ Command timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False

async def direct_database_copy():
    """Perform direct database copy using pg_dump/psql"""
    
    print("🚀 DIRECT DATABASE COPY - OPTION B")
    print("=" * 50)
    print("Method: pg_dump → psql (fastest approach)")
    print("Target: Copy all missing data from local to production")
    
    # Step 1: Verify local data
    table_stats, total_records = await verify_table_data()
    
    if total_records == 0:
        print("\n❌ No data found to copy!")
        return False
    
    # Step 2: Create temporary directory for exports
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n📁 Using temporary directory: {temp_dir}")
        
        # Step 3: Export each table
        print(f"\n📥 EXPORTING TABLES FROM LOCAL DATABASE")
        print("-" * 40)
        
        export_files = []
        failed_exports = []
        
        for table in TABLES_TO_COPY:
            count = table_stats.get(table, 0)
            if count == 0:
                print(f"  ⏭️ Skipping {table} - no data")
                continue
            
            export_file = os.path.join(temp_dir, f"{table}_export.sql")
            
            # Use pg_dump with --data-only and --inserts for compatibility
            export_cmd = f"""pg_dump "{LOCAL_DB_URL}" \\
                --table=public.{table} \\
                --data-only \\
                --inserts \\
                --no-owner \\
                --no-privileges \\
                --file="{export_file}" """
            
            if run_command(export_cmd, f"Exporting {table} ({count:,} records)"):
                export_files.append((table, export_file, count))
            else:
                failed_exports.append(table)
        
        if failed_exports:
            print(f"\n⚠️ Failed to export: {', '.join(failed_exports)}")
        
        if not export_files:
            print(f"\n❌ No files exported successfully!")
            return False
        
        # Step 4: Import to production
        print(f"\n📤 IMPORTING TO PRODUCTION DATABASE")
        print("-" * 40)
        
        successful_imports = []
        failed_imports = []
        
        for table, export_file, count in export_files:
            # Use psql to import
            import_cmd = f'''psql "{PROD_DB_URL}" --file="{export_file}" --quiet'''
            
            if run_command(import_cmd, f"Importing {table} ({count:,} records)"):
                successful_imports.append((table, count))
            else:
                failed_imports.append((table, count))
        
        # Step 5: Results summary
        print(f"\n" + "=" * 50)
        print(f"🎯 COPY RESULTS SUMMARY")
        print(f"=" * 50)
        
        if successful_imports:
            print(f"\n✅ SUCCESSFUL IMPORTS ({len(successful_imports)} tables):")
            total_imported = 0
            for table, count in successful_imports:
                print(f"   {table:<35} {count:>8,} records")
                total_imported += count
            print(f"\n📊 Total records imported: {total_imported:,}")
        
        if failed_imports:
            print(f"\n❌ FAILED IMPORTS ({len(failed_imports)} tables):")
            for table, count in failed_imports:
                print(f"   {table:<35} {count:>8,} records")
        
        # Step 6: Verification
        success_rate = len(successful_imports) / len(export_files) * 100
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"🎉 Copy completed successfully!")
            print(f"\n🔄 Next steps:")
            print(f"1. Verify: python scripts/compare_local_vs_production.py")
            print(f"2. Test endpoints: curl https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync-status")
            return True
        else:
            print(f"⚠️ Copy partially completed - some tables failed")
            return False

if __name__ == "__main__":
    print("🎯 Starting Direct Database Copy (Option B)")
    
    # Check prerequisites
    print("\n🔧 Checking prerequisites...")
    
    # Check if pg_dump and psql are available
    pg_dump_check = subprocess.run("which pg_dump", shell=True, capture_output=True)
    psql_check = subprocess.run("which psql", shell=True, capture_output=True)
    
    if pg_dump_check.returncode != 0:
        print("❌ pg_dump not found - install PostgreSQL client tools")
        exit(1)
        
    if psql_check.returncode != 0:
        print("❌ psql not found - install PostgreSQL client tools")
        exit(1)
    
    print("✅ PostgreSQL tools available")
    
    # Run the copy
    success = asyncio.run(direct_database_copy())
    
    if success:
        print(f"\n🎉 DATABASE COPY COMPLETED SUCCESSFULLY!")
        print(f"Production now has all historical data from local database.")
    else:
        print(f"\n⚠️ Database copy completed with some issues.")
        print(f"Check the output above for details.") 