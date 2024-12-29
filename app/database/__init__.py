from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager
from app.config import Config
from typing import AsyncGenerator

Base = declarative_base()

def init_models():
    """Initialize all models in the correct order to handle dependencies."""
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

engine = create_async_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    echo=Config.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
