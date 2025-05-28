#!/usr/bin/env python3
"""Check the actual table structure"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

async def check_table():
    """Check what columns exist in the table"""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'square_item_library_export' ORDER BY ordinal_position"))
            columns = result.fetchall()
            print('Current table columns:')
            for col in columns:
                print(f'  {col[0]}: {col[1]}')
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_table()) 