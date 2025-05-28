from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class SquareItemLibraryExport(Base):
    """Model for Square catalog export data"""
    __tablename__ = 'square_item_library_export'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_handle = Column(String(255))
    token = Column(String(255))
    item_name = Column(String(500))
    variation_name = Column(String(255))
    sku = Column(String(255))
    description = Column(Text)
    categories = Column(String(255))
    reporting_category = Column(String(255))
    item_type = Column(String(255))
    seo_title = Column(String(255))
    seo_description = Column(Text)
    permalink = Column(String(255))
    square_online_item_visibility = Column(String(255))
    gtin = Column(String(255))
    weight_lb = Column(String(255))
    contains_alcohol = Column(String(255))
    archived = Column(String(255))
    sellable = Column(String(255))
    stockable = Column(String(255))
    skip_detail_screen_in_pos = Column(String(255))
    social_media_link_title = Column(String(255))
    social_media_link_description = Column(Text)
    shipping_enabled = Column(String(255))
    self_serve_ordering_enabled = Column(String(255))
    delivery_enabled = Column(String(255))
    pickup_enabled = Column(String(255))
    price = Column(Numeric(10, 2))
    online_sale_price = Column(Numeric(10, 2))
    option_name_1 = Column(String(255))
    option_value_1 = Column(String(255))
    default_unit_cost = Column(Numeric(10, 2))
    default_vendor_name = Column(String(255))
    default_vendor_code = Column(String(255))
    tax_sales_tax = Column(String(255))
    location_data = Column(JSONB)  # JSONB containing location-specific data
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    export_date = Column(DateTime)
    
    def __repr__(self):
        return f"<SquareItemLibraryExport(id={self.id}, item_name='{self.item_name}', sku='{self.sku}')>" 