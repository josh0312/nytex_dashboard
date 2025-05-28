import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Get base directory
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Database settings
    DB_USER = os.getenv("POSTGRES_USER")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    DB_HOST = os.getenv("POSTGRES_HOST")
    DB_PORT = os.getenv("POSTGRES_PORT")
    DB_NAME = os.getenv("POSTGRES_DB")
    
    # Construct database URL
    SQLALCHEMY_DATABASE_URI = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    @classmethod
    def get_sync_db_url(cls):
        """Get synchronous database URL for migrations"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    # Square API configuration
    SQUARE_ACCESS_TOKEN = os.getenv('SQUARE_ACCESS_TOKEN')
    SQUARE_ENVIRONMENT = os.getenv('SQUARE_ENVIRONMENT', 'production')
    
    # OpenWeather API configuration
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    
    # Square Catalog Export Service
    SQUARE_CATALOG_EXPORT_URL = os.getenv("SQUARE_CATALOG_EXPORT_URL", "http://localhost:5001")
    
    # App settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set") 