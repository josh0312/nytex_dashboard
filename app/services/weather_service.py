from app.config import Config
import aiohttp
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database.models.weather import DailyWeather
from app.database.connection import get_db
from app.logger import logger

class WeatherService:
    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY
        if not self.api_key:
            raise ValueError("OpenWeather API key not found in environment variables")
        
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    def _extract_primary_zip(self, zip_code: str) -> str:
        """Extract primary 5-digit zip code from extended format (e.g., '12345-6789' -> '12345')"""
        if not zip_code:
            return zip_code
        
        # Handle extended zip codes like "12345-6789"
        if '-' in zip_code:
            return zip_code.split('-')[0]
        
        # Handle zip+4 format without dash like "123456789"
        if len(zip_code) == 9 and zip_code.isdigit():
            return zip_code[:5]
        
        # Return as-is if already 5 digits or other format
        return zip_code
    
    async def get_weather_by_zip(self, zip_code):
        """Get current weather for a zip code"""
        try:
            # Extract primary 5-digit zip code
            primary_zip = self._extract_primary_zip(zip_code)
            
            if zip_code != primary_zip:
                logger.info(f"Converted extended zip code '{zip_code}' to primary '{primary_zip}' for weather API")
            
            params = {
                'zip': f"{primary_zip},US",
                'appid': self.api_key,
                'units': 'imperial'  # For Fahrenheit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'temp': round(data['main']['temp']),
                            'temp_min': round(data['main']['temp_min']),
                            'temp_max': round(data['main']['temp_max']),
                            'main': data['weather'][0]['main'],  # Weather category (Clear, Rain, etc.)
                            'description': data['weather'][0]['description'].title(),
                            'humidity': data['main'].get('humidity', 0),
                            'icon': data['weather'][0]['icon']
                        }
                    else:
                        logger.error(f"Error fetching weather for {zip_code} (using {primary_zip}): {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching weather for {zip_code} (using {primary_zip}): {str(e)}", exc_info=True)
            return None

    async def store_daily_weather(self, location_id: str, weather_data: dict, weather_date: date = None):
        """Store daily weather data for a location"""
        if not weather_data:
            return None
            
        if weather_date is None:
            # Use Central Time instead of UTC for consistency with business operations
            from app.utils.timezone import get_central_now
            weather_date = get_central_now().date()
            
        try:
            async with get_db() as session:
                # Check if record already exists for this location and date
                existing = await session.execute(
                    select(DailyWeather).where(
                        and_(
                            DailyWeather.location_id == location_id,
                            DailyWeather.date == weather_date
                        )
                    )
                )
                existing_record = existing.scalar_one_or_none()
                
                if existing_record:
                    # Update existing record
                    existing_record.temp_high = weather_data.get('temp_max')
                    existing_record.temp_low = weather_data.get('temp_min')
                    existing_record.temp_avg = weather_data.get('temp')
                    existing_record.weather_main = weather_data.get('main')
                    existing_record.weather_description = weather_data.get('description')
                    existing_record.weather_icon = weather_data.get('icon')
                    existing_record.humidity = weather_data.get('humidity')
                    existing_record.updated_at = datetime.now()
                    logger.info(f"Updated weather record for location {location_id} on {weather_date}")
                else:
                    # Create new record
                    daily_weather = DailyWeather(
                        location_id=location_id,
                        date=weather_date,
                        temp_high=weather_data.get('temp_max'),
                        temp_low=weather_data.get('temp_min'),
                        temp_avg=weather_data.get('temp'),
                        weather_main=weather_data.get('main'),
                        weather_description=weather_data.get('description'),
                        weather_icon=weather_data.get('icon'),
                        humidity=weather_data.get('humidity'),
                        raw_data=weather_data
                    )
                    session.add(daily_weather)
                    logger.info(f"Created weather record for location {location_id} on {weather_date}")
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing weather data for {location_id} on {weather_date}: {str(e)}", exc_info=True)
            return False

    async def get_historical_weather(self, location_id: str, start_date: date, end_date: date):
        """Get historical weather data for a location between dates"""
        try:
            async with get_db() as session:
                result = await session.execute(
                    select(DailyWeather).where(
                        and_(
                            DailyWeather.location_id == location_id,
                            DailyWeather.date >= start_date,
                            DailyWeather.date <= end_date
                        )
                    ).order_by(DailyWeather.date)
                )
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Error getting historical weather for {location_id}: {str(e)}", exc_info=True)
            return [] 