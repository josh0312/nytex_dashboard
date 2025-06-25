from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, JSON
from sqlalchemy.sql import func
from .base import Base

class DailyWeather(Base):
    """Daily weather records for locations"""
    __tablename__ = 'daily_weather'
    
    id = Column(Integer, primary_key=True)
    location_id = Column(String(255), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Temperature data
    temp_high = Column(Float)  # High temperature in Fahrenheit
    temp_low = Column(Float)   # Low temperature in Fahrenheit
    temp_avg = Column(Float)   # Average temperature
    
    # Weather condition
    weather_main = Column(String(50))      # Main weather category (Clear, Rain, etc.)
    weather_description = Column(String(255))  # Detailed description
    weather_icon = Column(String(10))      # Weather icon code
    
    # Additional weather data
    humidity = Column(Integer)             # Humidity percentage
    pressure = Column(Float)               # Atmospheric pressure
    wind_speed = Column(Float)             # Wind speed
    wind_direction = Column(Integer)       # Wind direction in degrees
    precipitation = Column(Float)          # Precipitation amount
    cloud_cover = Column(Integer)          # Cloud cover percentage
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Store raw API response for future reference
    raw_data = Column(JSON)
    
    def __repr__(self):
        return f"<DailyWeather(location_id='{self.location_id}', date='{self.date}', temp_high={self.temp_high}, weather='{self.weather_main}')>" 