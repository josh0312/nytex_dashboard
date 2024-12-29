from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import asynccontextmanager
from app.config import Config
from app.logger import logger

# Create base model class
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

# Create async engine and session factory
logger.info(f"Creating database engine with URL: {Config.SQLALCHEMY_DATABASE_URI}")
engine = create_async_engine(Config.SQLALCHEMY_DATABASE_URI)
async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    """Async context manager for database sessions"""
    logger.debug("Opening database session")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Closed database session")
