from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
import pytz

from .base import Base
from .order import TimestampTZ

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

    # Relationships
    order = relationship("Order", back_populates="tenders")
    location = relationship("Location", back_populates="tenders")

    def __repr__(self):
        return f"<Tender {self.id}>" 