import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete, update
from app.config import Config
from app.logger import logger
from app.database.models.catalog import CatalogInventory, CatalogVariation, CatalogItem
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
        
        # Units Per Case attribute ID from our previous analysis
        self.units_per_case_id = "WLEIG6KKOKGRMX2PG2TCZFP7"

    def extract_units_per_case(self, obj: Dict[str, Any]) -> int:
        """Extract Units Per Case value from a catalog object's custom attributes"""
        try:
            if 'custom_attribute_values' in obj:
                custom_attrs = obj['custom_attribute_values']
                
                # Look for Units Per Case specifically
                for attr_key, attr_data in custom_attrs.items():
                    if (attr_data.get('custom_attribute_definition_id') == self.units_per_case_id or
                        attr_data.get('name') == 'Units Per Case'):
                        units_value = attr_data.get('number_value')
                        if units_value is not None:
                            try:
                                # Convert to float first, then to int (handles decimal values from Square)
                                return int(float(units_value))
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid Units Per Case value: {units_value} for object {obj.get('id')}")
                                return None
                        break
            
            return None
        except Exception as e:
            logger.error(f"Error extracting Units Per Case from object {obj.get('id')}: {str(e)}")
            return None

    async def fetch_catalog_updates_from_square(self, session: AsyncSession) -> Dict[str, Any]:
        """Fetch catalog items and variations to update Units Per Case data"""
        try:
            logger.info("=== Fetching catalog updates for Units Per Case ===")
            
            catalog_updates = {
                'items_updated': 0,
                'variations_updated': 0,
                'items_with_units': 0,
                'variations_with_units': 0
            }
            
            # Fetch catalog items first
            url = f"{self.base_url}/v2/catalog/search"
            headers = {
                'Authorization': f'Bearer {self.square_access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get existing catalog items from database for comparison
            db_items_result = await session.execute(
                select(CatalogItem).where(CatalogItem.is_deleted == False)
            )
            db_items = {item.id: item for item in db_items_result.scalars().all()}
            
            # Fetch items from Square
            all_items = []
            cursor = None
            page = 1
            
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                while True:
                    body = {
                        "object_types": ["ITEM"],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    logger.info(f"Fetching catalog items page {page} for Units Per Case sync...")
                    
                    async with client_session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('objects', [])
                            all_items.extend(items)
                            
                            logger.info(f"Retrieved {len(items)} items on page {page} (total: {len(all_items)})")
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                            page += 1
                        else:
                            error_text = await response.text()
                            logger.error(f"Square API error fetching items: {response.status} - {error_text}")
                            break
                
                # Process items and update Units Per Case
                for square_item in all_items:
                    item_id = square_item.get('id')
                    
                    if not item_id or item_id not in db_items:
                        continue
                    
                    units_per_case = self.extract_units_per_case(square_item)
                    
                    if units_per_case is not None:
                        catalog_updates['items_with_units'] += 1
                    
                    # Update if different
                    db_item = db_items[item_id]
                    if db_item.units_per_case != units_per_case:
                        await session.execute(
                            update(CatalogItem)
                            .where(CatalogItem.id == item_id)
                            .values(
                                units_per_case=units_per_case,
                                updated_at=datetime.utcnow()
                            )
                        )
                        catalog_updates['items_updated'] += 1
                
                # Now fetch catalog variations
                db_variations_result = await session.execute(
                    select(CatalogVariation).where(CatalogVariation.is_deleted == False)
                )
                db_variations = {var.id: var for var in db_variations_result.scalars().all()}
                
                all_variations = []
                cursor = None
                page = 1
                
                while True:
                    body = {
                        "object_types": ["ITEM_VARIATION"],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    logger.info(f"Fetching catalog variations page {page} for Units Per Case sync...")
                    
                    async with client_session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            variations = data.get('objects', [])
                            all_variations.extend(variations)
                            
                            logger.info(f"Retrieved {len(variations)} variations on page {page} (total: {len(all_variations)})")
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                            page += 1
                        else:
                            error_text = await response.text()
                            logger.error(f"Square API error fetching variations: {response.status} - {error_text}")
                            break
                
                # Process variations and update Units Per Case
                for square_variation in all_variations:
                    variation_id = square_variation.get('id')
                    
                    if not variation_id or variation_id not in db_variations:
                        continue
                    
                    units_per_case = self.extract_units_per_case(square_variation)
                    
                    if units_per_case is not None:
                        catalog_updates['variations_with_units'] += 1
                    
                    # Update if different
                    db_variation = db_variations[variation_id]
                    if db_variation.units_per_case != units_per_case:
                        await session.execute(
                            update(CatalogVariation)
                            .where(CatalogVariation.id == variation_id)
                            .values(
                                units_per_case=units_per_case,
                                updated_at=datetime.utcnow()
                            )
                        )
                        catalog_updates['variations_updated'] += 1
            
            logger.info(f"Catalog updates completed - Items: {catalog_updates['items_updated']} updated ({catalog_updates['items_with_units']} with units), Variations: {catalog_updates['variations_updated']} updated ({catalog_updates['variations_with_units']} with units)")
            
            return catalog_updates
            
        except Exception as e:
            logger.error(f"Error fetching catalog updates: {str(e)}", exc_info=True)
            return {
                'items_updated': 0,
                'variations_updated': 0,
                'items_with_units': 0,
                'variations_with_units': 0,
                'error': str(e)
            }
        
    async def fetch_inventory_from_square(self, session: AsyncSession) -> Dict[str, Any]:
        """Fetch all inventory data from Square API and update the database, including Units Per Case sync"""
        try:
            logger.info("=== Starting Square inventory and catalog sync ===")
            
            if not self.square_access_token:
                return {
                    'success': False,
                    'error': 'Square access token not configured',
                    'updated_time': datetime.now(timezone.utc).isoformat()
                }
            
            # First, sync catalog data (Units Per Case)
            catalog_updates = await self.fetch_catalog_updates_from_square(session)
            
            # Get all active locations
            locations_result = await session.execute(
                select(Location).where(Location.status == 'ACTIVE')
            )
            locations = locations_result.scalars().all()
            
            if not locations:
                return {
                    'success': False,
                    'error': 'No active locations found',
                    'updated_time': datetime.now(timezone.utc).isoformat(),
                    'catalog_updates': catalog_updates
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
                for location in locations:
                    logger.info(f"Fetching inventory for location: {location.name}")
                    
                    location_inventory_items = []
                    cursor = None
                    
                    inventory_url = f"{self.base_url}/v2/inventory/counts/batch-retrieve"
                    headers = {
                        'Authorization': f'Bearer {self.square_access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    request_body = {
                        'location_ids': [location.id],
                        'updated_after': '2020-01-01T00:00:00Z'  # Get all inventory since 2020
                    }
                    
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
            
            # Deduplicate inventory data before insertion
            # Use a dictionary to keep only the latest entry for each (variation_id, location_id) pair
            unique_inventory = {}
            total_raw_items = 0
            
            for location_id, inventory_items in location_inventory.items():
                for item in inventory_items:
                    total_raw_items += 1
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
                            # Convert to timezone-naive UTC for database storage
                            if calculated_datetime.tzinfo is not None:
                                calculated_datetime = calculated_datetime.astimezone(timezone.utc).replace(tzinfo=None)
                        except ValueError:
                            calculated_datetime = datetime.now(timezone.utc).replace(tzinfo=None)
                    else:
                        calculated_datetime = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    # Only process if we have a matching variation and valid catalog object ID
                    if catalog_object_id and catalog_object_id in catalog_to_variation:
                        # Create unique key for deduplication
                        unique_key = (catalog_object_id, location_id)
                        
                        # If this combination doesn't exist or has a newer timestamp, update it
                        if (unique_key not in unique_inventory or 
                            (calculated_datetime and 
                             unique_inventory[unique_key]['calculated_datetime'] < calculated_datetime)):
                            
                            unique_inventory[unique_key] = {
                                'variation_id': catalog_object_id,
                                'location_id': location_id,
                                'quantity': quantity_int,
                                'calculated_datetime': calculated_datetime
                            }
            
            logger.info(f"Processed {total_raw_items} raw inventory items, deduplicated to {len(unique_inventory)} unique records")
            
            # Insert deduplicated inventory data
            for inventory_data in unique_inventory.values():
                inventory_record = CatalogInventory(
                    variation_id=inventory_data['variation_id'],
                    location_id=inventory_data['location_id'],
                    quantity=inventory_data['quantity'],
                    calculated_at=inventory_data['calculated_datetime']
                )
                session.add(inventory_record)
                total_updated += 1
            
            await session.commit()
            
            logger.info(f"Successfully updated {total_updated} inventory records")
            logger.info("=== Completed Square inventory and catalog sync ===")
            
            return {
                'success': True,
                'total_inventory_updated': total_updated,
                'locations_processed': len(locations),
                'catalog_updates': catalog_updates,
                'updated_time': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during inventory sync: {str(e)}", exc_info=True)
            await session.rollback()
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
                    # Database stores timezone-naive UTC, so add UTC timezone for display
                    utc_update = latest_update.replace(tzinfo=timezone.utc)
                else:
                    utc_update = latest_update.astimezone(timezone.utc)
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