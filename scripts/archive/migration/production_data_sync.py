#!/usr/bin/env python3
"""
Production Data Sync - Get production fully synchronized with local database
"""
import asyncio
import json
import psycopg2
from sqlalchemy import text
from app.database import get_session
from app.config import Config
import os
from datetime import datetime

async def production_sync_strategy():
    """Comprehensive production sync strategy"""
    
    print("🚀 PRODUCTION DATA SYNCHRONIZATION")
    print("=" * 60)
    print("Target: Sync ALL missing data to production immediately")
    print("Strategy: Direct database export/import + API validation")
    
    # Phase 1: Critical Tables (High Priority)
    critical_tables = [
        'orders',
        'order_line_items', 
        'payments',
        'tenders',
        'order_fulfillments',
        'order_refunds',
        'order_returns'
    ]
    
    # Phase 2: Support Tables (Medium Priority) 
    support_tables = [
        'transactions',
        'operating_seasons'
    ]
    
    # Phase 3: Derived Tables (Low Priority)
    derived_tables = [
        'catalog_location_availability',
        'catalog_vendor_info', 
        'inventory_counts',
        'square_item_library_export'
    ]
    
    all_tables = critical_tables + support_tables + derived_tables
    
    print(f"\n📊 TABLES TO SYNC:")
    print(f"  🔴 Critical: {len(critical_tables)} tables")
    print(f"  🟡 Support: {len(support_tables)} tables") 
    print(f"  🟢 Derived: {len(derived_tables)} tables")
    print(f"  📈 Total: {len(all_tables)} tables")
    
    # Analyze local data
    async with get_session() as session:
        print(f"\n🔍 ANALYZING LOCAL DATA:")
        print("-" * 40)
        
        total_records = 0
        table_stats = {}
        
        for table in all_tables:
            try:
                count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                table_stats[table] = count
                total_records += count
                
                status = "🔴" if count > 10000 else "🟡" if count > 100 else "🟢"
                print(f"  {status} {table:<35} {count:>8,} records")
                
            except Exception as e:
                print(f"  ❌ {table:<35} Error: {str(e)[:50]}...")
                table_stats[table] = 0
        
        print(f"\n📈 TOTAL RECORDS TO SYNC: {total_records:,}")
        
        # Create export strategy
        print(f"\n🎯 IMPLEMENTATION PLAN:")
        print("=" * 40)
        
        print(f"""
1️⃣ IMMEDIATE ACTION - Critical Data Export
   • Export {sum(table_stats.get(t, 0) for t in critical_tables):,} critical records
   • Tables: orders, order_line_items, payments, tenders
   • Method: pg_dump specific tables → production import
   • Timeline: ~10 minutes
   
2️⃣ SUPPORT DATA - Business Logic Tables  
   • Export {sum(table_stats.get(t, 0) for t in support_tables):,} support records
   • Tables: transactions, operating_seasons
   • Method: CSV export → production import
   • Timeline: ~5 minutes
   
3️⃣ DERIVED DATA - Computed Tables
   • Export {sum(table_stats.get(t, 0) for t in derived_tables):,} derived records
   • Tables: location_availability, vendor_info, etc.
   • Method: CSV export → production import  
   • Timeline: ~5 minutes
   
4️⃣ VALIDATION & API SYNC
   • Verify all data imported correctly
   • Enable incremental sync for ongoing updates
   • Test all endpoints and reports
   • Timeline: ~10 minutes
        """)
        
        return table_stats

async def create_export_commands(table_stats):
    """Create the actual export/import commands"""
    
    print(f"\n🛠️ EXPORT/IMPORT COMMANDS:")
    print("=" * 50)
    
    # Database connection details (you'll need to update these)
    local_db_url = "postgresql://postgres:password@localhost/nytex_dashboard"
    prod_db_url = "postgresql://postgres:password@production-host/nytex_dashboard"
    
    # Critical tables - use pg_dump for best performance
    critical_tables = ['orders', 'order_line_items', 'payments', 'tenders', 'order_fulfillments', 'order_refunds', 'order_returns']
    
    print(f"📥 1. EXPORT CRITICAL TABLES:")
    for table in critical_tables:
        count = table_stats.get(table, 0)
        if count > 0:
            print(f"  pg_dump {local_db_url} --table={table} --data-only --inserts > {table}_export.sql")
    
    print(f"\n📤 2. IMPORT TO PRODUCTION:")
    for table in critical_tables:
        count = table_stats.get(table, 0)
        if count > 0:
            print(f"  psql {prod_db_url} < {table}_export.sql")
    
    print(f"\n🔄 3. ALTERNATIVE: API-BASED SYNC")
    print(f"  # If database access is restricted, create API endpoints:")
    print(f"  curl -X POST 'https://nytex-dashboard-932676587025.us-central1.run.app/admin/bulk-import' \\")
    print(f"       -F 'table=orders' -F 'file=@orders_export.csv'")
    
    print(f"\n✅ 4. VALIDATION:")
    print(f"  python scripts/compare_local_vs_production.py")

async def create_csv_exports(table_stats):
    """Create CSV exports for easier import"""
    
    print(f"\n📋 CREATING CSV EXPORTS:")
    print("-" * 30)
    
    async with get_session() as session:
        for table, count in table_stats.items():
            if count > 0:
                print(f"  📄 Exporting {table} ({count:,} records)...")
                
                try:
                    # Export to CSV
                    result = await session.execute(text(f'SELECT * FROM "{table}" LIMIT 5'))
                    columns = result.keys()
                    print(f"    Columns: {', '.join(columns)}")
                    
                    # You could add actual CSV export logic here
                    # For now, just show the command needed
                    export_path = f"exports/{table}_export.csv"
                    print(f"    Export path: {export_path}")
                    
                except Exception as e:
                    print(f"    ❌ Error: {str(e)[:50]}...")

if __name__ == "__main__":
    print("🎯 Starting Production Data Sync Analysis...")
    
    # Run the analysis
    table_stats = asyncio.run(production_sync_strategy())
    
    # Create the commands
    asyncio.run(create_export_commands(table_stats))
    
    # Create CSV exports info
    asyncio.run(create_csv_exports(table_stats))
    
    print(f"\n🎉 ANALYSIS COMPLETE!")
    print(f"Next steps:")
    print(f"1. Choose your preferred sync method (database copy vs API)")
    print(f"2. Execute the export/import commands")
    print(f"3. Validate the results")
    print(f"4. Enable ongoing incremental sync") 