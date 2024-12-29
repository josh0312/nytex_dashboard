from app.config import Config
import aiohttp
from app.logger import logger

class WeatherService:
    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY
        if not self.api_key:
            raise ValueError("OpenWeather API key not found in environment variables")
        
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    async def get_weather_by_zip(self, zip_code):
        """Get current weather for a zip code"""
        try:
            logger.info(f"Fetching weather for zip code: {zip_code}")
            params = {
                'zip': f"{zip_code},US",
                'appid': self.api_key,
                'units': 'imperial'  # For Fahrenheit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Weather data received: {data}")
                        weather_data = {
                            'temp': round(data['main']['temp']),
                            'temp_min': round(data['main']['temp_min']),
                            'temp_max': round(data['main']['temp_max']),
                            'description': data['weather'][0]['description'].title(),
                            'humidity': data['main'].get('humidity', 0),
                            'icon': data['weather'][0]['icon']
                        }
                        logger.info(f"Processed weather data: {weather_data}")
                        return weather_data
                    else:
                        error_data = await response.text()
                        logger.error(f"Error fetching weather for {zip_code}: {response.status} - {error_data}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching weather for {zip_code}: {str(e)}", exc_info=True)
            return None 