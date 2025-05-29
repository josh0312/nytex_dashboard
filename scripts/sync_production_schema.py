"""
Sync missing tables from local to production database
"""
import asyncio
import os
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config
from app.database.models import Base

async def sync_production_schema():
    """Add missing tables to production database"""
    try:
        # Production database connection
        prod_url = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
        
        print("🔄 Syncing production database schema...")
        print("=" * 50)
        
        # Create async engine for production
        prod_engine = create_async_engine(prod_url, echo=False, connect_args={"ssl": "require"})
        
        # Create all tables from models
        async with prod_engine.begin() as conn:
            print("📋 Creating missing tables...")
            
            # Create all tables defined in models
            await conn.run_sync(Base.metadata.create_all)
            
            print("✅ Tables created successfully!")
            
            # Check if alembic_version exists and create it if not
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """))
            
            alembic_exists = result.scalar()
            
            if not alembic_exists:
                print("📝 Creating alembic_version table...")
                await conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """))
                
                # Insert current version (get from local)
                local_url = Config.SQLALCHEMY_DATABASE_URI.replace('postgresql+asyncpg://', 'postgresql://')
                local_engine = create_engine(local_url)
                
                with local_engine.connect() as local_conn:
                    local_version = local_conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                    if local_version:
                        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:version)"), 
                                         {"version": local_version})
                        print(f"   Set alembic version to: {local_version}")
                
                local_engine.dispose()
            
            # Get final table list
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print(f"\n📊 Production now has {len(tables)} tables:")
            for table in tables:
                print(f"  • {table}")
        
        await prod_engine.dispose()
        
        print(f"\n🎉 Schema sync completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error syncing schema: {str(e)}")
        return False

async def main():
    """Main function"""
    print("🔄 Production Database Schema Sync")
    print("=" * 60)
    
    success = await sync_production_schema()
    
    if success:
        print("\n✅ Production database schema is now in sync!")
        print("   You can now run data syncs to populate the tables.")
    else:
        print("\n❌ Schema sync failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main()) 