#!/usr/bin/env python3
"""
Add missing columns to order_line_items table to match Square API
"""
import asyncio
import os
from sqlalchemy import text
from app.database import get_session

async def add_missing_columns():
    """Add variation_total_price_money and item_variation_metadata columns"""
    
    async with get_session() as session:
        print("🔧 Adding missing columns to order_line_items table...")
        
        try:
            # Add variation_total_price_money column
            await session.execute(text("""
                ALTER TABLE order_line_items 
                ADD COLUMN IF NOT EXISTS variation_total_price_money JSON;
            """))
            print("✅ Added variation_total_price_money column")
            
            # Add item_variation_metadata column
            await session.execute(text("""
                ALTER TABLE order_line_items 
                ADD COLUMN IF NOT EXISTS item_variation_metadata JSON;
            """))
            print("✅ Added item_variation_metadata column")
            
            await session.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(add_missing_columns()) 