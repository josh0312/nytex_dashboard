import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.config import Config
from app.logger import logger
from app.database.models.location import Location
import json


class SquareLocationService:
    """Service for fetching and updating location data from Square API"""
    
    def __init__(self):
        # Configuration for Square API
        self.square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
        self.square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'sandbox')
        
        # Set base URL based on environment
        if self.square_environment.lower() == 'production':
            self.base_url = "https://connect.squareup.com"
        else:
            self.base_url = "https://connect.squareupsandbox.com"
            
        self.timeout = aiohttp.ClientTimeout(total=60)  # 1 minute timeout

    async def fetch_locations_from_square(self, session: AsyncSession) -> Dict[str, Any]:
        """Fetch all locations from Square API and update the database"""
        try:
            logger.info("=== Starting Square locations sync ===")
            
            if not self.square_access_token:
                return {
                    'success': False,
                    'error': 'Square access token not configured',
                    'updated_time': datetime.now(timezone.utc).isoformat()
                }
            
            # Fetch locations from Square API
            locations_url = f"{self.base_url}/v2/locations"
            headers = {
                'Authorization': f'Bearer {self.square_access_token}',
                'Content-Type': 'application/json'
            }
            
            square_locations = []
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                logger.info("Fetching locations from Square API...")
                
                async with client_session.get(locations_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        square_locations = data.get('locations', [])
                        logger.info(f"Retrieved {len(square_locations)} locations from Square")
                    else:
                        error_text = await response.text()
                        logger.error(f"Square API error fetching locations: {response.status} - {error_text}")
                        return {
                            'success': False,
                            'error': f'Square API error: {response.status} - {error_text}',
                            'updated_time': datetime.now(timezone.utc).isoformat()
                        }
            
            if not square_locations:
                return {
                    'success': False,
                    'error': 'No locations returned from Square API',
                    'updated_time': datetime.now(timezone.utc).isoformat()
                }
            
            # Start a transaction to update locations
            async with session.begin():
                # Get existing locations from database
                existing_locations_result = await session.execute(select(Location))
                existing_locations = {loc.id: loc for loc in existing_locations_result.scalars().all()}
                
                locations_created = 0
                locations_updated = 0
                
                # Process each Square location
                for square_location in square_locations:
                    location_id = square_location.get('id')
                    
                    if not location_id:
                        logger.warning("Skipping location with no ID")
                        continue
                    
                    # Extract location data
                    name = square_location.get('name', '')
                    status = square_location.get('status', 'UNKNOWN')
                    
                    # Extract address information
                    address_data = square_location.get('address', {})
                    address_line_1 = address_data.get('address_line_1', '')
                    address_line_2 = address_data.get('address_line_2', '')
                    locality = address_data.get('locality', '')
                    administrative_district_level_1 = address_data.get('administrative_district_level_1', '')
                    postal_code = address_data.get('postal_code', '')
                    country = address_data.get('country', '')
                    
                    # Store address as JSONB to match model
                    address_json = address_data if address_data else {}
                    
                    # Extract other fields
                    timezone_name = square_location.get('timezone', '')
                    capabilities = square_location.get('capabilities', [])
                    description = square_location.get('description', '')
                    
                    # Extract coordinates as JSONB
                    coordinates_data = address_data.get('coordinates', {})
                    coordinates_json = coordinates_data if coordinates_data else None
                    
                    # Extract business hours (simplified)
                    business_hours = json.dumps(square_location.get('business_hours', {})) if square_location.get('business_hours') else None
                    
                    # Extract contact info
                    business_email = square_location.get('business_email', '')
                    phone_number = square_location.get('phone_number', '')
                    website_url = square_location.get('website_url', '')
                    
                    # Current timestamp
                    now = datetime.utcnow()
                    
                    if location_id in existing_locations:
                        # Update existing location
                        existing_location = existing_locations[location_id]
                        
                        # Check if any fields have changed
                        if (existing_location.name != name or
                            existing_location.status != status or
                            existing_location.address != address_json or
                            existing_location.timezone != timezone_name):
                            
                            await session.execute(
                                update(Location)
                                .where(Location.id == location_id)
                                .values(
                                    name=name,
                                    address=address_json,
                                    timezone=timezone_name,
                                    capabilities=capabilities,
                                    status=status,
                                    updated_at=now,
                                    description=description,
                                    coordinates=coordinates_json,
                                    business_hours=business_hours,
                                    business_email=business_email,
                                    phone_number=phone_number,
                                    website_url=website_url
                                )
                            )
                            locations_updated += 1
                            logger.info(f"Updated location: {name}")
                    else:
                        # Create new location
                        new_location = Location(
                            id=location_id,
                            name=name,
                            address=address_json,
                            timezone=timezone_name,
                            capabilities=capabilities,
                            status=status,
                            created_at=now,
                            updated_at=now,
                            description=description,
                            coordinates=coordinates_json,
                            business_hours=business_hours,
                            business_email=business_email,
                            phone_number=phone_number,
                            website_url=website_url
                        )
                        session.add(new_location)
                        locations_created += 1
                        logger.info(f"Created new location: {name}")
                
                # Transaction will be committed automatically by session.begin() context manager
            
            logger.info(f"Locations sync completed - Created: {locations_created}, Updated: {locations_updated}")
            logger.info("=== Completed Square locations sync ===")
            
            return {
                'success': True,
                'locations_created': locations_created,
                'locations_updated': locations_updated,
                'total_locations': len(square_locations),
                'updated_time': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during locations sync: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'updated_time': datetime.now(timezone.utc).isoformat()
            }

    async def get_locations_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Get current locations status and statistics"""
        try:
            # Get total location records
            count_result = await session.execute(
                select(Location).where(Location.status == 'ACTIVE')
            )
            active_locations = count_result.scalars().all()
            
            # Get all locations
            all_result = await session.execute(select(Location))
            all_locations = all_result.scalars().all()
            
            locations_data = []
            for location in all_locations:
                # Extract readable address from JSONB
                address_display = "No address"
                if location.address and isinstance(location.address, dict):
                    address_parts = []
                    for key in ['address_line_1', 'address_line_2', 'locality', 'administrative_district_level_1', 'postal_code', 'country']:
                        if key in location.address and location.address[key]:
                            address_parts.append(location.address[key])
                    address_display = ', '.join(address_parts) if address_parts else "No address"
                
                locations_data.append({
                    'id': location.id,
                    'name': location.name,
                    'status': location.status,
                    'address': address_display
                })
            
            return {
                'total_locations': len(all_locations),
                'active_locations': len(active_locations),
                'has_locations': len(all_locations) > 0,
                'locations': locations_data
            }
            
        except Exception as e:
            logger.error(f"Error getting locations status: {str(e)}")
            return {
                'total_locations': 0,
                'active_locations': 0,
                'has_locations': False,
                'locations': [],
                'error': str(e)
            } 