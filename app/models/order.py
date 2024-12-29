from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, nullable=False)
    order_date = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False) 