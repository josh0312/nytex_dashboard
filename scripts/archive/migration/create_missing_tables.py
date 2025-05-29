"""
Manually create missing vendors and transactions tables in production
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def create_missing_tables():
    """Create vendors and transactions tables in production"""
    try:
        # Production database connection
        prod_url = "postgresql+asyncpg://nytex_user:NytexSecure2024!@34.67.201.62:5432/nytex_dashboard"
        
        print("🔄 Creating missing tables in production...")
        print("=" * 50)
        
        engine = create_async_engine(prod_url, echo=False, connect_args={"ssl": "require"})
        
        async with engine.begin() as conn:
            # Create vendors table
            print("📋 Creating vendors table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vendors (
                    id VARCHAR NOT NULL,
                    name VARCHAR,
                    account_number VARCHAR,
                    note VARCHAR,
                    status VARCHAR,
                    version VARCHAR,
                    address TEXT,
                    contacts TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE,
                    updated_at TIMESTAMP WITHOUT TIME ZONE,
                    synced_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    CONSTRAINT vendors_pkey PRIMARY KEY (id)
                )
            """))
            
            # Create transactions table
            print("📋 Creating transactions table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id VARCHAR NOT NULL,
                    location_id VARCHAR,
                    created_at TIMESTAMP WITHOUT TIME ZONE,
                    CONSTRAINT transactions_pkey PRIMARY KEY (id),
                    CONSTRAINT transactions_location_id_fkey FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """))
            
            # Create indexes
            print("📋 Creating indexes...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_transactions_id ON transactions (id)
            """))
            
            print("✅ Tables created successfully!")
            
            # Verify tables exist
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('vendors', 'transactions')
                ORDER BY table_name
            """))
            
            created_tables = [row[0] for row in result.fetchall()]
            
            print(f"\n📊 Created tables: {created_tables}")
            
            # Get total table count
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            
            total_tables = result.scalar()
            print(f"📊 Production now has {total_tables} tables total")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

async def main():
    """Main function"""
    print("🔄 Creating Missing Production Tables")
    print("=" * 60)
    
    success = await create_missing_tables()
    
    if success:
        print("\n✅ Missing tables created successfully!")
        print("   Production database should now match local schema.")
    else:
        print("\n❌ Failed to create tables. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main()) 