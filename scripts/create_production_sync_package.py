#!/usr/bin/env python3
"""
Create production sync package - export local data for production import
"""
import asyncio
import json
import csv
import os
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text
from app.database import get_session

def json_serializer(obj):
    """Custom JSON serializer for datetime, date, and decimal objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

async def create_sync_package():
    """Create a complete sync package for production"""
    
    print("📦 CREATING PRODUCTION SYNC PACKAGE")
    print("=" * 50)
    
    # Create exports directory
    os.makedirs("app/static/exports/production_sync", exist_ok=True)
    
    # Tables to export
    tables_to_export = {
        'orders': {'priority': 1, 'desc': 'Core business transactions'},
        'order_line_items': {'priority': 1, 'desc': 'Transaction details'},
        'payments': {'priority': 1, 'desc': 'Payment records'}, 
        'tenders': {'priority': 1, 'desc': 'Payment methods'},
        'operating_seasons': {'priority': 2, 'desc': 'Business seasons'},
        'catalog_location_availability': {'priority': 3, 'desc': 'Item availability'},
        'catalog_vendor_info': {'priority': 3, 'desc': 'Vendor information'},
        'inventory_counts': {'priority': 3, 'desc': 'Inventory tracking'},
        'square_item_library_export': {'priority': 3, 'desc': 'Item library'}
    }
    
    sync_commands = []
    total_records = 0
    
    async with get_session() as session:
        for table_name, info in tables_to_export.items():
            print(f"\n🔄 Processing: {table_name}")
            print(f"   {info['desc']}")
            
            try:
                # Get record count
                count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                count = count_result.scalar()
                
                if count == 0:
                    print(f"   ⏭️ Skipping - no data")
                    continue
                
                print(f"   📊 Records: {count:,}")
                total_records += count
                
                # Export data to JSON file for easy import
                export_file = f"app/static/exports/production_sync/{table_name}.json"
                
                # Get all data
                data_result = await session.execute(text(f'SELECT * FROM "{table_name}"'))
                rows = data_result.fetchall()
                columns = data_result.keys()
                
                # Convert to JSON-serializable format
                export_data = []
                for row in rows:
                    record = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if isinstance(value, datetime):
                            record[col] = value.isoformat()
                        elif isinstance(value, date):
                            record[col] = value.isoformat()
                        elif isinstance(value, Decimal):
                            record[col] = float(value)
                        elif value is None:
                            record[col] = None
                        else:
                            record[col] = value
                    export_data.append(record)
                
                # Write to file
                with open(export_file, 'w') as f:
                    json.dump({
                        'table': table_name,
                        'columns': list(columns),
                        'count': len(export_data),
                        'exported_at': datetime.now().isoformat(),
                        'data': export_data
                    }, f, indent=2, default=json_serializer)
                
                print(f"   ✅ Exported to: {export_file}")
                
                # Create import command
                sync_commands.append({
                    'table': table_name,
                    'priority': info['priority'],
                    'count': count,
                    'file': export_file,
                    'curl_command': f"""curl -X POST "https://nytex-dashboard-932676587025.us-central1.run.app/admin/import-table-data" \\
     -H "Content-Type: application/json" \\
     -d '@{export_file}'"""
                })
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
    
    # Create import script
    script_content = f"""#!/bin/bash
# Production Data Import Script
# Generated: {datetime.now().isoformat()}
# Total records to import: {total_records:,}

echo "🚀 Starting Production Data Import"
echo "Total records to sync: {total_records:,}"
echo "Tables to sync: {len(sync_commands)}"

"""
    
    # Sort by priority
    sync_commands.sort(key=lambda x: x['priority'])
    
    for i, cmd in enumerate(sync_commands, 1):
        script_content += f"""
echo ""
echo "📊 {i}/{len(sync_commands)}: Importing {cmd['table']} ({cmd['count']:,} records)"
{cmd['curl_command']}

if [ $? -eq 0 ]; then
    echo "✅ {cmd['table']} imported successfully"
else
    echo "❌ {cmd['table']} import failed"
    exit 1
fi
"""
    
    script_content += """
echo ""
echo "🎉 Production import completed successfully!"
echo "Next steps:"
echo "1. Verify data with: curl https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync-status"
echo "2. Run comparison: python scripts/compare_local_vs_production.py"
"""
    
    script_file = "app/static/exports/production_sync/import_all_data.sh"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_file, 0o755)
    
    print(f"\n" + "=" * 50)
    print(f"📦 SYNC PACKAGE CREATED")
    print(f"=" * 50)
    print(f"📊 Total records: {total_records:,}")
    print(f"📁 Export location: app/static/exports/production_sync/")
    print(f"🚀 Import script: {script_file}")
    print(f"\n🎯 TO SYNC PRODUCTION:")
    print(f"1. Deploy the import endpoint (next step)")
    print(f"2. Run: ./{script_file}")
    print(f"3. Validate: python scripts/compare_local_vs_production.py")
    
    return len(sync_commands), total_records

if __name__ == "__main__":
    asyncio.run(create_sync_package()) 