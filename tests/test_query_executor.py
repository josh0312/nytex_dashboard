#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '.')
from app.services.reports.query_executor import QueryExecutor

async def test_query_executor():
    try:
        executor = QueryExecutor()
        df = await executor.execute_query_to_df('missing_category_inventory')
        print(f'✅ Query executed successfully. Found {len(df)} items.')
        print('📋 Columns:', list(df.columns))
        
        if len(df) > 0:
            print('\n📊 Sample data:')
            print(df.head())
        else:
            print('\n📝 No data found (which is expected with clean category data)')
            
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query_executor()) 