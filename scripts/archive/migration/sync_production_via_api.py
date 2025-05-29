#!/usr/bin/env python3
"""
Sync Production Data via API - Uses production API endpoints to sync data
This approach avoids direct database connections and uses the web interface

Usage:
    python scripts/sync_production_via_api.py
"""

import asyncio
import aiohttp
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionAPISyncService:
    """Sync production data using API endpoints"""
    
    def __init__(self):
        self.base_url = "https://nytex-dashboard-932676587025.us-central1.run.app"
        self.timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout
    
    async def run_complete_sync(self):
        """Run complete sync via production API"""
        try:
            print("🚀 Starting Production Sync via API")
            print("=" * 80)
            print(f"🌐 Production URL: {self.base_url}")
            print("=" * 80)
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Step 1: Check if production is accessible
                print("\n🔍 Step 1: Checking production accessibility...")
                accessible = await self.check_production_accessible(session)
                if not accessible:
                    print("❌ Production not accessible - stopping")
                    return False
                
                # Step 2: Run complete sync
                print("\n🚀 Step 2: Running complete sync...")
                success = await self.trigger_complete_sync(session)
                if not success:
                    print("❌ Complete sync failed - stopping")
                    return False
                
                # Step 3: Verify data
                print("\n📊 Step 3: Verifying data...")
                await self.verify_data(session)
                
                print("\n🎉 Production sync completed successfully!")
                return True
                
        except Exception as e:
            print(f"❌ Error during production sync: {str(e)}")
            return False
    
    async def check_production_accessible(self, session):
        """Check if production is accessible"""
        try:
            url = f"{self.base_url}/"
            print(f"   📡 Checking: {url}")
            
            async with session.get(url) as response:
                print(f"   📊 Response status: {response.status}")
                
                if response.status == 200:
                    print("   ✅ Production is accessible")
                    return True
                else:
                    print(f"   ❌ Production returned status: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error checking production: {str(e)}")
            return False
    
    async def trigger_complete_sync(self, session):
        """Trigger complete sync via API"""
        try:
            url = f"{self.base_url}/admin/complete-sync"
            print(f"   📡 Triggering sync: {url}")
            
            async with session.post(url) as response:
                print(f"   📊 Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        print("   ✅ Complete sync successful")
                        print(f"   📋 Message: {result.get('message', 'No message')}")
                        return True
                    else:
                        print(f"   ❌ Sync failed: {result.get('error', 'Unknown error')}")
                        return False
                else:
                    response_text = await response.text()
                    print(f"   ❌ API error: {response.status}")
                    print(f"   📄 Response: {response_text}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error triggering sync: {str(e)}")
            return False
    
    async def verify_data(self, session):
        """Verify that data was synced correctly"""
        try:
            # Check admin status
            url = f"{self.base_url}/admin/status"
            print(f"   📡 Checking status: {url}")
            
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success') and result.get('data'):
                        data = result['data']
                        print("   📊 Production Database Status:")
                        
                        for table, count in data.items():
                            if isinstance(count, int):
                                print(f"      {table:<30} {count:>10,} rows")
                        
                        # Check if we have essential data
                        essential_tables = ['locations', 'catalog_items', 'catalog_variations', 'catalog_inventory']
                        missing_data = []
                        
                        for table in essential_tables:
                            if table not in data or data[table] == 0:
                                missing_data.append(table)
                        
                        if missing_data:
                            print(f"   ⚠️  Missing data in: {', '.join(missing_data)}")
                        else:
                            print("   ✅ All essential data is present")
                    else:
                        print("   ⚠️  Unable to get detailed status")
                else:
                    print(f"   ⚠️  Status check failed: {response.status}")
                    
        except Exception as e:
            print(f"   ⚠️  Error verifying data: {str(e)}")

async def main():
    """Main function"""
    sync_service = ProductionAPISyncService()
    success = await sync_service.run_complete_sync()
    
    if success:
        print("\n🎉 Production sync via API successful!")
        print("   Production database should now have all necessary data.")
        print("   Reports should display actual data.")
        print(f"   🌐 Check reports at: {sync_service.base_url}/reports/inventory/low-stock")
    else:
        print("\n❌ Production sync via API failed!")
        print("   Check the errors above and retry.")

if __name__ == "__main__":
    asyncio.run(main()) 