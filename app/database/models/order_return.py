from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class OrderReturn(Base):
    __tablename__ = "order_returns"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    source_order_id = Column(String, index=True)
    return_line_items = Column(JSON)  # List of returned items
    return_service_charges = Column(JSON)  # List of returned service charges
    return_taxes = Column(JSON)  # List of returned taxes
    return_discounts = Column(JSON)  # List of returned discounts
    rounding_adjustment = Column(JSON)
    return_amounts = Column(JSON)

    # Relationships
    order = relationship("Order", back_populates="returns")

    def __repr__(self):
        return f"<OrderReturn {self.id}>" 