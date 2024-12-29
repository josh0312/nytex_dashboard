import os
from dotenv import load_dotenv
from app.logger import logger

load_dotenv()

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = "postgresql+asyncpg://postgres:postgres@localhost:5432/square_data_sync"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Square API configuration
    SQUARE_ACCESS_TOKEN = os.getenv('SQUARE_ACCESS_TOKEN')
    SQUARE_ENVIRONMENT = os.getenv('SQUARE_ENVIRONMENT', 'production')
    
    # OpenWeather API configuration
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    
    # Application configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' 