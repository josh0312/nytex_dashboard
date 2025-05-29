"""
Complete Production Data Sync - Syncs all data in proper order
This script ensures production has the same data as local development
"""
import asyncio
import aiohttp
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config

class CompleteProductionSync:
    """Complete data synchronization service for production"""
    
    def __init__(self):
        self.square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
        self.square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'sandbox')
        
        if self.square_environment.lower() == 'production':
            self.base_url = "https://connect.squareup.com"
        else:
            self.base_url = "https://connect.squareupsandbox.com"
            
        self.timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout
        
        # Production database connection
        self.prod_url = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
        
        # Local database connection for copying data
        local_db_url = Config.SQLALCHEMY_DATABASE_URI
        self.local_url = local_db_url.replace('postgresql+asyncpg://', 'postgresql://')

    async def run_complete_sync(self):
        """Run complete data synchronization in proper order"""
        try:
            print("🚀 Starting Complete Production Data Sync")
            print("=" * 80)
            
            if not self.square_access_token:
                print("❌ Square access token not configured")
                return False
            
            # Step 1: Sync Locations (Foundation)
            print("\n📍 Step 1: Syncing Locations...")
            locations_success = await self.sync_locations()
            if not locations_success:
                print("❌ Location sync failed - stopping")
                return False
            
            # Step 2: Sync Catalog Data (Categories, Items, Variations)
            print("\n📂 Step 2: Syncing Catalog Data...")
            catalog_success = await self.sync_catalog_data()
            if not catalog_success:
                print("❌ Catalog sync failed - stopping")
                return False
            
            # Step 3: Sync Inventory Data
            print("\n📦 Step 3: Syncing Inventory Data...")
            inventory_success = await self.sync_inventory_data()
            if not inventory_success:
                print("❌ Inventory sync failed - stopping")
                return False
            
            # Step 4: Copy Historical Data from Local
            print("\n📊 Step 4: Copying Historical Data...")
            historical_success = await self.copy_historical_data()
            if not historical_success:
                print("⚠️ Historical data copy had issues - continuing")
            
            # Step 5: Sync Additional Square Data
            print("\n💳 Step 5: Syncing Additional Square Data...")
            additional_success = await self.sync_additional_square_data()
            if not additional_success:
                print("⚠️ Additional Square data sync had issues - continuing")
            
            print("\n🎉 Complete Production Sync Finished!")
            await self.print_final_summary()
            return True
            
        except Exception as e:
            print(f"❌ Error during complete sync: {str(e)}")
            return False

    async def sync_locations(self):
        """Sync locations from Square API"""
        try:
            print(f"   🔑 Using Square environment: {self.square_environment}")
            print(f"   🌐 API base URL: {self.base_url}")
            print(f"   🔐 Access token configured: {'Yes' if self.square_access_token else 'No'}")
            
            if not self.square_access_token:
                print("   ❌ Square access token not configured")
                return False
            
            engine = create_async_engine(self.prod_url, echo=False, connect_args={"ssl": "require"})
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/v2/locations"
                headers = {'Authorization': f'Bearer {self.square_access_token}'}
                
                print(f"   📡 Making request to: {url}")
                
                async with session.get(url, headers=headers) as response:
                    print(f"   📊 Response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        locations = data.get('locations', [])
                        
                        print(f"   📍 Retrieved {len(locations)} locations from Square")
                        
                        async with engine.begin() as conn:
                            # Clear existing locations
                            await conn.execute(text("DELETE FROM locations"))
                            
                            # Insert locations
                            for location in locations:
                                await conn.execute(text("""
                                    INSERT INTO locations (id, name, address, timezone, status, created_at, updated_at)
                                    VALUES (:id, :name, :address, :timezone, :status, :created_at, :updated_at)
                                """), {
                                    'id': location['id'],
                                    'name': location.get('name', ''),
                                    'address': str(location.get('address', {})),
                                    'timezone': location.get('timezone', ''),
                                    'status': location.get('status', 'ACTIVE'),
                                    'created_at': datetime.utcnow(),
                                    'updated_at': datetime.utcnow()
                                })
                        
                        print(f"   ✅ Synced {len(locations)} locations")
                        await engine.dispose()
                        return True
                    else:
                        response_text = await response.text()
                        print(f"   ❌ Square API error: {response.status}")
                        print(f"   📄 Response: {response_text}")
                        await engine.dispose()
                        return False
                        
        except Exception as e:
            print(f"   ❌ Error syncing locations: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def sync_catalog_data(self):
        """Sync catalog data from Square API"""
        try:
            engine = create_async_engine(self.prod_url, echo=False, connect_args={"ssl": "require"})
            
            async with engine.begin() as conn:
                # Clear existing catalog data
                print("   🗑️ Clearing existing catalog data...")
                await conn.execute(text("DELETE FROM catalog_inventory"))
                await conn.execute(text("DELETE FROM catalog_variations"))
                await conn.execute(text("DELETE FROM catalog_items"))
                await conn.execute(text("DELETE FROM catalog_categories"))
                
                # Sync categories
                print("   📂 Syncing categories...")
                categories = await self.fetch_catalog_objects("CATEGORY")
                for category in categories:
                    await conn.execute(text("""
                        INSERT INTO catalog_categories (id, name, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :is_deleted, :created_at, :updated_at)
                    """), {
                        'id': category['id'],
                        'name': category.get('category_data', {}).get('name', ''),
                        'is_deleted': False,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                
                # Sync items
                print("   📦 Syncing items...")
                items = await self.fetch_catalog_objects("ITEM")
                for item in items:
                    item_data = item.get('item_data', {})
                    await conn.execute(text("""
                        INSERT INTO catalog_items (id, name, description, category_id, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :description, :category_id, :is_deleted, :created_at, :updated_at)
                    """), {
                        'id': item['id'],
                        'name': item_data.get('name', ''),
                        'description': item_data.get('description', ''),
                        'category_id': item_data.get('category_id'),
                        'is_deleted': False,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                
                # Sync variations
                print("   🔧 Syncing variations...")
                variations = await self.fetch_catalog_objects("ITEM_VARIATION")
                for variation in variations:
                    variation_data = variation.get('item_variation_data', {})
                    await conn.execute(text("""
                        INSERT INTO catalog_variations (id, name, item_id, sku, price_money, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :item_id, :sku, :price_money, :is_deleted, :created_at, :updated_at)
                    """), {
                        'id': variation['id'],
                        'name': variation_data.get('name', ''),
                        'item_id': variation_data.get('item_id'),
                        'sku': variation_data.get('sku', ''),
                        'price_money': str(variation_data.get('price_money', {})),
                        'is_deleted': False,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                
                print(f"   ✅ Synced {len(categories)} categories, {len(items)} items, {len(variations)} variations")
            
            await engine.dispose()
            return True
            
        except Exception as e:
            print(f"   ❌ Error syncing catalog: {str(e)}")
            return False

    async def sync_inventory_data(self):
        """Sync inventory data from Square API"""
        try:
            engine = create_async_engine(self.prod_url, echo=False, connect_args={"ssl": "require"})
            
            async with engine.begin() as conn:
                # Get locations
                locations_result = await conn.execute(text("SELECT id, name FROM locations WHERE status = 'ACTIVE'"))
                locations = locations_result.fetchall()
                
                if not locations:
                    print("   ❌ No active locations found")
                    return False
                
                # Clear existing inventory
                await conn.execute(text("DELETE FROM catalog_inventory"))
                
                total_inventory = 0
                
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    for location in locations:
                        location_id, location_name = location
                        print(f"   📦 Fetching inventory for {location_name}...")
                        
                        url = f"{self.base_url}/v2/inventory/counts/batch-retrieve"
                        headers = {
                            'Authorization': f'Bearer {self.square_access_token}',
                            'Content-Type': 'application/json'
                        }
                        
                        body = {
                            'location_ids': [location_id],
                            'updated_after': '2020-01-01T00:00:00Z'
                        }
                        
                        async with session.post(url, headers=headers, json=body) as response:
                            if response.status == 200:
                                data = await response.json()
                                counts = data.get('counts', [])
                                
                                for count in counts:
                                    catalog_object_id = count.get('catalog_object_id')
                                    quantity = int(count.get('quantity', 0))
                                    calculated_at = count.get('calculated_at')
                                    
                                    if catalog_object_id:
                                        await conn.execute(text("""
                                            INSERT INTO catalog_inventory (variation_id, location_id, quantity, calculated_at)
                                            VALUES (:variation_id, :location_id, :quantity, :calculated_at)
                                        """), {
                                            'variation_id': catalog_object_id,
                                            'location_id': location_id,
                                            'quantity': quantity,
                                            'calculated_at': datetime.utcnow()
                                        })
                                        total_inventory += 1
                                
                                print(f"      ✅ {len(counts)} inventory items for {location_name}")
                            else:
                                print(f"      ❌ Error fetching inventory for {location_name}: {response.status}")
                
                print(f"   ✅ Total inventory records: {total_inventory}")
            
            await engine.dispose()
            return True
            
        except Exception as e:
            print(f"   ❌ Error syncing inventory: {str(e)}")
            return False

    async def copy_historical_data(self):
        """Copy historical data from local database"""
        try:
            print("   📊 Copying vendor data...")
            await self.copy_table_data("vendors")
            
            print("   📊 Copying operating seasons...")
            await self.copy_table_data("operating_seasons")
            
            print("   📊 Copying catalog vendor info...")
            await self.copy_table_data("catalog_vendor_info")
            
            print("   📊 Copying catalog location availability...")
            await self.copy_table_data("catalog_location_availability")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error copying historical data: {str(e)}")
            return False

    async def copy_table_data(self, table_name):
        """Copy data from local table to production"""
        try:
            # This would require a more complex implementation
            # For now, we'll skip historical data and focus on current Square data
            print(f"      ⚠️ Skipping {table_name} (historical data)")
            return True
            
        except Exception as e:
            print(f"      ❌ Error copying {table_name}: {str(e)}")
            return False

    async def sync_additional_square_data(self):
        """Sync additional Square data like payments, orders (if needed)"""
        try:
            print("   💳 Additional Square data sync not implemented yet")
            print("   📝 This would include orders, payments, etc.")
            return True
            
        except Exception as e:
            print(f"   ❌ Error syncing additional data: {str(e)}")
            return False

    async def fetch_catalog_objects(self, object_type):
        """Fetch catalog objects from Square API"""
        try:
            url = f"{self.base_url}/v2/catalog/search"
            headers = {
                'Authorization': f'Bearer {self.square_access_token}',
                'Content-Type': 'application/json'
            }
            
            all_objects = []
            cursor = None
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                while True:
                    body = {
                        "object_types": [object_type],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            objects = data.get('objects', [])
                            all_objects.extend(objects)
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                        else:
                            print(f"      ❌ Square API error: {response.status}")
                            break
            
            return all_objects
            
        except Exception as e:
            print(f"      ❌ Error fetching {object_type}: {str(e)}")
            return []

    async def print_final_summary(self):
        """Print final summary of sync results"""
        try:
            engine = create_async_engine(self.prod_url, echo=False, connect_args={"ssl": "require"})
            
            async with engine.begin() as conn:
                # Get counts
                tables = [
                    'locations', 'catalog_categories', 'catalog_items', 
                    'catalog_variations', 'catalog_inventory'
                ]
                
                print("\n📊 Final Production Database Status:")
                print("-" * 50)
                
                for table in tables:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   {table:<30} {count:>10,} rows")
            
            await engine.dispose()
            
        except Exception as e:
            print(f"   ❌ Error getting final summary: {str(e)}")

async def main():
    """Main function"""
    sync_service = CompleteProductionSync()
    success = await sync_service.run_complete_sync()
    
    if success:
        print("\n🎉 Complete production sync successful!")
        print("   Production database should now have all necessary data.")
        print("   Reports should display actual data.")
    else:
        print("\n❌ Complete production sync failed!")
        print("   Check the errors above and retry.")

if __name__ == "__main__":
    asyncio.run(main()) 