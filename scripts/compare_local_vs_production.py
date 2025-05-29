#!/usr/bin/env python3
"""
Compare database tables between local and production environments
"""
import asyncio
import requests
import sys
from sqlalchemy import text
from app.database import get_session

async def get_local_table_counts():
    """Get all table counts from local database"""
    async with get_session() as session:
        # Get all table names
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result.fetchall()]
        
        table_counts = {}
        for table in tables:
            try:
                result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                table_counts[table] = count
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        return table_counts

def get_production_table_counts():
    """Get table counts from production via API"""
    try:
        response = requests.get("https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync-status")
        data = response.json()
        return data.get('table_counts', {})
    except Exception as e:
        print(f"Error fetching production data: {e}")
        return {}

async def main():
    print("🔍 Comparing Local vs Production Database Tables")
    print("=" * 80)
    
    # Get local counts
    print("📊 Fetching local table counts...")
    local_counts = await get_local_table_counts()
    
    # Get production counts
    print("🌐 Fetching production table counts...")
    prod_counts = get_production_table_counts()
    
    # Combine all table names
    all_tables = set(local_counts.keys()) | set(prod_counts.keys())
    
    print(f"\n📋 Database Comparison Summary:")
    print("=" * 80)
    print(f"{'Table Name':<35} {'Production':<12} {'Local':<12} {'Status':<15}")
    print("-" * 80)
    
    total_prod = 0
    total_local = 0
    
    for table in sorted(all_tables):
        local_count = local_counts.get(table, 0)
        prod_count = prod_counts.get(table, 0)
        
        # Handle error cases
        if isinstance(local_count, str):
            local_display = "ERROR"
        else:
            local_display = f"{local_count:,}"
            total_local += local_count
            
        if isinstance(prod_count, str):
            prod_display = "ERROR"
        else:
            prod_display = f"{prod_count:,}"
            total_prod += prod_count
        
        # Determine status
        if local_count == prod_count:
            status = "✅ MATCH"
        elif table not in prod_counts:
            status = "❌ MISSING PROD"
        elif table not in local_counts:
            status = "❌ MISSING LOCAL"
        elif isinstance(local_count, int) and isinstance(prod_count, int):
            if local_count > prod_count:
                status = "📈 LOCAL AHEAD"
            else:
                status = "📉 PROD AHEAD"
        else:
            status = "❓ UNKNOWN"
        
        print(f"{table:<35} {prod_display:<12} {local_display:<12} {status:<15}")
    
    print("-" * 80)
    print(f"{'TOTALS':<35} {total_prod:<12,} {total_local:<12,}")
    print("=" * 80)
    
    # Analysis
    print(f"\n📊 Analysis:")
    print(f"  🌐 Production total records: {total_prod:,}")
    print(f"  💻 Local total records: {total_local:,}")
    
    if total_local > total_prod:
        diff = total_local - total_prod
        percentage = (diff / total_prod * 100) if total_prod > 0 else 0
        print(f"  📈 Local is ahead by: {diff:,} records ({percentage:.1f}%)")
    elif total_prod > total_local:
        diff = total_prod - total_local
        percentage = (diff / total_local * 100) if total_local > 0 else 0
        print(f"  📉 Production is ahead by: {diff:,} records ({percentage:.1f}%)")
    else:
        print(f"  ✅ Both environments have equal record counts")
    
    # Tables only in local
    local_only = set(local_counts.keys()) - set(prod_counts.keys())
    if local_only:
        print(f"\n📋 Tables only in LOCAL ({len(local_only)}):")
        for table in sorted(local_only):
            count = local_counts[table]
            if isinstance(count, int):
                print(f"  - {table}: {count:,} records")
            else:
                print(f"  - {table}: {count}")
    
    # Tables only in production
    prod_only = set(prod_counts.keys()) - set(local_counts.keys())
    if prod_only:
        print(f"\n🌐 Tables only in PRODUCTION ({len(prod_only)}):")
        for table in sorted(prod_only):
            count = prod_counts[table]
            if isinstance(count, int):
                print(f"  - {table}: {count:,} records")
            else:
                print(f"  - {table}: {count}")

if __name__ == "__main__":
    asyncio.run(main()) 