#!/usr/bin/env python3
"""
Analyze missing tables in production and create sync strategy
"""
import asyncio
from sqlalchemy import text, inspect
from app.database import get_session

async def analyze_table_schemas():
    """Analyze each table's structure and data patterns"""
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
        
        print("📋 COMPLETE TABLE ANALYSIS FOR PRODUCTION SYNC")
        print("=" * 80)
        
        # Categories of tables
        square_api_tables = []
        derived_tables = []
        system_tables = []
        unknown_tables = []
        
        for table in tables:
            print(f"\n🔍 Analyzing: {table}")
            print("-" * 40)
            
            # Get row count
            count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = count_result.scalar()
            
            # Get sample data (first 3 rows)
            try:
                sample_result = await session.execute(text(f'SELECT * FROM "{table}" LIMIT 3'))
                sample_rows = sample_result.fetchall()
                
                # Get column info
                columns_result = await session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    ORDER BY ordinal_position
                """))
                columns = columns_result.fetchall()
                
                print(f"  📊 Records: {count:,}")
                print(f"  🏗️  Columns: {len(columns)}")
                
                # Analyze table purpose based on name and structure
                table_category = categorize_table(table, columns, sample_rows)
                print(f"  🏷️  Category: {table_category}")
                
                # Show key columns
                key_columns = [col[0] for col in columns[:5]]  # First 5 columns
                print(f"  🔑 Key columns: {', '.join(key_columns)}")
                
                # Determine sync strategy
                sync_strategy = determine_sync_strategy(table, table_category, count)
                print(f"  🎯 Sync Strategy: {sync_strategy}")
                
                # Add to appropriate category
                if table_category == "Square API":
                    square_api_tables.append((table, count, sync_strategy))
                elif table_category == "Derived/Computed":
                    derived_tables.append((table, count, sync_strategy))
                elif table_category == "System":
                    system_tables.append((table, count, sync_strategy))
                else:
                    unknown_tables.append((table, count, sync_strategy))
                    
            except Exception as e:
                print(f"  ❌ Error analyzing: {str(e)}")
                unknown_tables.append((table, count, "ERROR - Manual Review"))
        
        # Summary report
        print("\n" + "=" * 80)
        print("📊 SYNC STRATEGY SUMMARY")
        print("=" * 80)
        
        print(f"\n🔵 SQUARE API TABLES ({len(square_api_tables)}):")
        print("   These need direct Square API sync")
        for table, count, strategy in square_api_tables:
            print(f"   - {table:<30} {count:>8,} records | {strategy}")
        
        print(f"\n🟡 DERIVED/COMPUTED TABLES ({len(derived_tables)}):")
        print("   These are generated from Square data")
        for table, count, strategy in derived_tables:
            print(f"   - {table:<30} {count:>8,} records | {strategy}")
        
        print(f"\n🟢 SYSTEM TABLES ({len(system_tables)}):")
        print("   These are infrastructure/metadata")
        for table, count, strategy in system_tables:
            print(f"   - {table:<30} {count:>8,} records | {strategy}")
            
        if unknown_tables:
            print(f"\n🔴 UNKNOWN/REVIEW TABLES ({len(unknown_tables)}):")
            print("   These need manual investigation")
            for table, count, strategy in unknown_tables:
                print(f"   - {table:<30} {count:>8,} records | {strategy}")
        
        # Priority recommendations
        print(f"\n🎯 IMPLEMENTATION PRIORITY:")
        print("   1. Square API tables (extend incremental sync)")
        print("   2. High-value derived tables (orders, payments)")
        print("   3. System tables (sync_state, alembic)")
        print("   4. Remaining derived tables")

def categorize_table(table_name, columns, sample_rows):
    """Categorize table based on name and structure"""
    
    # System tables
    if table_name in ['alembic_version', 'sync_state']:
        return "System"
    
    # Clear Square API tables (already syncing)
    if table_name in ['locations', 'catalog_categories', 'catalog_items', 'catalog_variations', 'catalog_inventory', 'vendors']:
        return "Square API"
    
    # Likely Square API tables (need to add to sync)
    if any(keyword in table_name for keyword in ['order', 'payment', 'tender', 'transaction']):
        return "Square API"
    
    # Derived/computed tables
    if any(keyword in table_name for keyword in ['_export', '_info', '_availability', '_counts', 'square_sales']):
        return "Derived/Computed"
        
    # Operating seasons looks like business data
    if table_name == 'operating_seasons':
        return "Business Data"
    
    return "Unknown"

def determine_sync_strategy(table_name, category, count):
    """Determine the best sync strategy for each table"""
    
    if category == "System":
        if table_name == 'sync_state':
            return "AUTO CREATED - No sync needed"
        elif table_name == 'alembic_version':
            return "DEPLOY ONLY - Migration artifact"
    
    elif category == "Square API":
        if table_name in ['locations', 'catalog_categories', 'catalog_items', 'catalog_variations', 'catalog_inventory']:
            return "✅ ALREADY SYNCED - Incremental working"
        elif table_name == 'vendors':
            return "🔄 ADD TO INCREMENTAL - 404 error to fix"
        elif 'order' in table_name:
            return "🆕 ADD ORDERS API - High priority"
        elif 'payment' in table_name or 'tender' in table_name:
            return "🆕 ADD PAYMENTS API - High priority"
        elif 'transaction' in table_name:
            return "🆕 ADD TRANSACTIONS API - Medium priority"
    
    elif category == "Derived/Computed":
        if count == 0:
            return "⏭️ SKIP - Empty table"
        elif count < 100:
            return "📊 ONE-TIME COPY - Small dataset"
        else:
            return "🔄 REBUILD FROM SOURCE - Large derived data"
    
    elif category == "Business Data":
        return "📋 MANUAL REVIEW - Business logic needed"
    
    return "❓ INVESTIGATE - Unknown source"

if __name__ == "__main__":
    asyncio.run(analyze_table_schemas()) 