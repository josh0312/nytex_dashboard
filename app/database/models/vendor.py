"""
Vendor model for Square vendor data
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Vendor(Base):
    """Vendor model for Square vendor information"""
    __tablename__ = 'vendors'
    
    id = Column(String, primary_key=True)
    name = Column(String)
    account_number = Column(String)
    note = Column(String)
    status = Column(String)
    version = Column(String)
    address = Column(Text)
    contacts = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    synced_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Vendor(id='{self.id}', name='{self.name}')>" 