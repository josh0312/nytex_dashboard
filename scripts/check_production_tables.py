"""
Check what tables exist in the production database
"""
import asyncio
import os
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config

async def check_production_tables():
    """Check what tables exist in production database"""
    try:
        # Production database connection with SSL
        DATABASE_URL = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
        
        print("🔍 Checking production database tables...")
        engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": "require"})
        
        async with engine.begin() as conn:
            # Get all table names
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print(f"\n📊 Production Database Tables ({len(tables)} total):")
            print("=" * 50)
            if tables:
                for table in tables:
                    print(f"  • {table}")
            else:
                print("  No tables found!")
            
            # Check row counts for key tables
            if tables:
                print(f"\n📈 Table Row Counts:")
                print("=" * 30)
                
                for table in tables:
                    try:
                        count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = count_result.scalar()
                        print(f"  {table:<30} {count:>10} rows")
                    except Exception as e:
                        print(f"  {table:<30} {'ERROR':>10}")
        
        await engine.dispose()
        return tables
        
    except Exception as e:
        print(f"❌ Error checking production tables: {str(e)}")
        print(f"   Database URL: postgresql+asyncpg://nytex_user:***@34.67.201.62:5432/nytex_dashboard")
        return []

def check_local_tables():
    """Check what tables exist in local database using app config"""
    try:
        # Use the same database URL logic as the main app
        local_db_url = Config.SQLALCHEMY_DATABASE_URI
        # Convert to sync URL for this script
        sync_url = local_db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        print(f"\n🏠 Checking local database tables...")
        print(f"📍 Using database: {sync_url}")
        
        engine = create_engine(sync_url, echo=False)
        
        with engine.begin() as conn:
            # Get all table names
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print(f"\n📊 Local Database Tables ({len(tables)} total):")
            print("=" * 50)
            for table in tables:
                print(f"  • {table}")
            
            # Check row counts for key tables
            print(f"\n📈 Table Row Counts:")
            print("=" * 30)
            
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    print(f"  {table:<30} {count:>10} rows")
                except Exception as e:
                    print(f"  {table:<30} {'ERROR':>10}")
        
        engine.dispose()
        return tables
        
    except Exception as e:
        print(f"❌ Error checking local tables: {str(e)}")
        print(f"Database URL: {Config.SQLALCHEMY_DATABASE_URI}")
        return []

async def main():
    """Main function to compare databases"""
    print("🔍 Database Table Comparison")
    print("=" * 60)
    
    # Check both databases
    prod_tables = await check_production_tables()
    local_tables = check_local_tables()
    
    # Compare tables
    print(f"\n🔄 Table Comparison:")
    print("=" * 40)
    
    prod_set = set(prod_tables)
    local_set = set(local_tables)
    
    # Tables in both
    common_tables = prod_set & local_set
    print(f"\n✅ Tables in both databases ({len(common_tables)}):")
    for table in sorted(common_tables):
        print(f"  • {table}")
    
    # Tables only in production
    prod_only = prod_set - local_set
    if prod_only:
        print(f"\n🌐 Tables only in production ({len(prod_only)}):")
        for table in sorted(prod_only):
            print(f"  • {table}")
    
    # Tables only in local
    local_only = local_set - prod_set
    if local_only:
        print(f"\n🏠 Tables only in local ({len(local_only)}):")
        for table in sorted(local_only):
            print(f"  • {table}")
    
    if prod_set == local_set:
        print(f"\n🎉 Perfect match! Both databases have the same tables.")
    else:
        print(f"\n⚠️  Databases have different table structures.")

if __name__ == "__main__":
    asyncio.run(main()) 