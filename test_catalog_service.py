#!/usr/bin/env python3
"""Test script for the catalog service"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_session
from app.services.square_catalog_service import SquareCatalogService

async def test_catalog_service():
    """Test the catalog service functionality"""
    try:
        print("Testing catalog service...")
        
        async with get_session() as session:
            service = SquareCatalogService()
            status = await service.get_export_status(session)
            print(f"✅ Database connection works! Status: {status}")
            
    except Exception as e:
        print(f"❌ Error testing catalog service: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_catalog_service()) 