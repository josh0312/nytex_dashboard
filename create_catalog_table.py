#!/usr/bin/env python3
"""
Script to create the square_item_library_export table in the database.
This is a temporary solution to get the catalog export functionality working.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.database.models.square_catalog_export import SquareItemLibraryExport

async def create_table():
    """Create the square_item_library_export table"""
    try:
        print("Creating square_item_library_export table...")
        
        async with engine.begin() as conn:
            # Create only the new table
            await conn.run_sync(SquareItemLibraryExport.__table__.create, checkfirst=True)
        
        print("✅ Table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(create_table()) 