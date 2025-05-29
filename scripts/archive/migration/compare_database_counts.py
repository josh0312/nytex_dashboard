"""
Compare row counts between production and local databases
"""
import asyncio
import os
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config

async def get_production_counts():
    """Get row counts from production database"""
    try:
        # Production database connection
        prod_url = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
        
        print("🌐 Checking production database...")
        engine = create_async_engine(prod_url, echo=False, connect_args={"ssl": "require"})
        
        async with engine.begin() as conn:
            # Get all table names
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f"   Found {len(tables)} tables in production")
            
            # Get row counts for each table
            counts = {}
            for table in tables:
                try:
                    count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    counts[table] = count
                except Exception as e:
                    counts[table] = f"ERROR: {str(e)}"
        
        await engine.dispose()
        return counts
        
    except Exception as e:
        print(f"❌ Error checking production: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

def get_local_counts():
    """Get row counts from local database"""
    try:
        # Use the same database URL logic as the main app
        local_db_url = Config.SQLALCHEMY_DATABASE_URI
        print(f"   Local DB URL: {local_db_url}")
        
        # Convert to sync URL for this script
        sync_url = local_db_url.replace('postgresql+asyncpg://', 'postgresql://')
        print(f"   Sync URL: {sync_url}")
        
        print("🏠 Checking local database...")
        
        engine = create_engine(sync_url, echo=False)
        
        with engine.begin() as conn:
            # Get all table names
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f"   Found {len(tables)} tables in local")
            
            # Get row counts for each table
            counts = {}
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    counts[table] = count
                except Exception as e:
                    counts[table] = f"ERROR: {str(e)}"
        
        engine.dispose()
        return counts
        
    except Exception as e:
        print(f"❌ Error checking local: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

def format_count(count):
    """Format count for display"""
    if isinstance(count, str):  # Error message
        return count
    elif count == 0:
        return "0"
    elif count < 1000:
        return str(count)
    else:
        return f"{count:,}"

async def main():
    """Main function to compare databases"""
    print("📊 Database Row Count Comparison")
    print("=" * 80)
    
    # Get counts from both databases
    prod_counts = await get_production_counts()
    local_counts = get_local_counts()
    
    if not prod_counts or not local_counts:
        print("❌ Failed to get data from one or both databases")
        return
    
    # Get all unique table names
    all_tables = sorted(set(prod_counts.keys()) | set(local_counts.keys()))
    
    print(f"\n📋 Row Count Comparison ({len(all_tables)} tables)")
    print("=" * 80)
    print(f"{'Table Name':<30} {'Production':<15} {'Local':<15} {'Difference':<15} {'Status'}")
    print("-" * 80)
    
    total_prod = 0
    total_local = 0
    tables_match = 0
    tables_differ = 0
    
    for table in all_tables:
        prod_count = prod_counts.get(table, "MISSING")
        local_count = local_counts.get(table, "MISSING")
        
        # Calculate difference and status
        if prod_count == "MISSING":
            difference = "N/A"
            status = "❌ Missing in Prod"
        elif local_count == "MISSING":
            difference = "N/A"
            status = "⚠️  Missing in Local"
        elif isinstance(prod_count, str) or isinstance(local_count, str):
            difference = "ERROR"
            status = "❌ Error"
        else:
            difference = prod_count - local_count
            total_prod += prod_count
            total_local += local_count
            
            if difference == 0:
                status = "✅ Match"
                tables_match += 1
            elif abs(difference) <= 5:  # Small difference
                status = "⚠️  Close"
                tables_differ += 1
            else:
                status = "❌ Different"
                tables_differ += 1
            
            # Format difference
            if difference == 0:
                difference = "0"
            elif difference > 0:
                difference = f"+{difference:,}"
            else:
                difference = f"{difference:,}"
        
        print(f"{table:<30} {format_count(prod_count):<15} {format_count(local_count):<15} {difference:<15} {status}")
    
    # Summary
    print("-" * 80)
    print(f"{'TOTALS':<30} {total_prod:,} {total_local:,} {total_prod - total_local:+,}")
    
    print(f"\n📈 Summary:")
    print(f"   Tables that match: {tables_match}")
    print(f"   Tables that differ: {tables_differ}")
    print(f"   Total production rows: {total_prod:,}")
    print(f"   Total local rows: {total_local:,}")
    print(f"   Overall difference: {total_prod - total_local:+,}")
    
    # Key insights
    print(f"\n🔍 Key Insights:")
    
    # Check critical tables
    critical_tables = ['catalog_items', 'catalog_variations', 'catalog_categories', 'locations', 'catalog_inventory']
    
    for table in critical_tables:
        if table in prod_counts and table in local_counts:
            prod_val = prod_counts[table]
            local_val = local_counts[table]
            if isinstance(prod_val, int) and isinstance(local_val, int):
                if prod_val == 0 and local_val > 0:
                    print(f"   ⚠️  {table}: Production empty but local has {local_val:,} rows")
                elif prod_val > 0 and local_val == 0:
                    print(f"   ⚠️  {table}: Local empty but production has {prod_val:,} rows")
                elif abs(prod_val - local_val) > 100:
                    print(f"   ⚠️  {table}: Large difference ({prod_val:,} vs {local_val:,})")
                elif prod_val > 0 and local_val > 0:
                    print(f"   ✅ {table}: Both populated ({prod_val:,} vs {local_val:,})")

if __name__ == "__main__":
    asyncio.run(main()) 