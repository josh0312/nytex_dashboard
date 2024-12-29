from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
from datetime import datetime

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    address = Column(JSONB)
    timezone = Column(String)
    capabilities = Column(JSONB, default=list)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(String)
    coordinates = Column(JSONB)
    business_hours = Column(JSONB)
    business_email = Column(String)
    phone_number = Column(String)
    website_url = Column(String)
    
    orders = relationship("Order", back_populates="location")
    tenders = relationship("Tender", back_populates="location")
    payments = relationship("Payment", back_populates="location")
    sales = relationship("SquareSale", back_populates="location")
    catalog_availability = relationship("CatalogLocationAvailability", back_populates="location")
    catalog_inventory = relationship("CatalogInventory", back_populates="location") 