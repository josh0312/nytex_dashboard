#!/usr/bin/env python3
"""
Production Database Population Script

This script connects directly to the production Cloud SQL database
and runs all necessary sync operations to populate it with data from Square.

Usage:
    python scripts/populate_production_db.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import Config
from app.database import get_session
from app.services.square_catalog_service import SquareCatalogService
from app.services.square_inventory_service import SquareInventoryService
from app.logger import logger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import logging

# Configure logging for this script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/production_sync.log', mode='a')
    ]
)

class ProductionDBPopulator:
    """Handles populating the production database with Square data"""
    
    def __init__(self):
        # Override config to use production Cloud SQL database
        self.db_url = self._construct_production_db_url()
        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    def _construct_production_db_url(self):
        """Construct the production database URL"""
        # Production Cloud SQL connection details
        db_user = "nytex_user"
        db_pass = "NytexSecure2024!"
        db_name = "nytex_dashboard"
        db_host = "34.67.201.62"  # Cloud SQL public IP
        db_port = "5432"
        
        return f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    async def check_database_connection(self):
        """Test the database connection"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"✅ Connected to production database: {version}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to production database: {str(e)}")
            return False
    
    async def check_current_data_status(self):
        """Check what data currently exists in the database"""
        try:
            async with self.async_session() as session:
                # Check for existing data
                checks = {
                    'locations': "SELECT COUNT(*) FROM locations",
                    'catalog_items': "SELECT COUNT(*) FROM catalog_items",
                    'catalog_variations': "SELECT COUNT(*) FROM catalog_variations", 
                    'catalog_inventory': "SELECT COUNT(*) FROM catalog_inventory",
                    'square_exports': "SELECT COUNT(*) FROM square_item_library_export",
                    'operating_seasons': "SELECT COUNT(*) FROM operating_seasons"
                }
                
                status = {}
                for table, query in checks.items():
                    try:
                        result = await session.execute(text(query))
                        count = result.scalar()
                        status[table] = count
                        logger.info(f"📊 {table}: {count} records")
                    except Exception as e:
                        status[table] = f"Error: {str(e)}"
                        logger.warning(f"⚠️  Could not check {table}: {str(e)}")
                
                return status
        except Exception as e:
            logger.error(f"❌ Error checking database status: {str(e)}")
            return {}
    
    async def sync_catalog_data(self):
        """Sync catalog data from Square"""
        try:
            logger.info("🔄 Starting catalog data sync...")
            
            async with self.async_session() as session:
                catalog_service = SquareCatalogService()
                result = await catalog_service.export_catalog_to_database(session)
                
                if result['success']:
                    items_count = result.get('items_exported', 'unknown')
                    logger.info(f"✅ Catalog sync completed: {items_count} items exported")
                    return True
                else:
                    logger.error(f"❌ Catalog sync failed: {result.get('error', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error during catalog sync: {str(e)}")
            return False
    
    async def sync_inventory_data(self):
        """Sync inventory data from Square"""
        try:
            logger.info("🔄 Starting inventory data sync...")
            
            async with self.async_session() as session:
                inventory_service = SquareInventoryService()
                result = await inventory_service.fetch_inventory_from_square(session)
                
                if result['success']:
                    inventory_updated = result.get('total_inventory_updated', 0)
                    catalog_updates = result.get('catalog_updates', {})
                    
                    items_updated = catalog_updates.get('items_updated', 0)
                    variations_updated = catalog_updates.get('variations_updated', 0)
                    
                    logger.info(f"✅ Inventory sync completed:")
                    logger.info(f"   📦 {inventory_updated} inventory records updated")
                    logger.info(f"   📋 {items_updated} catalog items updated")
                    logger.info(f"   🔧 {variations_updated} variations updated")
                    return True
                else:
                    logger.error(f"❌ Inventory sync failed: {result.get('error', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error during inventory sync: {str(e)}")
            return False
    
    async def populate_database(self):
        """Run the complete database population process"""
        logger.info("🚀 Starting production database population...")
        
        # Step 1: Check database connection
        if not await self.check_database_connection():
            logger.error("❌ Cannot proceed without database connection")
            return False
        
        # Step 2: Check current status
        logger.info("📊 Checking current database status...")
        status = await self.check_current_data_status()
        
        # Step 3: Sync catalog data (items, variations, categories)
        logger.info("📋 Syncing catalog data from Square...")
        catalog_success = await self.sync_catalog_data()
        
        if not catalog_success:
            logger.error("❌ Catalog sync failed - stopping")
            return False
        
        # Step 4: Sync inventory data
        logger.info("📦 Syncing inventory data from Square...")
        inventory_success = await self.sync_inventory_data()
        
        if not inventory_success:
            logger.error("❌ Inventory sync failed")
            return False
        
        # Step 5: Final status check
        logger.info("📊 Checking final database status...")
        final_status = await self.check_current_data_status()
        
        logger.info("🎉 Production database population completed successfully!")
        logger.info("📋 Summary:")
        for table, count in final_status.items():
            logger.info(f"   {table}: {count}")
        
        return True
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

async def main():
    """Main execution function"""
    print("🚀 NyTex Production Database Population")
    print("="*50)
    
    populator = ProductionDBPopulator()
    
    try:
        success = await populator.populate_database()
        
        if success:
            print("\n✅ Database population completed successfully!")
            print("🌐 Your production app should now have data:")
            print("   https://nytex-dashboard-932676587025.us-central1.run.app")
        else:
            print("\n❌ Database population failed - check logs for details")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    finally:
        await populator.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 