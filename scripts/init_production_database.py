"""
Initialize production database with all tables
"""
import asyncio
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base, init_models

async def init_production_database():
    """Create all database tables in production"""
    try:
        print("Initializing database models...")
        init_models()
        
        # Production database connection
        DATABASE_URL = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
        
        print("Creating database engine for production...")
        engine = create_async_engine(
            DATABASE_URL,
            echo=True,  # Show SQL queries
            pool_size=5,
            max_overflow=10
        )
        
        print(f"Connecting to production database...")
        
        # Create all tables
        print("Creating all database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Production database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing production database: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(init_production_database())
    sys.exit(0 if success else 1) 