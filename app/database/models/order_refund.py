from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class OrderRefund(Base):
    __tablename__ = "order_refunds"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    status = Column(String)
    amount_money = Column(JSON)
    processing_fee = Column(JSON)
    reason = Column(String)
    payment_id = Column(String, index=True)

    # Use string reference for relationship
    order = relationship("Order", back_populates="refunds", lazy="joined")

    def __repr__(self):
        return f"<OrderRefund {self.id}>" 