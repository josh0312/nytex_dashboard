from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager
from app.config import Config
from typing import AsyncGenerator
import logging

Base = declarative_base()

def init_models():
    """Initialize all models in the correct order to handle dependencies."""
    # Import authentication models first
    from app.database.models.auth import User, Session
    
    # Import base models first (no dependencies)
    from app.database.models.operating_season import OperatingSeason
    from app.database.models.location import Location
    
    # Import order-related models in dependency order
    from app.database.models.order_line_item import OrderLineItem
    from app.database.models.order_fulfillment import OrderFulfillment
    from app.database.models.order_return import OrderReturn
    from app.database.models.order_refund import OrderRefund
    from app.database.models.order import Order
    
    # Import payment-related models
    from app.database.models.tender import Tender
    from app.database.models.payment import Payment
    from app.database.models.square_sale import SquareSale
    
    # Import catalog models
    from app.database.models.catalog import (
        CatalogCategory,
        CatalogItem,
        CatalogVariation,
        CatalogVendorInfo,
        CatalogLocationAvailability,
        CatalogInventory
    )
    
    # Import catalog export model
    from app.database.models.square_catalog_export import SquareItemLibraryExport

# Create engine only if database URL is available
engine = None
async_session = None

def get_engine():
    global engine
    if engine is None and Config.SQLALCHEMY_DATABASE_URI:
        try:
            engine = create_async_engine(
                Config.SQLALCHEMY_DATABASE_URI,
                echo=Config.DEBUG,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
        except Exception as e:
            logging.error(f"Failed to create database engine: {e}")
            engine = None
    return engine

def get_async_session():
    global async_session
    if async_session is None:
        engine = get_engine()
        if engine:
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
    return async_session

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_async_session()
    if session_maker is None:
        raise RuntimeError("Database not configured")
    
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
