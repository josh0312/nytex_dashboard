#!/usr/bin/env python3
"""
Historical Orders Sync Script
Syncs all orders from Square API from January 2018 to present in manageable chunks.
Handles API rate limits, pagination, and database insertion efficiently.
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import aiohttp
import time
from dataclasses import dataclass

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_async_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.database import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SyncConfig:
    """Configuration for the historical sync"""
    start_date: datetime = datetime(2018, 1, 1, tzinfo=timezone.utc)
    end_date: datetime = datetime.now(timezone.utc)
    chunk_size_days: int = 30  # Process 30 days at a time
    batch_size: int = 100      # Insert 100 orders at a time
    max_requests_per_minute: int = 100  # Square API rate limit
    request_delay: float = 0.6  # Delay between requests (60s / 100 requests)

class HistoricalOrdersSync:
    def __init__(self):
        self.config = SyncConfig()
        self.square_access_token = os.getenv('SQUARE_ACCESS_TOKEN')
        self.square_base_url = os.getenv('SQUARE_BASE_URL', 'https://connect.squareup.com')
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.square_access_token:
            raise ValueError("SQUARE_ACCESS_TOKEN environment variable is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.engine = create_async_engine(self.database_url, echo=False)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        
        # Track progress
        self.total_orders_synced = 0
        self.total_chunks_processed = 0
        self.errors = []
        
        logger.info(f"Historical Orders Sync initialized")
        logger.info(f"Date range: {self.config.start_date} to {self.config.end_date}")
        logger.info(f"Chunk size: {self.config.chunk_size_days} days")
        logger.info(f"Rate limit: {self.config.max_requests_per_minute} requests/minute")

    async def run_sync(self) -> Dict[str, Any]:
        """Run the complete historical sync"""
        start_time = time.time()
        logger.info("🚀 Starting historical orders sync...")
        
        try:
            # Get active locations first
            locations = await self._get_active_locations()
            if not locations:
                raise Exception("No active locations found")
            
            location_ids = [loc['id'] for loc in locations]
            logger.info(f"Found {len(location_ids)} active locations: {[loc['name'] for loc in locations]}")
            
            # Generate date chunks
            date_chunks = self._generate_date_chunks()
            logger.info(f"Generated {len(date_chunks)} date chunks to process")
            
            # Process each chunk
            async with self.async_session() as session:
                for i, (start_date, end_date) in enumerate(date_chunks, 1):
                    logger.info(f"\n📅 Processing chunk {i}/{len(date_chunks)}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                    
                    try:
                        chunk_orders = await self._fetch_orders_for_period(location_ids, start_date, end_date)
                        
                        if chunk_orders:
                            # Process orders in batches
                            await self._process_orders_batch(session, chunk_orders)
                            logger.info(f"✅ Processed {len(chunk_orders)} orders for period")
                        else:
                            logger.info(f"📭 No orders found for period")
                        
                        # Update progress tracking
                        await self._update_progress(session, start_date, end_date, len(chunk_orders))
                        self.total_chunks_processed += 1
                        
                        # Commit after each chunk
                        await session.commit()
                        
                        # Rate limiting delay
                        await asyncio.sleep(self.config.request_delay)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing chunk {i}: {str(e)}")
                        self.errors.append(f"Chunk {i} ({start_date} to {end_date}): {str(e)}")
                        await session.rollback()
                        # Continue with next chunk
                        continue
            
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                'success': True,
                'total_orders_synced': self.total_orders_synced,
                'total_chunks_processed': self.total_chunks_processed,
                'total_chunks': len(date_chunks),
                'duration_seconds': duration,
                'errors': self.errors
            }
            
            logger.info(f"\n🎉 Historical sync completed!")
            logger.info(f"Total orders synced: {self.total_orders_synced}")
            logger.info(f"Chunks processed: {self.total_chunks_processed}/{len(date_chunks)}")
            logger.info(f"Duration: {duration:.2f} seconds")
            if self.errors:
                logger.warning(f"Errors encountered: {len(self.errors)}")
                for error in self.errors:
                    logger.warning(f"  - {error}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Fatal error in historical sync: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_orders_synced': self.total_orders_synced,
                'total_chunks_processed': self.total_chunks_processed
            }

    def _generate_date_chunks(self) -> List[Tuple[datetime, datetime]]:
        """Generate date chunks for processing"""
        chunks = []
        current_date = self.config.start_date
        
        while current_date < self.config.end_date:
            chunk_end = min(
                current_date + timedelta(days=self.config.chunk_size_days),
                self.config.end_date
            )
            chunks.append((current_date, chunk_end))
            current_date = chunk_end
        
        return chunks

    async def _get_active_locations(self) -> List[Dict[str, Any]]:
        """Get active locations from Square API"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.square_base_url}/v2/locations"
                headers = {
                    'Authorization': f'Bearer {self.square_access_token}',
                    'Content-Type': 'application/json'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        locations = data.get('locations', [])
                        # Filter for active locations
                        active_locations = [loc for loc in locations if loc.get('status') == 'ACTIVE']
                        return active_locations
                    else:
                        error_text = await response.text()
                        raise Exception(f"Square API error getting locations: {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"Error fetching locations: {str(e)}")
            raise

    async def _fetch_orders_for_period(self, location_ids: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch all orders for a specific date period"""
        all_orders = []
        
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.square_base_url}/v2/orders/search"
                headers = {
                    'Authorization': f'Bearer {self.square_access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Build query
                base_query = {
                    "location_ids": location_ids,
                    "query": {
                        "filter": {
                            "date_time_filter": {
                                "created_at": {
                                    "start_at": start_date.isoformat(),
                                    "end_at": end_date.isoformat()
                                }
                            },
                            "state_filter": {
                                "states": ["COMPLETED", "OPEN", "CANCELED"]  # Include all states for historical data
                            }
                        }
                    },
                    "limit": 500  # Maximum allowed by Square API
                }
                
                cursor = None
                page = 1
                
                while True:
                    # Add cursor if we have one
                    body = base_query.copy()
                    if cursor:
                        body["cursor"] = cursor
                    
                    # Rate limiting
                    await asyncio.sleep(self.config.request_delay)
                    
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            orders = data.get('orders', [])
                            all_orders.extend(orders)
                            
                            logger.info(f"  📄 Page {page}: retrieved {len(orders)} orders (total: {len(all_orders)})")
                            
                            # Check for more pages
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                                
                            page += 1
                            
                        elif response.status == 429:
                            # Rate limited - wait longer
                            logger.warning("⏳ Rate limited, waiting 60 seconds...")
                            await asyncio.sleep(60)
                            continue
                            
                        else:
                            error_text = await response.text()
                            raise Exception(f"Square API error: {response.status} - {error_text}")
            
            return all_orders
            
        except Exception as e:
            logger.error(f"Error fetching orders for period {start_date} to {end_date}: {str(e)}")
            raise

    async def _process_orders_batch(self, session: AsyncSession, orders: List[Dict[str, Any]]):
        """Process and insert a batch of orders"""
        # Filter out erroneous orders first
        filtered_orders = [order for order in orders if not self._should_skip_order(order)]
        skipped_count = len(orders) - len(filtered_orders)
        
        if skipped_count > 0:
            logger.info(f"  🚫 Skipped {skipped_count} erroneous orders in this batch")
        
        # Process in smaller batches for efficiency
        for i in range(0, len(filtered_orders), self.config.batch_size):
            batch = filtered_orders[i:i + self.config.batch_size]
            
            # Insert orders
            await self._insert_orders(session, batch)
            
            # Insert line items for these orders
            await self._insert_order_line_items(session, batch)
            
            # Extract and insert payments if they exist
            await self._insert_order_payments(session, batch)
            
            self.total_orders_synced += len(batch)
            logger.info(f"  💾 Inserted batch of {len(batch)} orders (total: {self.total_orders_synced})")

    async def _insert_orders(self, session: AsyncSession, orders: List[Dict[str, Any]]):
        """Insert orders using upsert"""
        for order_data in orders:
            await session.execute(text("""
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
            """), {
                'id': order_data['id'],
                'location_id': order_data.get('location_id'),
                'created_at': self._parse_timestamp(order_data.get('created_at')),
                'updated_at': self._parse_timestamp(order_data.get('updated_at')),
                'closed_at': self._parse_timestamp(order_data.get('closed_at')),
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

    async def _insert_order_line_items(self, session: AsyncSession, orders: List[Dict[str, Any]]):
        """Insert order line items"""
        for order_data in orders:
            line_items = order_data.get('line_items', [])
            for line_item in line_items:
                await session.execute(text("""
                    INSERT INTO order_line_items (
                        uid, order_id, catalog_object_id, catalog_version, name, 
                        quantity, item_type, base_price_money, variation_total_price_money,
                        gross_sales_money, total_discount_money, total_tax_money, total_money,
                        variation_name, item_variation_metadata
                    ) VALUES (
                        :uid, :order_id, :catalog_object_id, :catalog_version, :name,
                        :quantity, :item_type, :base_price_money, :variation_total_price_money,
                        :gross_sales_money, :total_discount_money, :total_tax_money, :total_money,
                        :variation_name, :item_variation_metadata
                    )
                    ON CONFLICT (uid) DO UPDATE SET
                        catalog_object_id = EXCLUDED.catalog_object_id,
                        catalog_version = EXCLUDED.catalog_version,
                        name = EXCLUDED.name,
                        quantity = EXCLUDED.quantity,
                        item_type = EXCLUDED.item_type,
                        base_price_money = EXCLUDED.base_price_money,
                        variation_total_price_money = EXCLUDED.variation_total_price_money,
                        gross_sales_money = EXCLUDED.gross_sales_money,
                        total_discount_money = EXCLUDED.total_discount_money,
                        total_tax_money = EXCLUDED.total_tax_money,
                        total_money = EXCLUDED.total_money,
                        variation_name = EXCLUDED.variation_name,
                        item_variation_metadata = EXCLUDED.item_variation_metadata
                """), {
                    'uid': line_item['uid'],
                    'order_id': order_data['id'],
                    'catalog_object_id': line_item.get('catalog_object_id'),
                    'catalog_version': line_item.get('catalog_version'),
                    'name': line_item.get('name'),
                    'quantity': line_item.get('quantity'),
                    'item_type': line_item.get('item_type'),
                    'base_price_money': json.dumps(line_item.get('base_price_money', {})),
                    'variation_total_price_money': json.dumps(line_item.get('variation_total_price_money', {})),
                    'gross_sales_money': json.dumps(line_item.get('gross_sales_money', {})),
                    'total_discount_money': json.dumps(line_item.get('total_discount_money', {})),
                    'total_tax_money': json.dumps(line_item.get('total_tax_money', {})),
                    'total_money': json.dumps(line_item.get('total_money', {})),
                    'variation_name': line_item.get('variation_name'),
                    'item_variation_metadata': json.dumps(line_item.get('item_variation_metadata', {}))
                })

    async def _insert_order_payments(self, session: AsyncSession, orders: List[Dict[str, Any]]):
        """Insert payments associated with orders"""
        # Note: Orders API doesn't include payment details
        # This would need to be handled separately via Payments API
        # For now, we'll skip this to focus on the order data itself
        pass

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime object"""
        if not timestamp_str:
            return None
        try:
            # Handle RFC3339 format from Square API
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    def _should_skip_order(self, order: Dict[str, Any]) -> bool:
        """Check if an order should be skipped due to being erroneous"""
        order_id = order.get('id')
        
        # Exclude known erroneous orders - specifically the $2.16M "The Godfather" order
        if order_id == 'mknasZtDiUul9el73zNLANleV':
            logger.info(f"   🚫 Skipping erroneous order {order_id} ($2.16M 'The Godfather' order)")
            return True
        
        # Additional safety check: skip orders with unreasonably high amounts (over $100K)
        total_money = order.get('total_money', {})
        if total_money.get('amount'):
            try:
                amount_cents = int(total_money['amount'])
                amount_dollars = amount_cents / 100
                if amount_dollars > 100000:  # Over $100,000
                    logger.warning(f"   ⚠️ Skipping suspiciously large order {order_id}: ${amount_dollars:,.2f}")
                    return True
            except (ValueError, TypeError):
                pass  # If we can't parse the amount, continue with normal processing
        
        return False

    async def _update_progress(self, session: AsyncSession, start_date: datetime, end_date: datetime, orders_count: int):
        """Update sync progress in database"""
        await session.execute(text("""
            INSERT INTO sync_state (table_name, last_sync_timestamp, records_synced, updated_at)
            VALUES (:table_name, :timestamp, :records, NOW())
            ON CONFLICT (table_name) DO UPDATE SET
                last_sync_timestamp = :timestamp,
                records_synced = sync_state.records_synced + :records,
                updated_at = NOW()
        """), {
            "table_name": "historical_orders_sync",
            "timestamp": end_date,
            "records": orders_count
        })

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

async def main():
    """Main entry point"""
    try:
        sync = HistoricalOrdersSync()
        result = await sync.run_sync()
        
        if result['success']:
            print(f"\n✅ Historical orders sync completed successfully!")
            print(f"Total orders synced: {result['total_orders_synced']}")
            print(f"Duration: {result['duration_seconds']:.2f} seconds")
        else:
            print(f"\n❌ Historical orders sync failed: {result.get('error', 'Unknown error')}")
            return 1
        
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        return 1
    
    finally:
        if 'sync' in locals():
            await sync.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 