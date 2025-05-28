#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def check_vendor_data():
    async with get_session() as session:
        # Check vendor_info table structure
        print("Checking catalog_vendor_info table...")
        result = await session.execute(text('SELECT * FROM catalog_vendor_info LIMIT 5'))
        vendor_info = result.fetchall()
        print(f'Found {len(vendor_info)} vendor info records')
        for row in vendor_info:
            print(f'  ID: {row[0]}, Variation ID: {row[1]}, Vendor ID: {row[2]}')
        
        # Check distinct vendor_ids
        result = await session.execute(text('SELECT DISTINCT vendor_id FROM catalog_vendor_info WHERE vendor_id IS NOT NULL LIMIT 10'))
        vendor_ids = result.fetchall()
        print(f'\nDistinct Vendor IDs ({len(vendor_ids)} found):')
        for row in vendor_ids:
            print(f'  {row[0]}')
        
        # Check if vendor_id looks like vendor names or IDs
        result = await session.execute(text('''
            SELECT vendor_id, COUNT(*) as count 
            FROM catalog_vendor_info 
            WHERE vendor_id IS NOT NULL 
            GROUP BY vendor_id 
            ORDER BY count DESC 
            LIMIT 10
        '''))
        vendor_counts = result.fetchall()
        print(f'\nTop Vendor IDs by usage:')
        for row in vendor_counts:
            print(f'  {row[0]}: {row[1]} items')

if __name__ == "__main__":
    asyncio.run(check_vendor_data()) 