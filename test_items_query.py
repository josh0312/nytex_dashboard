#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import get_session
from sqlalchemy import text

async def test_simple_query():
    """Test a simple query first to see what data we have"""
    async with get_session() as session:
        try:
            # Simple query to see what we have
            simple_query = """
            SELECT 
                item_name,
                sku,
                description,
                categories,
                price,
                default_vendor_name,
                default_vendor_code,
                default_unit_cost
            FROM square_item_library_export 
            WHERE archived != 'Y'
            ORDER BY item_name
            LIMIT 5
            """
            
            result = await session.execute(text(simple_query))
            items = result.fetchall()
            
            print(f'Simple query executed successfully! Found {len(items)} sample items:')
            
            # Get column names
            columns = result.keys()
            print(f'Columns: {", ".join(columns)}')
            print()
            
            for i, item in enumerate(items):
                print(f'Item {i+1}:')
                print(f'  Name: {item[0]}')
                print(f'  SKU: {item[1]}')
                print(f'  Description: {item[2][:50] if item[2] else "None"}...')
                print(f'  Category: {item[3]}')
                print(f'  Price: ${item[4]}' if item[4] else 'No Price')
                print(f'  Vendor: {item[5]}')
                print('---')
                
        except Exception as e:
            print(f'Simple query error: {e}')
            import traceback
            traceback.print_exc()

async def test_complex_query():
    """Test the complex query from the file"""
    async with get_session() as session:
        try:
            with open('app/database/queries/items_inventory.sql', 'r') as f:
                query = f.read()
            
            # Remove comments and get just the query part
            query_lines = []
            in_query = False
            for line in query.split('\n'):
                if line.strip().startswith('WITH') or in_query:
                    in_query = True
                    if not line.strip().startswith('--'):
                        query_lines.append(line)
            
            clean_query = '\n'.join(query_lines).strip()
            
            # Remove any existing ORDER BY and add our own with LIMIT
            if 'ORDER BY' in clean_query:
                clean_query = clean_query.split('ORDER BY')[0] + 'ORDER BY item_name LIMIT 3'
            else:
                clean_query += ' LIMIT 3'
            
            result = await session.execute(text(clean_query))
            items = result.fetchall()
            
            if items:
                print(f'Complex query executed successfully! Found {len(items)} sample items:')
                
                # Get column names
                columns = result.keys()
                print(f'Columns ({len(columns)}): {", ".join(columns)}')
                print()
                
                for i, item in enumerate(items):
                    print(f'Item {i+1}: {item[0]}')
                    print('---')
            else:
                print('Complex query executed but returned no results')
                
        except Exception as e:
            print(f'Complex query error: {e}')

if __name__ == "__main__":
    print("=== Testing Simple Query ===")
    asyncio.run(test_simple_query())
    print("\n=== Testing Complex Query ===")
    asyncio.run(test_complex_query()) 