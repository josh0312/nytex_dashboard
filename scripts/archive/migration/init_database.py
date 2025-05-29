"""
Initialize database with all tables for fresh deployment
"""
import asyncio
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_engine, Base, init_models
from app.config import Config

async def init_database():
    """Create all database tables"""
    try:
        print("Initializing database models...")
        init_models()
        
        print("Creating database engine...")
        engine = get_engine()
        
        if not engine:
            print("ERROR: Could not create database engine. Check configuration.")
            return False
            
        print(f"Connecting to database: {Config.SQLALCHEMY_DATABASE_URI}")
        
        # Create all tables
        print("Creating all database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1) 