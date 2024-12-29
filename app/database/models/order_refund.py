from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class OrderRefund(Base):
    __tablename__ = "order_refunds"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    status = Column(String)
    amount_money = Column(JSON)
    processing_fee = Column(JSON)
    payment_id = Column(String, index=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    reason = Column(String)
    refund_metadata = Column(JSON)

    # Relationships
    order = relationship("Order", back_populates="refunds")

    def __repr__(self):
        return f"<OrderRefund {self.id}>" 