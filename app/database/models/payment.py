from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base
from .order import TimestampTZ

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(TimestampTZ)
    updated_at = Column(TimestampTZ)
    amount_money = Column(JSON)
    total_money = Column(JSON)
    tip_money = Column(JSON)
    app_fee_money = Column(JSON)
    approved_money = Column(JSON)
    processing_fee = Column(JSON)
    refunded_money = Column(JSON)
    status = Column(String)
    delay_duration = Column(String)
    delay_action = Column(String)
    delayed_until = Column(TimestampTZ)
    source_type = Column(String)
    card_details = Column(JSON)
    cash_details = Column(JSON)
    external_details = Column(JSON)
    location_id = Column(String, ForeignKey("locations.id"), index=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    reference_id = Column(String)
    risk_evaluation = Column(JSON)
    buyer_email_address = Column(String)
    billing_address = Column(JSON)
    shipping_address = Column(JSON)
    note = Column(String)
    statement_description_identifier = Column(String)
    capabilities = Column(JSON)
    receipt_number = Column(String)
    receipt_url = Column(String)
    device_details = Column(JSON)
    application_details = Column(JSON)
    version_token = Column(String)
    refund_ids = Column(JSON)

    # Relationships
    location = relationship("Location", back_populates="payments")
    order = relationship("Order", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id}>" 