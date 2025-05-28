#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def check_vendors():
    async with get_session() as session:
        # Check vendors table structure
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'vendors'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        print('Vendors table columns:')
        for row in columns:
            print(f'  {row[0]}: {row[1]}')
        
        # Check sample vendors
        result = await session.execute(text('SELECT * FROM vendors LIMIT 5'))
        vendors = result.fetchall()
        print('\nSample vendors:')
        for vendor in vendors:
            print(f'  {vendor}')

if __name__ == "__main__":
    asyncio.run(check_vendors()) 