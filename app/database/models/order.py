from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from datetime import datetime, timezone
from app.database import Base

class TimestampTZ(TypeDecorator):
    """Timezone-aware timestamp type."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is not None:
                value = value.astimezone(timezone.utc)
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
        return value

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    location_id = Column(String, ForeignKey("locations.id"), index=True)
    created_at = Column(TimestampTZ, index=True)
    updated_at = Column(TimestampTZ)
    closed_at = Column(TimestampTZ)
    state = Column(String)
    version = Column(Integer)
    total_money = Column(JSON)  # {amount: int, currency: str}
    total_tax_money = Column(JSON)
    total_discount_money = Column(JSON)
    net_amounts = Column(JSON)
    source = Column(JSON)
    return_amounts = Column(JSON)
    order_metadata = Column(JSON)

    # Use string references for relationships
    location = relationship("Location", back_populates="orders", lazy="joined")
    tenders = relationship("Tender", back_populates="order", cascade="all, delete-orphan")
    line_items = relationship("OrderLineItem", back_populates="order", cascade="all, delete-orphan")
    fulfillments = relationship("OrderFulfillment", back_populates="order", cascade="all, delete-orphan")
    returns = relationship("OrderReturn", back_populates="order", cascade="all, delete-orphan")
    refunds = relationship("OrderRefund", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")

    def __repr__(self):
        return f"<Order {self.id}>" 