#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def check_inventory():
    async with get_session() as session:
        # Check catalog_inventory table structure
        result = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'catalog_inventory'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        print('Catalog inventory table columns:')
        for row in columns:
            print(f'  {row[0]}: {row[1]}')
        
        # Check sample inventory
        result = await session.execute(text('SELECT COUNT(*) FROM catalog_inventory'))
        count = result.scalar()
        print(f'\nTotal inventory records: {count}')
        
        if count > 0:
            result = await session.execute(text('SELECT * FROM catalog_inventory LIMIT 3'))
            inventory = result.fetchall()
            print('\nSample inventory:')
            for inv in inventory:
                print(f'  {inv}')

if __name__ == "__main__":
    asyncio.run(check_inventory()) 