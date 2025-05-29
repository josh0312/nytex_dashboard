"""
Daily Sync Script - Automated data synchronization for production
This script should be run daily to keep production data up to date
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
import logging

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.complete_production_sync import CompleteProductionSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_sync.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('daily_sync')

class DailySyncService:
    """Daily synchronization service"""
    
    def __init__(self):
        self.sync_service = CompleteProductionSync()
    
    async def run_daily_sync(self):
        """Run daily synchronization"""
        try:
            logger.info("=" * 80)
            logger.info("🌅 Starting Daily Production Sync")
            logger.info(f"📅 Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info("=" * 80)
            
            # Run the complete sync
            success = await self.sync_service.run_complete_sync()
            
            if success:
                logger.info("🎉 Daily sync completed successfully!")
                logger.info("✅ Production data is now up to date")
                return True
            else:
                logger.error("❌ Daily sync failed!")
                logger.error("🔧 Manual intervention may be required")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during daily sync: {str(e)}", exc_info=True)
            return False
        finally:
            logger.info("=" * 80)
            logger.info("🌙 Daily sync process completed")
            logger.info("=" * 80)

async def main():
    """Main function"""
    daily_sync = DailySyncService()
    success = await daily_sync.run_daily_sync()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 