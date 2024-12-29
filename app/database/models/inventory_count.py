from sqlalchemy import Column, String, DateTime, JSON, UniqueConstraint, Integer
from sqlalchemy.orm import relationship

from .base import Base

class InventoryCount(Base):
    __tablename__ = "inventory_counts"
    __table_args__ = (
        UniqueConstraint('catalog_object_id', 'location_id', name='uix_inventory_counts_object_location'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    catalog_object_id = Column(String, index=True)
    location_id = Column(String, index=True)
    state = Column(String)
    quantity = Column(String)
    calculated_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __repr__(self):
        return f"<InventoryCount {self.catalog_object_id} {self.location_id}>" 