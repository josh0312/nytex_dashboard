from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
import pytz
from app.database import Base
from datetime import datetime, timezone

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

class Tender(Base):
    __tablename__ = "tenders"

    id = Column(String, primary_key=True, index=True)
    location_id = Column(String, ForeignKey("locations.id"), index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    created_at = Column(TimestampTZ, index=True)
    note = Column(String)
    amount_money = Column(JSON)  # {amount: int, currency: str}
    tip_money = Column(JSON)
    processing_fee_money = Column(JSON)
    customer_id = Column(String, index=True)
    type = Column(String)
    card_details = Column(JSON)
    cash_details = Column(JSON)
    additional_recipients = Column(JSON)
    payment_id = Column(String, index=True)

    # Use string references for relationships
    order = relationship("Order", back_populates="tenders", lazy="joined")
    location = relationship("Location", back_populates="tenders", lazy="joined")

    def __repr__(self):
        return f"<Tender {self.id}>" 