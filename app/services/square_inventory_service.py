import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from app.config import Config
from app.logger import logger
from app.database.models.catalog import CatalogInventory, CatalogVariation
from app.database.models.location import Location
import json


class SquareInventoryService:
    """Service for fetching and updating inventory data from Square API"""
    
    def __init__(self):
        # Configuration for Square API
        self.square_application_id = getattr(Config, 'SQUARE_APPLICATION_ID', '')
        self.square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
        self.square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'sandbox')
        
        # Set base URL based on environment
        if self.square_environment.lower() == 'production':
            self.base_url = "https://connect.squareup.com"
        else:
            self.base_url = "https://connect.squareupsandbox.com"
            
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        
    async def fetch_inventory_from_square(self, session: AsyncSession) -> Dict[str, Any]:
        """Fetch all inventory data from Square API and update the database"""
        try:
            logger.info("=== Starting Square inventory fetch ===")
            
            if not self.square_access_token:
                return {
                    'success': False,
                    'error': 'Square access token not configured',
                    'updated_time': datetime.now(timezone.utc).isoformat()
                }
            
            # Get all active locations
            locations_result = await session.execute(
                select(Location).where(Location.status == 'ACTIVE')
            )
            locations = locations_result.scalars().all()
            
            if not locations:
                return {
                    'success': False,
                    'error': 'No active locations found',
                    'updated_time': datetime.now(timezone.utc).isoformat()
                }
            
            logger.info(f"Found {len(locations)} active locations")
            
            # Get all catalog variations to map SKUs to variation IDs
            variations_result = await session.execute(
                select(CatalogVariation).where(CatalogVariation.is_deleted == False)
            )
            variations = variations_result.scalars().all()
            
            # Create mapping of catalog object IDs to variation IDs
            catalog_to_variation = {}
            for variation in variations:
                catalog_to_variation[variation.id] = variation.id
            
            logger.info(f"Found {len(variations)} catalog variations")
            
            # Fetch inventory for each location
            total_updated = 0
            location_inventory = {}
            
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                headers = {
                    'Authorization': f'Bearer {self.square_access_token}',
                    'Content-Type': 'application/json',
                    'Square-Version': '2025-05-21'  # Use current API version
                }
                
                for location in locations:
                    logger.info(f"Fetching inventory for location: {location.name}")
                    
                    # Get inventory counts for this location
                    inventory_url = f"{self.base_url}/v2/inventory/counts/batch-retrieve"
                    
                    # Prepare request body - we'll get all inventory for this location
                    request_body = {
                        "location_ids": [location.id],
                        "cursor": None
                    }
                    
                    location_inventory_items = []
                    cursor = None
                    
                    while True:
                        if cursor:
                            request_body["cursor"] = cursor
                        
                        async with client_session.post(
                            inventory_url, 
                            headers=headers, 
                            json=request_body
                        ) as response:
                            
                            if response.status == 200:
                                data = await response.json()
                                counts = data.get('counts', [])
                                
                                logger.info(f"Retrieved {len(counts)} inventory items for {location.name}")
                                location_inventory_items.extend(counts)
                                
                                # Check for more pages
                                cursor = data.get('cursor')
                                if not cursor:
                                    break
                                    
                            else:
                                error_text = await response.text()
                                logger.error(f"Square API error for {location.name}: {response.status} - {error_text}")
                                break
                    
                    location_inventory[location.id] = location_inventory_items
                    logger.info(f"Total inventory items for {location.name}: {len(location_inventory_items)}")
            
            # Update database with fetched inventory data
            logger.info("Updating database with inventory data...")
            
            # Clear existing inventory data
            await session.execute(delete(CatalogInventory))
            await session.flush()
            
            # Insert new inventory data
            for location_id, inventory_items in location_inventory.items():
                for item in inventory_items:
                    catalog_object_id = item.get('catalog_object_id')
                    quantity = item.get('quantity', '0')
                    calculated_at = item.get('calculated_at')
                    
                    # Convert quantity to integer
                    try:
                        quantity_int = int(quantity)
                    except (ValueError, TypeError):
                        quantity_int = 0
                    
                    # Parse calculated_at timestamp
                    calculated_datetime = None
                    if calculated_at:
                        try:
                            calculated_datetime = datetime.fromisoformat(calculated_at.replace('Z', '+00:00'))
                        except ValueError:
                            calculated_datetime = datetime.now(timezone.utc)
                    else:
                        calculated_datetime = datetime.now(timezone.utc)
                    
                    # Only create inventory record if we have a matching variation
                    if catalog_object_id in catalog_to_variation:
                        inventory_record = CatalogInventory(
                            variation_id=catalog_object_id,
                            location_id=location_id,
                            quantity=quantity_int,
                            calculated_at=calculated_datetime
                        )
                        session.add(inventory_record)
                        total_updated += 1
            
            await session.commit()
            
            logger.info(f"Successfully updated {total_updated} inventory records")
            logger.info("=== Completed Square inventory fetch ===")
            
            return {
                'success': True,
                'records_updated': total_updated,
                'locations_processed': len(locations),
                'updated_time': datetime.now(timezone.utc).isoformat(),
                'message': f'Successfully updated {total_updated} inventory records across {len(locations)} locations'
            }
            
        except Exception as e:
            logger.error(f"Error fetching inventory from Square: {str(e)}", exc_info=True)
            logger.error("=== Failed Square inventory fetch ===")
            return {
                'success': False,
                'error': str(e),
                'updated_time': datetime.now(timezone.utc).isoformat()
            }
    
    async def get_inventory_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Get current inventory status and statistics"""
        try:
            # Get total inventory records
            count_result = await session.execute(
                text("SELECT COUNT(*) FROM catalog_inventory")
            )
            total_records = count_result.scalar()
            
            # Get latest update time
            latest_result = await session.execute(
                text("SELECT MAX(updated_at) FROM catalog_inventory")
            )
            latest_update = latest_result.scalar()
            
            # Get inventory by location
            location_result = await session.execute(
                text("""
                    SELECT l.name, COUNT(ci.id) as item_count, SUM(ci.quantity) as total_qty
                    FROM catalog_inventory ci
                    JOIN locations l ON ci.location_id = l.id
                    WHERE l.status = 'ACTIVE'
                    GROUP BY l.name
                    ORDER BY l.name
                """)
            )
            location_stats = [
                {
                    'location': row[0],
                    'item_count': row[1],
                    'total_quantity': row[2]
                }
                for row in location_result.fetchall()
            ]
            
            # Format last update time
            last_update_iso = None
            if latest_update:
                if latest_update.tzinfo is None:
                    # Assume UTC if no timezone info
                    utc_update = latest_update.replace(tzinfo=timezone.utc)
                else:
                    utc_update = latest_update
                last_update_iso = utc_update.isoformat()
            
            return {
                'total_records': total_records,
                'last_update': last_update_iso,
                'has_data': total_records > 0,
                'location_stats': location_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory status: {str(e)}")
            return {
                'total_records': 0,
                'last_update': None,
                'has_data': False,
                'location_stats': [],
                'error': str(e)
            } 