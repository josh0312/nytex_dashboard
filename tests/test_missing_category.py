#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def test_missing_category_query():
    async with get_session() as session:
        # Read the query from file
        with open('app/database/queries/missing_category_inventory.sql', 'r') as f:
            query = f.read()
        
        print("🔍 TESTING MISSING CATEGORY QUERY")
        print("=" * 60)
        
        try:
            result = await session.execute(text(query))
            records = result.fetchall()
            
            print(f"📊 TOTAL MISSING CATEGORY ITEMS: {len(records)}")
            
            if records:
                print(f"\n📋 SAMPLE RESULTS (first 10):")
                print(f"{'Item Name':<40} {'Vendor':<20} {'Price':<12} {'Quantity':<10}")
                print("-" * 82)
                
                for i, record in enumerate(records[:10]):
                    item_name = record.item_name[:37] + "..." if len(record.item_name) > 40 else record.item_name
                    vendor = record.vendor_name[:17] + "..." if len(record.vendor_name) > 20 else record.vendor_name
                    price = record.price
                    quantity = record.quantity
                    
                    print(f"{item_name:<40} {vendor:<20} {price:<12} {quantity:<10}")
                
                if len(records) > 10:
                    print(f"\n... and {len(records) - 10} more items")
                
                # Show vendor breakdown
                vendor_counts = {}
                for record in records:
                    vendor = record.vendor_name
                    vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
                
                print(f"\n📈 VENDOR BREAKDOWN:")
                for vendor, count in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {vendor}: {count} items")
                
                # Show quantity stats
                quantities = [record.quantity for record in records]
                total_qty = sum(quantities)
                avg_qty = total_qty / len(quantities) if quantities else 0
                max_qty = max(quantities) if quantities else 0
                min_qty = min(quantities) if quantities else 0
                
                print(f"\n📊 QUANTITY STATISTICS:")
                print(f"  Total Quantity: {total_qty:,}")
                print(f"  Average Quantity: {avg_qty:.1f}")
                print(f"  Max Quantity: {max_qty:,}")
                print(f"  Min Quantity: {min_qty:,}")
            else:
                print("No items found with missing categories")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_missing_category_query()) 