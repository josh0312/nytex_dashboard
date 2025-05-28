#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def check_categories():
    async with get_session() as session:
        # Check category distribution
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as total_items, 
                COUNT(category_id) as with_category, 
                COUNT(*) - COUNT(category_id) as without_category 
            FROM catalog_items 
            WHERE is_deleted = false AND is_archived = false
        """))
        stats = result.fetchone()
        print(f'Total items: {stats.total_items}')
        print(f'With category: {stats.with_category}')
        print(f'Without category: {stats.without_category}')
        
        # Check for empty string categories
        result = await session.execute(text("""
            SELECT COUNT(*) as empty_category_count
            FROM catalog_items 
            WHERE is_deleted = false AND is_archived = false
            AND (category_id = '' OR category_id IS NULL)
        """))
        empty_count = result.fetchone()
        print(f'Empty/NULL categories: {empty_count.empty_category_count}')
        
        # Show top categories
        result = await session.execute(text("""
            SELECT category_id, COUNT(*) as count 
            FROM catalog_items 
            WHERE is_deleted = false AND is_archived = false 
            GROUP BY category_id 
            ORDER BY count DESC 
            LIMIT 10
        """))
        categories = result.fetchall()
        print('\nTop categories:')
        for cat in categories:
            category_display = cat.category_id if cat.category_id else 'NULL/Empty'
            print(f'  {category_display}: {cat.count} items')
        
        # Check if there are items with variations but no categories
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT ci.id) as items_with_variations_no_category
            FROM catalog_items ci
            JOIN catalog_variations cv ON ci.id = cv.item_id
            WHERE ci.is_deleted = false 
            AND ci.is_archived = false
            AND cv.is_deleted = false
            AND (ci.category_id IS NULL OR ci.category_id = '')
        """))
        no_cat_with_variations = result.fetchone()
        print(f'\nItems with variations but no category: {no_cat_with_variations.items_with_variations_no_category}')

if __name__ == "__main__":
    asyncio.run(check_categories()) 