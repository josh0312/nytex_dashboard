"""
Transaction model for Square transaction data
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from app.database import Base

class Transaction(Base):
    """Transaction model for Square transaction information"""
    __tablename__ = 'transactions'
    
    id = Column(String, primary_key=True, index=True)
    location_id = Column(String, ForeignKey('locations.id'))
    created_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Transaction(id='{self.id}', location_id='{self.location_id}')>" 