#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def test():
    async with get_session() as session:
        query = '''
        SELECT 
            item_name,
            COALESCE(sku, 'No SKU') AS sku,
            COALESCE(description, 'No Description') AS description,
            COALESCE(categories, 'No Category') AS category,
            CASE 
                WHEN price IS NOT NULL 
                THEN TO_CHAR(price, '$999,999.99') 
                ELSE 'No Price' 
            END AS price,
            COALESCE(default_vendor_name, 'No Vendor') AS vendor_name,
            CASE 
                WHEN location_data->>'Aubrey'->>'enabled' = 'Y' THEN 'Yes' 
                ELSE 'No' 
            END AS aubrey_enabled
        FROM square_item_library_export
        WHERE archived != 'Y'
        ORDER BY item_name
        LIMIT 5
        '''
        result = await session.execute(text(query))
        items = result.fetchall()
        columns = result.keys()
        
        print(f'Found {len(items)} items with {len(columns)} columns:')
        print(f'Columns: {", ".join(columns)}')
        print()
        
        for i, item in enumerate(items):
            print(f'Item {i+1}:')
            print(f'  Name: {item[0]}')
            print(f'  SKU: {item[1]}')
            print(f'  Description: {item[2][:50]}...')
            print(f'  Category: {item[3]}')
            print(f'  Price: {item[4]}')
            print(f'  Vendor: {item[5]}')
            print(f'  Aubrey Enabled: {item[6]}')
            print('---')

if __name__ == "__main__":
    asyncio.run(test()) 