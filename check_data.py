#!/usr/bin/env python3
"""Check if there's existing data in the table"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

async def check_data():
    """Check if there's data in the table"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM square_item_library_export"))
            count = result.scalar()
            print(f"Table has {count} rows")
            
            if count > 0:
                # Show a sample row
                result = await conn.execute(text("SELECT * FROM square_item_library_export LIMIT 1"))
                row = result.fetchone()
                print(f"Sample row: {dict(row._mapping) if row else 'None'}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_data()) 