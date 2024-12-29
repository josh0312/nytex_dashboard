from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class OrderFulfillment(Base):
    __tablename__ = "order_fulfillments"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    status = Column(String)
    type = Column(String)
    state = Column(String)
    line_item_application = Column(String)
    fulfillment_metadata = Column(JSON)
    pickup_details = Column(JSON)
    shipment_details = Column(JSON)
    delivery_details = Column(JSON)

    # Use string reference for relationship
    order = relationship("Order", back_populates="fulfillments", lazy="joined")

    def __repr__(self):
        return f"<OrderFulfillment {self.id}>" 