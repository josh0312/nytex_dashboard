from sqlalchemy import Column, String, Integer, JSON, ForeignKey, UniqueConstraint, BigInteger
from sqlalchemy.orm import relationship

from .base import Base

class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    __table_args__ = (
        UniqueConstraint('order_id', 'uid', name='uix_order_line_items_order_uid'),
    )

    uid = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    name = Column(String)
    quantity = Column(String)
    note = Column(String)
    catalog_object_id = Column(String, index=True)
    catalog_version = Column(BigInteger)
    variation_name = Column(String)
    item_type = Column(String)
    base_price_money = Column(JSON)
    gross_sales_money = Column(JSON)
    total_tax_money = Column(JSON)
    total_discount_money = Column(JSON)
    total_money = Column(JSON)
    applied_taxes = Column(JSON)
    applied_discounts = Column(JSON)
    modifiers = Column(JSON)
    pricing_blocklists = Column(JSON)

    # Relationships
    order = relationship("Order", back_populates="line_items")

    def __repr__(self):
        return f"<OrderLineItem {self.uid} {self.name}>" 