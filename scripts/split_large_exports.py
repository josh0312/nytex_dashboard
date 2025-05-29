#!/usr/bin/env python3
"""
Split large export files into smaller chunks for import
"""
import json
import os
import math

def split_large_file(file_path, max_records_per_chunk=1000):
    """Split a large JSON export file into smaller chunks"""
    
    print(f"📦 Processing: {file_path}")
    
    # Load the original file
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    table_name = data['table']
    columns = data['columns']
    records = data['data']
    total_records = len(records)
    
    print(f"   📊 Total records: {total_records:,}")
    
    if total_records <= max_records_per_chunk:
        print(f"   ✅ File is small enough, no splitting needed")
        return [file_path]
    
    # Calculate number of chunks
    num_chunks = math.ceil(total_records / max_records_per_chunk)
    print(f"   🔧 Splitting into {num_chunks} chunks")
    
    # Create directory for chunks
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    chunk_dir = f"app/static/exports/production_sync/chunks/{base_name}"
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_files = []
    
    for i in range(num_chunks):
        start_idx = i * max_records_per_chunk
        end_idx = min((i + 1) * max_records_per_chunk, total_records)
        chunk_records = records[start_idx:end_idx]
        
        chunk_data = {
            'table': table_name,
            'columns': columns,
            'count': len(chunk_records),
            'chunk_info': {
                'chunk_number': i + 1,
                'total_chunks': num_chunks,
                'start_record': start_idx + 1,
                'end_record': end_idx
            },
            'exported_at': data['exported_at'],
            'data': chunk_records
        }
        
        chunk_file = f"{chunk_dir}/{base_name}_chunk_{i+1:03d}.json"
        with open(chunk_file, 'w') as f:
            json.dump(chunk_data, f, indent=2)
        
        chunk_files.append(chunk_file)
        print(f"      📄 Chunk {i+1}: {len(chunk_records):,} records -> {chunk_file}")
    
    print(f"   ✅ Split complete: {num_chunks} chunks created")
    return chunk_files

def create_chunked_import_script(chunk_files_by_table):
    """Create import script for chunked files"""
    
    script_content = """#!/bin/bash
# Chunked Production Data Import Script
# Generated for large file imports

echo "🚀 Starting Chunked Production Data Import"

"""
    
    table_order = ['orders', 'order_line_items', 'payments', 'tenders', 'operating_seasons', 
                   'catalog_location_availability', 'catalog_vendor_info', 'inventory_counts', 
                   'square_item_library_export']
    
    total_tables = len(chunk_files_by_table)
    table_counter = 1
    
    for table in table_order:
        if table in chunk_files_by_table:
            chunk_files = chunk_files_by_table[table]
            
            if len(chunk_files) == 1:
                # Single file, use original
                script_content += f"""
echo ""
echo "📊 {table_counter}/{total_tables}: Importing {table} (single file)"
curl -X POST "https://nytex-dashboard-932676587025.us-central1.run.app/admin/import-table-data" \\
     -H "Content-Type: application/json" \\
     -d '@{chunk_files[0]}'

if [ $? -eq 0 ]; then
    echo "✅ {table} imported successfully"
else
    echo "❌ {table} import failed"
    exit 1
fi
"""
            else:
                # Multiple chunks
                script_content += f"""
echo ""
echo "📊 {table_counter}/{total_tables}: Importing {table} ({len(chunk_files)} chunks)"
"""
                
                for i, chunk_file in enumerate(chunk_files, 1):
                    script_content += f"""
echo "   📦 Chunk {i}/{len(chunk_files)} for {table}"
curl -X POST "https://nytex-dashboard-932676587025.us-central1.run.app/admin/import-table-data" \\
     -H "Content-Type: application/json" \\
     -d '@{chunk_file}'

if [ $? -eq 0 ]; then
    echo "   ✅ {table} chunk {i} imported successfully"
else
    echo "   ❌ {table} chunk {i} import failed"
    exit 1
fi
"""
                
                script_content += f"""
echo "✅ {table} import completed ({len(chunk_files)} chunks)"
"""
            
            table_counter += 1
    
    script_content += """
echo ""
echo "🎉 Chunked import completed successfully!"
echo "Next steps:"
echo "1. Verify data with: curl https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync-status"
echo "2. Run comparison: python scripts/compare_local_vs_production.py"
"""
    
    script_file = "app/static/exports/production_sync/import_chunked_data.sh"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_file, 0o755)
    print(f"\n🚀 Chunked import script created: {script_file}")
    return script_file

if __name__ == "__main__":
    # Files to potentially split
    files_to_check = [
        "app/static/exports/production_sync/orders.json",
        "app/static/exports/production_sync/order_line_items.json", 
        "app/static/exports/production_sync/payments.json",
        "app/static/exports/production_sync/tenders.json",
        "app/static/exports/production_sync/operating_seasons.json",
        "app/static/exports/production_sync/catalog_location_availability.json",
        "app/static/exports/production_sync/catalog_vendor_info.json",
        "app/static/exports/production_sync/inventory_counts.json",
        "app/static/exports/production_sync/square_item_library_export.json"
    ]
    
    chunk_files_by_table = {}
    
    print("🔪 SPLITTING LARGE EXPORT FILES")
    print("=" * 50)
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            chunk_files = split_large_file(file_path, max_records_per_chunk=1000)
            
            # Extract table name
            with open(file_path, 'r') as f:
                data = json.load(f)
                table_name = data['table']
            
            chunk_files_by_table[table_name] = chunk_files
        else:
            print(f"   ⚠️ File not found: {file_path}")
    
    # Create chunked import script
    script_file = create_chunked_import_script(chunk_files_by_table)
    
    print(f"\n✅ Chunking complete!")
    print(f"Run: {script_file}") 