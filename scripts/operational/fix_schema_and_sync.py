#!/usr/bin/env python3
"""
Fix Schema and Sync Data Script
Comprehensive script to fix order_line_items schema and sync missing data.
Works in both development and production environments.

Usage:
    python scripts/operational/fix_schema_and_sync.py --env dev --step schema
    python scripts/operational/fix_schema_and_sync.py --env prod --step schema
    python scripts/operational/fix_schema_and_sync.py --env dev --step sync
    python scripts/operational/fix_schema_and_sync.py --env prod --step sync
    python scripts/operational/fix_schema_and_sync.py --env dev --step all
    python scripts/operational/fix_schema_and_sync.py --env prod --step all
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SchemaAndSyncFixer:
    """Handles schema fixes and data synchronization"""
    
    def __init__(self, environment='dev'):
        self.environment = environment
        self.setup_database_urls()
        
    def setup_database_urls(self):
        """Setup database URLs based on environment"""
        if self.environment == 'dev':
            self.db_url = "postgresql+asyncpg://joshgoble@localhost:5432/square_data_sync"
            self.sync_db_url = "postgresql://joshgoble@localhost:5432/square_data_sync"
        elif self.environment == 'prod':
            self.db_url = "postgresql+asyncpg://nytex_user:NytexSecure2024!@localhost:5434/square_data_sync"
            self.sync_db_url = "postgresql://nytex_user:NytexSecure2024!@localhost:5434/square_data_sync"
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
            
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Database URL: {self.db_url[:50]}...")
    
    async def check_current_state(self):
        """Check current database state"""
        logger.info("🔍 Checking current database state...")
        
        engine = create_async_engine(self.db_url)
        
        try:
            async with engine.begin() as conn:
                # Check order counts
                result = await conn.execute(text("SELECT COUNT(*) FROM orders"))
                order_count = result.scalar()
                
                result = await conn.execute(text("SELECT COUNT(*) FROM order_line_items"))
                line_item_count = result.scalar()
                
                # Check primary key constraint
                result = await conn.execute(text("""
                    SELECT conname, pg_get_constraintdef(oid) 
                    FROM pg_constraint 
                    WHERE conrelid = 'order_line_items'::regclass 
                    AND contype = 'p'
                """))
                constraint_info = result.fetchone()
                
                logger.info(f"📊 Current State:")
                logger.info(f"   Orders: {order_count:,}")
                logger.info(f"   Order Line Items: {line_item_count:,}")
                logger.info(f"   Primary Key: {constraint_info[1] if constraint_info else 'None'}")
                
                return {
                    'order_count': order_count,
                    'line_item_count': line_item_count,
                    'primary_key': constraint_info[1] if constraint_info else None
                }
                
        finally:
            await engine.dispose()
    
    def fix_schema(self):
        """Fix the schema using Alembic migration"""
        logger.info("🔧 Fixing schema using Alembic migration...")
        
        # Set environment variables for the migration
        env = os.environ.copy()
        env['SQLALCHEMY_DATABASE_URI'] = self.sync_db_url
        env['PYTHONPATH'] = '.'
        
        try:
            # Run the migration
            cmd = ['alembic', '-c', 'migrations/alembic.ini', 'upgrade', 'head']
            
            logger.info(f"🚀 Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent
            )
            
            if result.returncode == 0:
                logger.info("✅ Schema migration completed successfully!")
                logger.info("Migration output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"   {line}")
                return True
            else:
                logger.error("❌ Schema migration failed!")
                logger.error("Error output:")
                for line in result.stderr.split('\n'):
                    if line.strip():
                        logger.error(f"   {line}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error running migration: {e}")
            return False
    
    async def sync_missing_data(self):
        """Sync missing data using the historical sync approach"""
        logger.info("🔄 Starting data synchronization...")
        
        if self.environment == 'prod':
            # For production, we'll call the existing API endpoint
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = "https://nytex-dashboard-932676587025.us-central1.run.app/admin/historical-orders-sync"
                
                logger.info(f"📡 Calling production sync API: {url}")
                
                async with session.post(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("✅ Production sync initiated successfully!")
                        logger.info(f"Response: {data}")
                        return True
                    else:
                        logger.error(f"❌ Production sync failed: {response.status}")
                        text = await response.text()
                        logger.error(f"Response: {text}")
                        return False
        else:
            # For development, run the historical sync script directly
            logger.info("🔄 Running historical sync script for development...")
            
            # Import and run the historical sync
            from scripts.historical_orders_sync import HistoricalOrdersSync
            
            try:
                sync_service = HistoricalOrdersSync()
                await sync_service.run_historical_sync()
                logger.info("✅ Development sync completed successfully!")
                return True
            except Exception as e:
                logger.error(f"❌ Development sync failed: {e}")
                return False
    
    async def run_step(self, step):
        """Run a specific step"""
        logger.info(f"🚀 Starting step: {step}")
        logger.info("=" * 60)
        
        # Always check current state first
        initial_state = await self.check_current_state()
        
        if step in ['schema', 'all']:
            logger.info("\n" + "=" * 60)
            logger.info("STEP 1: SCHEMA FIX")
            logger.info("=" * 60)
            
            if not self.fix_schema():
                logger.error("❌ Schema fix failed. Stopping.")
                return False
            
            # Check state after schema fix
            logger.info("\n🔍 Checking state after schema fix...")
            post_schema_state = await self.check_current_state()
            
            # Verify the schema was fixed
            if 'PRIMARY KEY (order_id, uid)' not in post_schema_state['primary_key']:
                logger.error("❌ Schema fix did not work correctly!")
                return False
            
            logger.info("✅ Schema fix verified successfully!")
        
        if step in ['sync', 'all']:
            logger.info("\n" + "=" * 60)
            logger.info("STEP 2: DATA SYNCHRONIZATION")
            logger.info("=" * 60)
            
            if not await self.sync_missing_data():
                logger.error("❌ Data sync failed. Stopping.")
                return False
            
            # Check final state
            logger.info("\n🔍 Checking final state...")
            final_state = await self.check_current_state()
            
            # Compare with expected values
            expected_orders = 30391 if self.environment == 'dev' else 30391
            expected_line_items = 159535 if self.environment == 'dev' else 159535
            
            logger.info(f"\n📊 FINAL RESULTS:")
            logger.info(f"   Orders: {final_state['order_count']:,} (expected: {expected_orders:,})")
            logger.info(f"   Line Items: {final_state['line_item_count']:,} (expected: {expected_line_items:,})")
            
            if final_state['order_count'] >= expected_orders * 0.95:  # Allow 5% tolerance
                logger.info("✅ Data sync completed successfully!")
            else:
                logger.warning("⚠️  Data sync may be incomplete. Please investigate.")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 ALL STEPS COMPLETED!")
        logger.info("=" * 60)
        
        return True

async def main():
    parser = argparse.ArgumentParser(description='Fix schema and sync data')
    parser.add_argument('--env', choices=['dev', 'prod'], required=True,
                       help='Environment to run against')
    parser.add_argument('--step', choices=['schema', 'sync', 'all'], required=True,
                       help='Step to execute')
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Fix Schema and Sync Data Script")
    logger.info(f"Environment: {args.env}")
    logger.info(f"Step: {args.step}")
    
    fixer = SchemaAndSyncFixer(args.env)
    success = await fixer.run_step(args.step)
    
    if success:
        logger.info("🎉 Script completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Script failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 