import os
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (parent of the app directory)
BASE_DIR = Path(__file__).resolve().parent.parent
# Load environment variables from .env.local in the project root
load_dotenv(BASE_DIR / '.env.local')

def get_database_url():
    """Get database URL based on available environment variables"""
    # Check if we have a full DATABASE_URL or SQLALCHEMY_DATABASE_URI first
    db_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
    if db_url:
        if not db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
        return db_url
    
    # Check for Cloud Run environment variables
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASS')
    db_name = os.environ.get('DB_NAME')
    cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    if all([db_user, db_pass, db_name, cloud_sql_connection_name]):
        # Cloud SQL connection format
        return f"postgresql+asyncpg://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
    
    # Check for traditional environment variables
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB")
    
    if all([db_user, db_password, db_host, db_port, db_name]):
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fallback for local development
    return "postgresql+asyncpg://postgres:password@localhost:5432/square_data_sync"

class Config:
    # Get base directory
    BASE_DIR = BASE_DIR
    
    # Database settings - use class method to evaluate at runtime
    @classmethod
    def get_database_url(cls):
        return get_database_url()
    
    @classmethod
    def get_sync_db_url(cls):
        """Get synchronous database URL for migrations"""
        # Check if we have a full DATABASE_URL or SQLALCHEMY_DATABASE_URI first
        db_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
        if db_url:
            # Convert asyncpg to psycopg2 for sync operations
            if 'postgresql+asyncpg://' in db_url:
                return db_url.replace('postgresql+asyncpg://', 'postgresql://')
            return db_url
        
        # For Cloud Run
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_name = os.environ.get('DB_NAME')
        cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
        
        if all([db_user, db_pass, db_name, cloud_sql_connection_name]):
            return f"postgresql://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
        
        # For traditional setup
        db_user = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD", "")
        db_host = os.getenv("POSTGRES_HOST")
        db_port = os.getenv("POSTGRES_PORT")
        db_name = os.getenv("POSTGRES_DB")
        
        if all([db_user, db_host, db_port, db_name]):
            # Handle password-less connections (like for joshgoble user)
            if db_password:
                return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            else:
                return f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"
        
        return "postgresql://postgres:password@localhost:5432/square_data_sync"
    
    # Square API configuration
    SQUARE_ACCESS_TOKEN = os.getenv('SQUARE_ACCESS_TOKEN')
    SQUARE_ENVIRONMENT = os.getenv('SQUARE_ENVIRONMENT', 'production')
    
    # OpenWeather API configuration
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    
    # Square Catalog Export Service
    SQUARE_CATALOG_EXPORT_URL = os.getenv("SQUARE_CATALOG_EXPORT_URL", "http://localhost:5001")
    
    # App settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-key-change-this-in-production"
    
    # Authentication settings
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", "https://your-domain.com/auth/callback")
    
    # Manual user settings
    MANUAL_USER_EMAIL = os.getenv("MANUAL_USER_EMAIL")
    MANUAL_USER_PASSWORD = os.getenv("MANUAL_USER_PASSWORD")
    MANUAL_USER_NAME = os.getenv("MANUAL_USER_NAME", "Guest User") 