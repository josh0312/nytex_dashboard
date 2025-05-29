"""
Sync catalog data directly from Square API to populate catalog tables
"""
import asyncio
import aiohttp
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config
from app.database.models.catalog import CatalogItem, CatalogVariation, CatalogCategory
import json

class SquareCatalogSyncService:
    """Service for syncing catalog data directly from Square API"""
    
    def __init__(self):
        self.square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
        self.square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'sandbox')
        
        if self.square_environment.lower() == 'production':
            self.base_url = "https://connect.squareup.com"
        else:
            self.base_url = "https://connect.squareupsandbox.com"
            
        self.timeout = aiohttp.ClientTimeout(total=300)

    async def sync_catalog_to_production(self):
        """Sync catalog data from Square API to production database"""
        try:
            print("🔄 Starting catalog sync from Square API...")
            print("=" * 60)
            
            if not self.square_access_token:
                print("❌ Square access token not configured")
                return False
            
            # Production database connection
            prod_url = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
            engine = create_async_engine(prod_url, echo=False, connect_args={"ssl": "require"})
            
            async with engine.begin() as conn:
                # Clear existing catalog data
                print("🗑️  Clearing existing catalog data...")
                await conn.execute(delete(CatalogVariation))
                await conn.execute(delete(CatalogItem))
                await conn.execute(delete(CatalogCategory))
                
                # Fetch and insert categories
                print("📂 Syncing categories...")
                categories = await self.fetch_categories()
                category_count = 0
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
                    category_count += 1
                
                print(f"✅ Synced {category_count} categories")
                
                # Fetch and insert items
                print("📦 Syncing items...")
                items = await self.fetch_items()
                item_count = 0
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
                    item_count += 1
                
                print(f"✅ Synced {item_count} items")
                
                # Fetch and insert variations
                print("🔧 Syncing variations...")
                variations = await self.fetch_variations()
                variation_count = 0
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
                        'price_money': json.dumps(variation_data.get('price_money', {})),
                        'is_deleted': False,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                    variation_count += 1
                
                print(f"✅ Synced {variation_count} variations")
                
                print(f"\n🎉 Catalog sync completed!")
                print(f"   Categories: {category_count}")
                print(f"   Items: {item_count}")
                print(f"   Variations: {variation_count}")
                
            await engine.dispose()
            return True
            
        except Exception as e:
            print(f"❌ Error during catalog sync: {str(e)}")
            return False

    async def fetch_categories(self) -> List[Dict[str, Any]]:
        """Fetch categories from Square API"""
        return await self.fetch_catalog_objects("CATEGORY")

    async def fetch_items(self) -> List[Dict[str, Any]]:
        """Fetch items from Square API"""
        return await self.fetch_catalog_objects("ITEM")

    async def fetch_variations(self) -> List[Dict[str, Any]]:
        """Fetch variations from Square API"""
        return await self.fetch_catalog_objects("ITEM_VARIATION")

    async def fetch_catalog_objects(self, object_type: str) -> List[Dict[str, Any]]:
        """Fetch catalog objects of specified type from Square API"""
        try:
            url = f"{self.base_url}/v2/catalog/search"
            headers = {
                'Authorization': f'Bearer {self.square_access_token}',
                'Content-Type': 'application/json'
            }
            
            all_objects = []
            cursor = None
            page = 1
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                while True:
                    body = {
                        "object_types": [object_type],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    print(f"   Fetching {object_type} page {page}...")
                    
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            objects = data.get('objects', [])
                            all_objects.extend(objects)
                            
                            print(f"   Retrieved {len(objects)} {object_type}s (total: {len(all_objects)})")
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                            page += 1
                        else:
                            error_text = await response.text()
                            print(f"   ❌ Square API error: {response.status} - {error_text}")
                            break
            
            return all_objects
            
        except Exception as e:
            print(f"   ❌ Error fetching {object_type}: {str(e)}")
            return []

async def main():
    """Main function"""
    print("🔄 Square Catalog Sync to Production")
    print("=" * 60)
    
    service = SquareCatalogSyncService()
    success = await service.sync_catalog_to_production()
    
    if success:
        print("\n✅ Catalog sync completed successfully!")
        print("   You can now run inventory sync to get actual inventory data.")
    else:
        print("\n❌ Catalog sync failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main()) 