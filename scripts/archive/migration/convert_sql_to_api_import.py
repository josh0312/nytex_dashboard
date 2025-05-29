#!/usr/bin/env python3
"""
Convert SQL exports to API imports
Since direct database connection failed, use the working API endpoints
"""
import asyncio
import json
import re
import sys
import os
import requests
from datetime import datetime
from typing import List, Dict

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.database import get_session

# API endpoint
API_BASE_URL = "https://nytex-dashboard-932676587025.us-central1.run.app"

async def get_latest_exports():
    """Get the latest successful exports from the direct copy attempt"""
    # Since we know the exports worked, let's check what we have locally
    # and use the existing chunked JSON exports instead
    
    export_dir = "app/static/exports/production_sync"
    
    if not os.path.exists(export_dir):
        print("❌ No export directory found")
        return []
    
    available_files = []
    for filename in os.listdir(export_dir):
        if filename.endswith('.json') and not filename.startswith('import'):
            filepath = os.path.join(export_dir, filename)
            # Get file size
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            table_name = filename.replace('.json', '')
            available_files.append((table_name, filepath, size_mb))
    
    return available_files

async def import_via_api(table_name: str, json_file: str):
    """Import data via the API endpoint"""
    print(f"🔄 Importing {table_name} via API...")
    
    try:
        # Read the JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print(f"   📊 Records to import: {data.get('count', 0):,}")
        
        # For large files, we need to use the chunked approach
        if data.get('count', 0) > 1000:
            print(f"   📦 Large file detected - checking for chunks...")
            
            # Check if chunks exist
            chunk_dir = f"app/static/exports/production_sync/chunks/{table_name}"
            if os.path.exists(chunk_dir):
                chunk_files = [f for f in os.listdir(chunk_dir) if f.endswith('.json')]
                chunk_files.sort()  # Process in order
                
                print(f"   📦 Found {len(chunk_files)} chunks")
                
                total_imported = 0
                for chunk_file in chunk_files:
                    chunk_path = os.path.join(chunk_dir, chunk_file)
                    chunk_imported = await import_single_chunk(chunk_path)
                    total_imported += chunk_imported
                    print(f"      ✅ {chunk_file}: {chunk_imported} records")
                
                print(f"   📈 Total imported for {table_name}: {total_imported:,}")
                return total_imported
        
        # For small files, import directly
        response = requests.post(
            f"{API_BASE_URL}/admin/import-table-data",
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            imported = result.get('records_imported', 0)
            print(f"   ✅ Successfully imported {imported:,} records")
            return imported
        else:
            print(f"   ❌ API error: {response.status_code}")
            print(f"   Response: {response.text[:100]}")
            return 0
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return 0

async def import_single_chunk(chunk_file: str) -> int:
    """Import a single chunk file"""
    try:
        with open(chunk_file, 'r') as f:
            chunk_data = json.load(f)
        
        response = requests.post(
            f"{API_BASE_URL}/admin/import-table-data",
            json=chunk_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('records_imported', 0)
        else:
            print(f"      ❌ Chunk error: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"      ❌ Chunk error: {str(e)}")
        return 0

async def main():
    """Main execution function"""
    print("🎯 API-BASED DATA IMPORT")
    print("=" * 50)
    print("Strategy: Use working API endpoints with existing exports")
    
    # Check if we have the JSON exports already
    available_files = await get_latest_exports()
    
    if not available_files:
        print("❌ No JSON export files found!")
        print("💡 Run: python scripts/create_production_sync_package.py first")
        return False
    
    print(f"\n📋 Available exports:")
    total_size = 0
    for table_name, filepath, size_mb in available_files:
        print(f"  📄 {table_name:<35} {size_mb:>8.1f} MB")
        total_size += size_mb
    
    print(f"\n📊 Total export size: {total_size:.1f} MB")
    
    # Import in priority order
    priority_order = [
        'orders', 'order_line_items', 'payments', 'tenders',
        'operating_seasons', 'catalog_location_availability', 
        'catalog_vendor_info', 'inventory_counts', 'square_item_library_export'
    ]
    
    total_imported = 0
    successful_tables = []
    failed_tables = []
    
    for table_name in priority_order:
        # Find the file for this table
        table_file = None
        for name, filepath, size_mb in available_files:
            if name == table_name:
                table_file = filepath
                break
        
        if table_file:
            imported = await import_via_api(table_name, table_file)
            total_imported += imported
            
            if imported > 0:
                successful_tables.append((table_name, imported))
            else:
                failed_tables.append(table_name)
    
    # Summary
    print(f"\n" + "=" * 50)
    print(f"🎯 IMPORT RESULTS SUMMARY")
    print(f"=" * 50)
    
    if successful_tables:
        print(f"\n✅ SUCCESSFUL IMPORTS ({len(successful_tables)} tables):")
        for table_name, count in successful_tables:
            print(f"   {table_name:<35} {count:>8,} records")
        print(f"\n📊 Total records imported: {total_imported:,}")
    
    if failed_tables:
        print(f"\n❌ FAILED IMPORTS ({len(failed_tables)} tables):")
        for table_name in failed_tables:
            print(f"   {table_name}")
    
    success_rate = len(successful_tables) / len(available_files) * 100
    print(f"\n📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print(f"\n🎉 API Import completed successfully!")
        print(f"🔄 Next step: python scripts/compare_local_vs_production.py")
        return True
    else:
        print(f"\n⚠️ API Import partially completed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main()) 