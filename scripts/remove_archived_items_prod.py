#!/usr/bin/env python3
"""
Remove Archived Items from Production Database

This script fetches all items from Square API (including archived ones) and removes
any archived items from our production database tables.

Usage:
    python scripts/remove_archived_items_prod.py [--dry-run]
"""

import asyncio
import sys
import os
import argparse
import aiohttp
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_square_credentials():
    """Get Square API credentials from environment"""
    access_token = os.environ.get('SQUARE_ACCESS_TOKEN')
    environment = os.environ.get('SQUARE_ENVIRONMENT', 'production')
    
    if not access_token:
        print("❌ SQUARE_ACCESS_TOKEN environment variable not set")
        sys.exit(1)
    
    if environment.lower() == 'production':
        base_url = "https://connect.squareup.com"
    else:
        base_url = "https://connect.squareupsandbox.com"
    
    return access_token, base_url

def get_production_db_connection():
    """Get production database connection"""
    # Use Cloud SQL proxy connection with password
    database_url = "postgresql://nytex_user:NytexSecure2024!@localhost:5433/square_data_sync"
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()

async def fetch_all_catalog_items(access_token: str, base_url: str) -> list:
    """Fetch ALL catalog items from Square API (including archived)"""
    print("🔍 Fetching all catalog items from Square API...")
    
    all_items = []
    cursor = None
    page = 1
    
    timeout = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            # Use SearchCatalogItems to get ALL items (archived and non-archived)
            url = f"{base_url}/v2/catalog/search-catalog-items"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "limit": 100,  # Maximum allowed limit for SearchCatalogItems
                "archived_state": "ARCHIVED_STATE_ALL"  # Get both archived and non-archived
            }
            
            if cursor:
                payload["cursor"] = cursor
            
            print(f"   📄 Fetching page {page}...")
            
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    all_items.extend(items)
                    
                    print(f"   ✅ Retrieved {len(items)} items (total: {len(all_items)})")
                    
                    cursor = data.get('cursor')
                    if not cursor:
                        break
                    page += 1
                else:
                    error_text = await response.text()
                    print(f"❌ Square API error: {response.status} - {error_text}")
                    sys.exit(1)
    
    return all_items

def identify_archived_items(items: list) -> list:
    """Identify which items are archived"""
    archived_items = []
    
    for item in items:
        if item.get('type') != 'ITEM':
            continue
            
        item_data = item.get('item_data', {})
        if item_data.get('is_archived', False):
            archived_items.append({
                'id': item['id'],
                'name': item_data.get('name', 'Unknown'),
                'is_archived': True
            })
    
    return archived_items

def remove_archived_items_from_db(session, archived_items: list, dry_run: bool = False) -> int:
    """Remove archived items from database tables"""
    if not archived_items:
        print("✅ No archived items found to remove")
        return 0
    
    print(f"\n📋 Found {len(archived_items)} archived items in Square:")
    for item in archived_items[:10]:  # Show first 10
        print(f"   • {item['name']} ({item['id']})")
    if len(archived_items) > 10:
        print(f"   ... and {len(archived_items) - 10} more")
    
    if dry_run:
        print(f"\n🔍 DRY RUN: Would remove {len(archived_items)} archived items from database")
        return 0
    
    removed_count = 0
    
    print(f"\n🗑️  Removing archived items from database...")
    
    for item in archived_items:
        item_id = item['id']
        item_name = item['name']
        
        # Check if item exists in our database
        existing_item = session.execute(
            text("SELECT id FROM catalog_items WHERE id = :item_id"),
            {"item_id": item_id}
        ).fetchone()
        
        if existing_item:
            # Remove related records first, then the item (in correct order)
            # 1. Remove vendor info (references variations)
            session.execute(
                text("DELETE FROM catalog_vendor_info WHERE variation_id IN (SELECT id FROM catalog_variations WHERE item_id = :item_id)"),
                {"item_id": item_id}
            )
            # 2. Remove inventory (references variations)
            session.execute(
                text("DELETE FROM catalog_inventory WHERE variation_id IN (SELECT id FROM catalog_variations WHERE item_id = :item_id)"),
                {"item_id": item_id}
            )
            # 3. Remove location availability (references item)
            session.execute(
                text("DELETE FROM catalog_location_availability WHERE item_id = :item_id"),
                {"item_id": item_id}
            )
            # 4. Remove variations (references item)
            session.execute(
                text("DELETE FROM catalog_variations WHERE item_id = :item_id"),
                {"item_id": item_id}
            )
            # 5. Finally remove the item
            session.execute(
                text("DELETE FROM catalog_items WHERE id = :item_id"),
                {"item_id": item_id}
            )
            print(f"   ✅ Removed: {item_name} ({item_id}) and related records")
            removed_count += 1
        else:
            print(f"   ⏭️  Not in DB: {item_name} ({item_id})")
    
    if removed_count > 0:
        session.commit()
        print(f"\n✅ Successfully removed {removed_count} archived items from database")
    else:
        print(f"\n✅ No archived items were found in the database to remove")
    
    return removed_count

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Remove archived items from production database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without actually removing')
    args = parser.parse_args()
    
    print("🚀 Starting archived items removal script")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE REMOVAL'}")
    print("=" * 60)
    
    try:
        # Get Square API credentials
        access_token, base_url = get_square_credentials()
        print(f"✅ Square API configured: {base_url}")
        
        # Get database connection
        session = get_production_db_connection()
        print("✅ Production database connected")
        
        # Fetch all items from Square
        all_items = await fetch_all_catalog_items(access_token, base_url)
        print(f"✅ Retrieved {len(all_items)} total items from Square API")
        
        # Identify archived items
        archived_items = identify_archived_items(all_items)
        
        # Remove archived items from database
        removed_count = remove_archived_items_from_db(session, archived_items, args.dry_run)
        
        session.close()
        
        print("\n" + "=" * 60)
        print("🎉 Script completed successfully!")
        print(f"   Archived items in Square: {len(archived_items)}")
        print(f"   Items removed from DB: {removed_count}")
        
        if args.dry_run and archived_items:
            print(f"\n💡 To actually remove the items, run without --dry-run flag")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 