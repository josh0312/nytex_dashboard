#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def check_vendor_tables():
    async with get_session() as session:
        # Check for vendor-related tables
        print("Checking for vendor-related tables...")
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%vendor%' OR table_name LIKE '%supplier%')
        """))
        vendor_tables = result.fetchall()
        print(f'Vendor-related tables: {[row[0] for row in vendor_tables]}')
        
    # Use separate session for catalog_vendor_info structure
    async with get_session() as session:
        # Check catalog_vendor_info structure
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'catalog_vendor_info'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        print(f'\ncatalog_vendor_info columns:')
        for row in columns:
            print(f'  {row[0]}: {row[1]}')
    
    # Check if vendor_id contains readable names or just IDs
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT vendor_id, COUNT(*) as count 
            FROM catalog_vendor_info 
            WHERE vendor_id IS NOT NULL 
            GROUP BY vendor_id 
            ORDER BY count DESC 
            LIMIT 5
        """))
        vendor_usage = result.fetchall()
        print(f'\nTop vendor IDs by usage:')
        for row in vendor_usage:
            print(f'  {row[0]}: {row[1]} items')
            
        # Check if any vendor_id looks like a readable name
        result = await session.execute(text("""
            SELECT DISTINCT vendor_id 
            FROM catalog_vendor_info 
            WHERE vendor_id IS NOT NULL 
            AND (LENGTH(vendor_id) > 20 OR vendor_id ~ '[A-Z]{2,}')
            LIMIT 10
        """))
        readable_vendors = result.fetchall()
        print(f'\nVendor IDs that might be readable names:')
        for row in readable_vendors:
            print(f'  {row[0]}')

if __name__ == "__main__":
    asyncio.run(check_vendor_tables()) 