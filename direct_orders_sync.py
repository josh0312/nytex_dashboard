#!/usr/bin/env python3
"""
Direct Orders Sync
Runs the same incremental sync logic directly to avoid web API transaction issues.
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

async def direct_orders_sync():
    """Run orders sync directly using incremental sync logic"""
    
    print("🚀 DIRECT ORDERS SYNC")
    print("=" * 50)
    print("Using the same logic as incremental sync but running directly")
    print()
    
    # Configuration
    square_access_token = os.getenv('SQUARE_ACCESS_TOKEN')
    square_base_url = os.getenv('SQUARE_BASE_URL', 'https://connect.squareup.com')
    
    if not square_access_token:
        print("❌ SQUARE_ACCESS_TOKEN environment variable is required")
        return False
    
    # Database connection
    engine = create_engine('postgresql://nytex_user:NytexSecure2024!@localhost:5434/square_data_sync')
    
    try:
        # Step 1: Get locations
        print("📍 Step 1: Getting active locations...")
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            locations_url = f"{square_base_url}/v2/locations"
            headers = {'Authorization': f'Bearer {square_access_token}'}
            
            async with session.get(locations_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Failed to fetch locations: {response.status} - {error_text}")
                    return False
                
                locations_data = await response.json()
                location_ids = [loc['id'] for loc in locations_data.get('locations', [])]
                print(f"✅ Found {len(location_ids)} locations")
            
            # Step 2: Fetch orders using incremental sync approach
            print("\n🔄 Step 2: Fetching orders (incremental sync approach)...")
            print("   Using: updated_at filter with start_at = None (gets ALL orders)")
            
            url = f"{square_base_url}/v2/orders/search"
            headers = {
                'Authorization': f'Bearer {square_access_token}',
                'Content-Type': 'application/json'
            }
            
            # This is EXACTLY what incremental sync does when last_sync is None
            payload = {
                "location_ids": location_ids,
                "query": {
                    "filter": {
                        "updated_at": {
                            "start_at": None,  # This gets ALL orders (no date filtering)
                            "end_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                },
                "limit": 500  # Maximum allowed by Square API
            }
            
            all_orders = []
            cursor = None
            page = 1
            
            while True:
                if cursor:
                    payload["cursor"] = cursor
                elif "cursor" in payload:
                    del payload["cursor"]
                
                print(f"   📄 Fetching page {page}...")
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        orders = data.get('orders', [])
                        all_orders.extend(orders)
                        
                        print(f"      Retrieved {len(orders)} orders (total: {len(all_orders):,})")
                        
                        # Check for more pages
                        cursor = data.get('cursor')
                        if not cursor:
                            break
                        
                        page += 1
                        
                        # Continue until all orders are fetched
                        # No limit - get all orders
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ API Error: {response.status} - {error_text}")
                        return False
            
            print(f"\n✅ Total orders fetched: {len(all_orders):,}")
            
            if not all_orders:
                print("⚠️  No orders found")
                return True
            
            # Step 3: Insert orders into database
            print("\n💾 Step 3: Inserting orders into database...")
            
            with engine.connect() as conn:
                # Start a fresh transaction
                trans = conn.begin()
                
                try:
                    inserted_count = 0
                    updated_count = 0
                    
                    for i, order_data in enumerate(all_orders):
                        if i % 100 == 0:
                            print(f"   Processing order {i+1:,}/{len(all_orders):,}...")
                        
                        # Parse timestamps
                        def parse_timestamp(timestamp_str):
                            if not timestamp_str:
                                return None
                            try:
                                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                return dt.astimezone(timezone.utc).replace(tzinfo=None)
                            except:
                                return None
                        
                        # Insert order using upsert
                        try:
                            result = conn.execute(text("""
                                INSERT INTO orders (
                                    id, location_id, created_at, updated_at, closed_at,
                                    state, version, total_money, total_tax_money, total_discount_money,
                                    net_amounts, source, return_amounts, order_metadata
                                ) VALUES (
                                    :id, :location_id, :created_at, :updated_at, :closed_at,
                                    :state, :version, :total_money, :total_tax_money, :total_discount_money,
                                    :net_amounts, :source, :return_amounts, :order_metadata
                                )
                                ON CONFLICT (id) DO UPDATE SET
                                    location_id = EXCLUDED.location_id,
                                    updated_at = EXCLUDED.updated_at,
                                    closed_at = EXCLUDED.closed_at,
                                    state = EXCLUDED.state,
                                    version = EXCLUDED.version,
                                    total_money = EXCLUDED.total_money,
                                    total_tax_money = EXCLUDED.total_tax_money,
                                    total_discount_money = EXCLUDED.total_discount_money,
                                    net_amounts = EXCLUDED.net_amounts,
                                    source = EXCLUDED.source,
                                    return_amounts = EXCLUDED.return_amounts,
                                    order_metadata = EXCLUDED.order_metadata
                                RETURNING (xmax = 0) AS inserted
                            """), {
                                'id': order_data['id'],
                                'location_id': order_data.get('location_id'),
                                'created_at': parse_timestamp(order_data.get('created_at')),
                                'updated_at': parse_timestamp(order_data.get('updated_at')),
                                'closed_at': parse_timestamp(order_data.get('closed_at')),
                                'state': order_data.get('state'),
                                'version': order_data.get('version'),
                                'total_money': json.dumps(order_data.get('total_money', {})),
                                'total_tax_money': json.dumps(order_data.get('total_tax_money', {})),
                                'total_discount_money': json.dumps(order_data.get('total_discount_money', {})),
                                'net_amounts': json.dumps(order_data.get('net_amounts', {})),
                                'source': json.dumps(order_data.get('source', {})),
                                'return_amounts': json.dumps(order_data.get('return_amounts', {})),
                                'order_metadata': json.dumps(order_data.get('metadata', {}))
                            })
                            
                            # Check if it was an insert or update
                            was_inserted = result.fetchone()[0]
                            if was_inserted:
                                inserted_count += 1
                            else:
                                updated_count += 1
                                
                        except Exception as e:
                            print(f"   ❌ Error inserting order {order_data.get('id', 'unknown')}: {e}")
                            continue
                    
                    # Commit the transaction
                    trans.commit()
                    
                    print(f"\n✅ Database operations completed:")
                    print(f"   📈 New orders inserted: {inserted_count:,}")
                    print(f"   🔄 Existing orders updated: {updated_count:,}")
                    print(f"   📊 Total processed: {inserted_count + updated_count:,}")
                    
                    # Check final count
                    result = conn.execute(text('SELECT COUNT(*) FROM orders'))
                    final_count = result.fetchone()[0]
                    print(f"   🎯 Final order count: {final_count:,}")
                    
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    print(f"❌ Database transaction failed: {e}")
                    return False
    
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False

async def main():
    """Main function"""
    success = await direct_orders_sync()
    
    if success:
        print("\n🎉 DIRECT ORDERS SYNC COMPLETED SUCCESSFULLY!")
        print("✅ Orders have been synced using the incremental approach")
    else:
        print("\n❌ Direct orders sync failed")

if __name__ == "__main__":
    asyncio.run(main()) 