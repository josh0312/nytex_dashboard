#!/usr/bin/env python3
"""Test script for the catalog export functionality"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_session
from app.services.square_catalog_service import SquareCatalogService

async def test_export():
    """Test the catalog export functionality"""
    try:
        print("Testing catalog export...")
        
        async with get_session() as session:
            service = SquareCatalogService()
            
            # Test export
            result = await service.export_catalog_to_database(session)
            print(f"✅ Export result: {result}")
            
            # Test status after export
            status = await service.get_export_status(session)
            print(f"✅ Status after export: {status}")
            
    except Exception as e:
        print(f"❌ Error testing export: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_export()) 