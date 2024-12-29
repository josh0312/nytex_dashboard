from sqlalchemy import Column, Integer, String, DateTime, Float
from app.database import Base

class SquareSale(Base):
    __tablename__ = 'square_sales'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, unique=True, nullable=False)
    location_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False)
    payment_id = Column(String)
    item_count = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f'<SquareSale {self.order_id}>' 