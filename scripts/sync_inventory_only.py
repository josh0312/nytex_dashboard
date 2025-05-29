#!/usr/bin/env python3
"""
Production Inventory-Only Sync

This script syncs only inventory data to production, bypassing the 
catalog export dependency. This should be enough to get reports working.

Usage:
    python scripts/sync_inventory_only.py
"""

import aiohttp
import asyncio
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

async def sync_inventory_only():
    """Sync only inventory data to production"""
    base_url = "https://nytex-dashboard-932676587025.us-central1.run.app"
    timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
    
    try:
        logger.info("🚀 Starting inventory-only sync to production...")
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Check service health first
            logger.info("🏥 Checking service health...")
            async with session.get(f"{base_url}/") as response:
                if response.status != 200:
                    logger.error(f"❌ Service not healthy: {response.status}")
                    return False
            
            logger.info("✅ Service is healthy")
            
            # Trigger inventory sync
            logger.info("📦 Triggering inventory sync...")
            async with session.post(f"{base_url}/inventory/sync") as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get('success'):
                        logger.info("✅ Inventory sync successful!")
                        logger.info(f"📋 Message: {result.get('message', 'Sync completed')}")
                        
                        # Extract details if available
                        data = result.get('data', {})
                        if isinstance(data, dict):
                            inventory_count = data.get('total_inventory_updated', 'unknown')
                            catalog_updates = data.get('catalog_updates', {})
                            items_updated = catalog_updates.get('items_updated', 0)
                            variations_updated = catalog_updates.get('variations_updated', 0)
                            
                            logger.info(f"📊 Results:")
                            logger.info(f"   • {inventory_count} inventory records")
                            logger.info(f"   • {items_updated} catalog items updated")
                            logger.info(f"   • {variations_updated} variations updated")
                        
                        return True
                    else:
                        logger.error(f"❌ Sync failed: {result.get('message', 'Unknown error')}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API error {response.status}: {error_text}")
                    
                    # Check if it's a Square token issue
                    if "Square access token not configured" in error_text:
                        logger.error("🔑 Square access token is missing!")
                        logger.info("📋 To fix this, run:")
                        logger.info("   gcloud run services update nytex-dashboard --region us-central1 \\")
                        logger.info("     --set-env-vars SQUARE_ACCESS_TOKEN=your_actual_token")
                    
                    return False
                    
    except asyncio.TimeoutError:
        logger.warning("⏰ Request timed out - sync may still be running in background")
        logger.info("ℹ️  Large datasets can take several minutes to process")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return False

async def main():
    """Main execution"""
    print("🔄 NyTex Production Inventory Sync")
    print("=" * 40)
    
    success = await sync_inventory_only()
    
    if success:
        print("\n✅ Inventory sync completed!")
        print("🌐 Your production app should now have inventory data")
        print("🔗 Check it out: https://nytex-dashboard-932676587025.us-central1.run.app")
        print("\n📋 Try the Low Item Stock Report to see if data is loading")
    else:
        print("\n❌ Sync failed or timed out")
        print("📋 Next steps:")
        print("   1. Ensure Square access token is configured (see logs above)")
        print("   2. Check production logs: gcloud run services logs read nytex-dashboard --region us-central1")
        print("   3. Large syncs may take 10+ minutes to complete")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 