#!/usr/bin/env python3
"""
Check local database tables and compare with production
"""
import asyncio
import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_session

async def check_local_tables():
    """Check all tables in local database"""
    try:
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
            
            print("📊 Local Database Tables:")
            print("=" * 50)
            
            total_records = 0
            for table in tables:
                try:
                    count_result = await session.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = count_result.scalar()
                    print(f"  {table:<30} {count:>10,} records")
                    total_records += count
                except Exception as e:
                    print(f"  {table:<30} {'ERROR':>10} - {str(e)}")
            
            print("=" * 50)
            print(f"  {'TOTAL RECORDS':<30} {total_records:>10,}")
            
            # Compare with known production counts
            production_counts = {
                "locations": 9,
                "catalog_categories": 23, 
                "catalog_items": 865,
                "catalog_variations": 986,
                "catalog_inventory": 6960
            }
            
            print("\n🔄 Production vs Local Comparison:")
            print("=" * 60)
            print(f"{'Table':<25} {'Production':<12} {'Local':<12} {'Status':<10}")
            print("-" * 60)
            
            for table, prod_count in production_counts.items():
                try:
                    local_result = await session.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    local_count = local_result.scalar()
                    
                    if local_count == prod_count:
                        status = "✅ MATCH"
                    elif local_count == 0:
                        status = "❌ EMPTY"
                    elif local_count < prod_count:
                        status = "⚠️ BEHIND"
                    else:
                        status = "📈 AHEAD"
                    
                    print(f"{table:<25} {prod_count:<12,} {local_count:<12,} {status}")
                except Exception as e:
                    print(f"{table:<25} {prod_count:<12,} {'ERROR':<12} ❌ MISSING")
            
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error checking local tables: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(check_local_tables()) 