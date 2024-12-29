from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class OrderReturn(Base):
    __tablename__ = "order_returns"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    source_order_id = Column(String, index=True)
    return_line_items = Column(JSON)
    return_service_charges = Column(JSON)
    return_taxes = Column(JSON)
    return_discounts = Column(JSON)
    rounding_adjustment = Column(JSON)
    return_amounts = Column(JSON)

    # Use string reference for relationship
    order = relationship("Order", back_populates="returns", lazy="joined")

    def __repr__(self):
        return f"<OrderReturn {self.id}>" 