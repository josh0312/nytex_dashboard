import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-this'
    
    # Database configuration for Cloud Run
    def get_database_url():
        # Check if we have SQLALCHEMY_DATABASE_URI from secret first
        db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
        if db_uri:
            return db_uri
            
        # Check if we have a full DATABASE_URL 
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            if not db_url.startswith('postgresql+asyncpg://'):
                db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
            return db_url
        
        # Otherwise, construct from Cloud Run environment variables
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_name = os.environ.get('DB_NAME')
        cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
        
        if all([db_user, db_pass, db_name, cloud_sql_connection_name]):
            # Cloud SQL connection format
            return f"postgresql+asyncpg://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
        
        # Fallback for local development
        return "postgresql+asyncpg://postgres:password@localhost:5432/square_data_sync"
    
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    
    # External Services
    SQUARE_CATALOG_EXPORT_URL = os.environ.get('SQUARE_CATALOG_EXPORT_URL', 'http://localhost:5000')
    
    # Square API Configuration
    # In production (Cloud Run), this will be injected from Secret Manager
    # In local development, this comes from .env file
    SQUARE_ACCESS_TOKEN = os.environ.get('SQUARE_ACCESS_TOKEN')
    SQUARE_APPLICATION_ID = os.environ.get('SQUARE_APPLICATION_ID')
    SQUARE_ENVIRONMENT = os.environ.get('SQUARE_ENVIRONMENT', 'production')
