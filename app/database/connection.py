from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from ..config import Config

# Create async engine with production-friendly settings
database_url = Config.get_database_url()

# Use different settings for SQLite vs PostgreSQL
if database_url.startswith('sqlite'):
    # SQLite doesn't support most pool settings
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True
    )
else:
    # PostgreSQL production settings
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        connect_args={
            "command_timeout": 30,
            "server_settings": {
                "application_name": "nytex_dashboard",
            },
        }
    )

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@asynccontextmanager
async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# FastAPI dependency function
async def get_db_session():
    """FastAPI dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Test helper function
@asynccontextmanager
async def get_async_session():
    """Get async session for testing and other uses"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close() 