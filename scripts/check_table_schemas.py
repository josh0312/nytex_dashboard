#!/usr/bin/env python3
"""
Check table schemas for orders, payments, transactions
"""
import asyncio
from sqlalchemy import text
from app.database import get_session

async def check_schemas():
    """Check schemas for key tables"""
    async with get_session() as session:
        tables = ['orders', 'payments', 'tenders', 'order_line_items']
        
        for table in tables:
            print(f"\n📋 {table.upper()} TABLE SCHEMA:")
            print("-" * 50)
            
            try:
                # Get schema
                result = await session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    default = f" DEFAULT {col[3]}" if col[3] else ""
                    print(f"  {col[0]:<25} {col[1]:<20} {nullable}{default}")
                
                # Get sample data
                count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                print(f"\n  📊 Total records: {count:,}")
                
                if count > 0:
                    sample_result = await session.execute(text(f'SELECT * FROM "{table}" LIMIT 2'))
                    print(f"  🔍 Sample data:")
                    for i, row in enumerate(sample_result.fetchall(), 1):
                        key_fields = str(row)[:100] + "..." if len(str(row)) > 100 else str(row)
                        print(f"    Row {i}: {key_fields}")
                        
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_schemas()) 