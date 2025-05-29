#!/usr/bin/env python3
"""
Analyze local data to create a production sync strategy
"""
import asyncio
from sqlalchemy import text
from app.database import get_session

async def analyze_data_strategy():
    """Analyze local data and create sync strategy"""
    async with get_session() as session:
        
        print("🔍 ANALYZING LOCAL DATA FOR PRODUCTION SYNC STRATEGY")
        print("=" * 70)
        
        # Key tables analysis
        key_tables = {
            'orders': 'High Priority - Core business data',
            'order_line_items': 'High Priority - Linked to orders',
            'payments': 'High Priority - Financial data',
            'tenders': 'High Priority - Payment methods'
        }
        
        for table, priority in key_tables.items():
            print(f"\n📊 {table.upper()} - {priority}")
            print("-" * 50)
            
            try:
                # Get basic stats
                count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                total_count = count_result.scalar()
                
                if total_count == 0:
                    print(f"  ✅ Empty table - will sync all data from Square")
                    continue
                
                print(f"  📈 Total records: {total_count:,}")
                
                # Get date range for time-based tables
                if table in ['orders', 'payments']:
                    date_column = 'created_at'
                elif table == 'tenders':
                    date_column = 'created_at'
                else:
                    date_column = None
                
                if date_column:
                    date_result = await session.execute(text(f"""
                        SELECT 
                            MIN({date_column}) as earliest,
                            MAX({date_column}) as latest,
                            COUNT(*) as total
                        FROM "{table}"
                        WHERE {date_column} IS NOT NULL
                    """))
                    date_stats = date_result.fetchone()
                    
                    if date_stats and date_stats[0]:
                        print(f"  📅 Date range: {date_stats[0].strftime('%Y-%m-%d')} to {date_stats[1].strftime('%Y-%m-%d')}")
                        print(f"  ⏱️  Time span: {(date_stats[1] - date_stats[0]).days} days")
                
                # Get recent activity (last 30 days)
                if date_column:
                    recent_result = await session.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM "{table}"
                        WHERE {date_column} >= NOW() - INTERVAL '30 days'
                    """))
                    recent_count = recent_result.scalar()
                    print(f"  🔥 Recent (30 days): {recent_count:,} records")
                
                # Sample some IDs to check format
                sample_result = await session.execute(text(f'SELECT id FROM "{table}" LIMIT 3'))
                sample_ids = [row[0] for row in sample_result.fetchall()]
                print(f"  🔑 Sample IDs: {sample_ids}")
                
            except Exception as e:
                print(f"  ❌ Error analyzing {table}: {str(e)}")
        
        print(f"\n" + "=" * 70)
        print("🎯 PRODUCTION SYNC STRATEGY")
        print("=" * 70)
        
        print(f"""
📋 PHASE 1: IMMEDIATE ACTION (High-Impact Tables)
   Target: Get production to match local for critical business data
   
   1️⃣ ORDERS SYNC
      • Local has 30,390 orders
      • These contain core business transactions
      • Strategy: Historical sync + incremental
      
   2️⃣ ORDER LINE ITEMS SYNC  
      • Local has 159,131 line items
      • Essential for detailed transaction analysis
      • Strategy: Sync with orders (parent-child relationship)
      
   3️⃣ PAYMENTS SYNC
      • Local has 49 payments  
      • Critical financial data
      • Strategy: Full historical sync
      
   4️⃣ TENDERS SYNC
      • Local has 2,493 tenders
      • Payment method details
      • Strategy: Full historical sync

📋 PHASE 2: SUPPORT TABLES (Medium Priority)
   Target: Enable full report functionality
   
   • transactions (currently empty)
   • order_fulfillments (currently empty) 
   • order_refunds (currently empty)
   • order_returns (currently empty)

📋 PHASE 3: DERIVED DATA (Low Priority)
   Target: Rebuild computed tables from Square data
   
   • catalog_location_availability (7,801 records)
   • catalog_vendor_info (989 records) 
   • inventory_counts (4,932 records)
   • square_item_library_export (986 records)

🚀 IMPLEMENTATION APPROACH:

Option A: DIRECT DATABASE COPY (Fastest)
   • Export tables from local database
   • Import directly to production
   • Pro: Immediate sync, all historical data
   • Con: Bypasses API, may miss recent changes

Option B: ENHANCED API SYNC (Recommended)
   • Extend incremental sync for orders/payments APIs
   • Use historical date range to get all data
   • Pro: Uses official API, gets latest data
   • Con: May be slower, API rate limits

Option C: HYBRID APPROACH (Best of both)
   • Copy historical data directly (older than 30 days)
   • Use API sync for recent data (last 30 days)
   • Pro: Fast + accurate, best data integrity
   • Con: More complex implementation
        """)
        
        # Get production comparison
        print(f"\n💡 RECOMMENDATION:")
        print(f"Start with Option B (Enhanced API Sync) because:")
        print(f"• Ensures data integrity through official Square API")
        print(f"• Can be automated for ongoing maintenance")
        print(f"• Validates against current Square state")
        print(f"• Can be tested incrementally")

if __name__ == "__main__":
    asyncio.run(analyze_data_strategy()) 