#!/usr/bin/env python3
"""
Script to capture daily weather for all locations
This can be run daily to build up historical weather data
"""

import asyncio
import sys
import os
from datetime import date, datetime

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.weather_service import WeatherService
from app.services.location_service import LocationService
from app.logger import logger

async def capture_daily_weather():
    """Capture current weather for all active locations"""
    try:
        weather_service = WeatherService()
        location_service = LocationService()
        
        # Get all active locations
        locations = await location_service.get_all_locations()
        
        # Use Central Time for consistent business date
        from app.utils.timezone import get_central_now
        today = get_central_now().date()
        logger.info(f"Capturing weather for {len(locations)} locations on {today} (Central Time)")
        
        for location in locations:
            try:
                location_id = location['id']
                location_name = location['name']
                
                # Extract zip code from address
                address = location.get('address', {})
                if isinstance(address, dict):
                    zip_code = address.get('postal_code')
                else:
                    logger.warning(f"No postal code found for {location_name}")
                    continue
                
                if not zip_code:
                    logger.warning(f"No postal code found for {location_name}")
                    continue
                
                logger.info(f"Getting weather for {location_name} (ZIP: {zip_code})")
                
                # Get current weather
                weather_data = await weather_service.get_weather_by_zip(zip_code)
                if weather_data:
                    # Store weather data
                    success = await weather_service.store_daily_weather(location_id, weather_data, today)
                    if success:
                        logger.info(f"Successfully stored weather for {location_name}: {weather_data['temp']}°F, {weather_data['description']}")
                    else:
                        logger.error(f"Failed to store weather for {location_name}")
                else:
                    logger.warning(f"Could not get weather data for {location_name}")
                    
            except Exception as e:
                logger.error(f"Error capturing weather for {location.get('name', 'Unknown')}: {str(e)}")
        
        logger.info("Daily weather capture completed")
        
    except Exception as e:
        logger.error(f"Error in daily weather capture: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("Daily Weather Capture Script")
    print("=" * 50)
    asyncio.run(capture_daily_weather()) 