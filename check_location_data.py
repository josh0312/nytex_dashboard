#!/usr/bin/env python3
import asyncio
import sys
import json
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def check_location_data():
    async with get_session() as session:
        result = await session.execute(text('SELECT item_name, location_data FROM square_item_library_export LIMIT 3'))
        items = result.fetchall()
        
        print('Sample location_data structure:')
        for item in items:
            print(f'Item: {item[0]}')
            print(f'Location data: {json.dumps(item[1], indent=2) if item[1] else "None"}')
            print('---')

if __name__ == "__main__":
    asyncio.run(check_location_data()) 