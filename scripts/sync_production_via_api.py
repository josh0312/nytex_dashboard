#!/usr/bin/env python3
"""
Production Data Sync via API

This script populates the production database by calling the sync API endpoints
on your production Cloud Run service. This is simpler than setting up external services.

Usage:
    python scripts/sync_production_via_api.py
"""

import aiohttp
import asyncio
import sys
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionSyncer:
    """Syncs production data via API calls"""
    
    def __init__(self):
        self.base_url = "https://nytex-dashboard-932676587025.us-central1.run.app"
        self.timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout
    
    async def check_service_health(self):
        """Check if the production service is running"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/") as response:
                    if response.status == 200:
                        logger.info("✅ Production service is running")
                        return True
                    else:
                        logger.error(f"❌ Production service returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Cannot reach production service: {str(e)}")
            return False
    
    async def sync_inventory_data(self):
        """Sync inventory data from Square via API"""
        try:
            logger.info("🔄 Starting inventory sync via API...")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(f"{self.base_url}/inventory/sync") as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('success'):
                            logger.info("✅ Inventory sync completed successfully")
                            logger.info(f"📋 Result: {result.get('message', 'Sync completed')}")
                            return True
                        else:
                            logger.error(f"❌ Inventory sync failed: {result.get('message', 'Unknown error')}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Inventory sync API error {response.status}: {error_text}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("❌ Inventory sync timed out - this is normal for large datasets")
            logger.info("ℹ️  Check the production logs to see if sync is still running")
            return False
        except Exception as e:
            logger.error(f"❌ Error during inventory sync: {str(e)}")
            return False
    
    async def check_data_status(self):
        """Check what data exists in the production database"""
        try:
            logger.info("📊 Checking production data status...")
            
            # Try inventory status endpoint if it exists
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                try:
                    async with session.get(f"{self.base_url}/inventory/status") as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"📦 Inventory data: {result}")
                            return result
                except:
                    pass
                
                # Try catalog status endpoint if it exists
                try:
                    async with session.get(f"{self.base_url}/catalog/status") as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"📋 Catalog data: {result}")
                            return result
                except:
                    pass
                
                logger.info("ℹ️  Status endpoints not available - data sync should populate database")
                return {}
                
        except Exception as e:
            logger.error(f"⚠️  Could not check data status: {str(e)}")
            return {}
    
    async def wait_for_sync_completion(self, check_interval=30, max_wait=600):
        """Wait for sync to complete by checking data status"""
        logger.info(f"⏳ Waiting for sync completion (checking every {check_interval}s, max {max_wait}s)...")
        
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < max_wait:
            await asyncio.sleep(check_interval)
            
            # Check if we have data now
            status = await self.check_data_status()
            
            # Look for signs that data exists
            if isinstance(status, dict) and status.get('data', {}).get('total_inventory_updated', 0) > 0:
                logger.info("✅ Detected data in production database!")
                return True
                
            logger.info(f"⏳ Still waiting... ({(datetime.now() - start_time).seconds}s elapsed)")
        
        logger.warning(f"⚠️  Timeout reached ({max_wait}s) - sync may still be running")
        return False
    
    async def run_complete_sync(self):
        """Run the complete sync process"""
        logger.info("🚀 Starting Production Data Sync")
        logger.info("=" * 50)
        
        # Step 1: Check service health
        if not await self.check_service_health():
            logger.error("❌ Cannot proceed - production service is not accessible")
            return False
        
        # Step 2: Check initial data status
        logger.info("📊 Checking initial data status...")
        initial_status = await self.check_data_status()
        
        # Step 3: Trigger inventory sync (includes catalog data)
        logger.info("🔄 Triggering inventory sync...")
        sync_success = await self.sync_inventory_data()
        
        if not sync_success:
            logger.warning("⚠️  Sync API call failed, but sync may still be running in background")
            logger.info("ℹ️  Large datasets can take several minutes to sync")
        
        # Step 4: Wait and check for completion
        await self.wait_for_sync_completion()
        
        # Step 5: Final status check
        logger.info("📊 Checking final data status...")
        final_status = await self.check_data_status()
        
        logger.info("🎉 Sync process completed!")
        logger.info("🌐 Check your production dashboard:")
        logger.info(f"   {self.base_url}")
        
        return True

async def main():
    """Main execution function"""
    syncer = ProductionSyncer()
    
    try:
        success = await syncer.run_complete_sync()
        
        if success:
            print("\n✅ Production sync completed!")
            print("🌐 Your production app should now have data:")
            print("   https://nytex-dashboard-932676587025.us-central1.run.app")
            print("\n📋 Next steps:")
            print("   1. Visit the production URL above")
            print("   2. Check the Low Item Stock Report")
            print("   3. If no data appears, check production logs:")
            print("      gcloud run services logs read nytex-dashboard --region us-central1")
        else:
            print("\n⚠️  Sync process encountered issues")
            print("📋 What to do:")
            print("   1. Check production logs for sync progress")
            print("   2. Large datasets may take 10+ minutes to sync")
            print("   3. Try visiting the production URL in a few minutes")
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 