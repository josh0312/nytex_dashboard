from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

Base = declarative_base(cls=AsyncAttrs)
AsyncBase = Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

__all__ = ['Base', 'AsyncBase']
