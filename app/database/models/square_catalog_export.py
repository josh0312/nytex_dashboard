from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class SquareItemLibraryExport(Base):
    """Model for Square catalog export data - matches Square's official export format"""
    __tablename__ = 'square_item_library_export'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core item fields
    reference_handle = Column(String(255))
    token = Column(String(255))
    item_name = Column(String(500))
    variation_name = Column(String(255))
    sku = Column(String(255))
    description = Column(Text)
    categories = Column(String(255))
    reporting_category = Column(String(255))
    seo_title = Column(String(255))
    seo_description = Column(Text)
    permalink = Column(String(255))
    gtin = Column(String(255))
    square_online_item_visibility = Column(String(255))
    item_type = Column(String(255))
    weight_lb = Column(String(255))
    social_media_link_title = Column(String(255))
    social_media_link_description = Column(Text)
    shipping_enabled = Column(String(255))
    self_serve_ordering_enabled = Column(String(255))
    delivery_enabled = Column(String(255))
    pickup_enabled = Column(String(255))
    price = Column(Numeric(10, 2))
    online_sale_price = Column(Numeric(10, 2))
    archived = Column(String(255))
    sellable = Column(String(255))
    contains_alcohol = Column(String(255))
    stockable = Column(String(255))
    skip_detail_screen_in_pos = Column(String(255))
    option_name_1 = Column(String(255))
    option_value_1 = Column(String(255))
    default_unit_cost = Column(Numeric(10, 2))
    default_vendor_name = Column(String(255))
    default_vendor_code = Column(String(255))
    
    # Location-specific fields - Aubrey
    enabled_aubrey = Column(String(255))
    current_quantity_aubrey = Column(String(255))
    new_quantity_aubrey = Column(String(255))
    stock_alert_enabled_aubrey = Column(String(255))
    stock_alert_count_aubrey = Column(String(255))
    price_aubrey = Column(String(255))
    
    # Location-specific fields - Bridgefarmer
    enabled_bridgefarmer = Column(String(255))
    current_quantity_bridgefarmer = Column(String(255))
    new_quantity_bridgefarmer = Column(String(255))
    stock_alert_enabled_bridgefarmer = Column(String(255))
    stock_alert_count_bridgefarmer = Column(String(255))
    price_bridgefarmer = Column(String(255))
    
    # Location-specific fields - Building
    enabled_building = Column(String(255))
    current_quantity_building = Column(String(255))
    new_quantity_building = Column(String(255))
    stock_alert_enabled_building = Column(String(255))
    stock_alert_count_building = Column(String(255))
    price_building = Column(String(255))
    
    # Location-specific fields - FloMo
    enabled_flomo = Column(String(255))
    current_quantity_flomo = Column(String(255))
    new_quantity_flomo = Column(String(255))
    stock_alert_enabled_flomo = Column(String(255))
    stock_alert_count_flomo = Column(String(255))
    price_flomo = Column(String(255))
    
    # Location-specific fields - Justin
    enabled_justin = Column(String(255))
    current_quantity_justin = Column(String(255))
    new_quantity_justin = Column(String(255))
    stock_alert_enabled_justin = Column(String(255))
    stock_alert_count_justin = Column(String(255))
    price_justin = Column(String(255))
    
    # Location-specific fields - Quinlan
    enabled_quinlan = Column(String(255))
    current_quantity_quinlan = Column(String(255))
    new_quantity_quinlan = Column(String(255))
    stock_alert_enabled_quinlan = Column(String(255))
    stock_alert_count_quinlan = Column(String(255))
    price_quinlan = Column(String(255))
    
    # Location-specific fields - Terrell
    enabled_terrell = Column(String(255))
    current_quantity_terrell = Column(String(255))
    new_quantity_terrell = Column(String(255))
    stock_alert_enabled_terrell = Column(String(255))
    stock_alert_count_terrell = Column(String(255))
    price_terrell = Column(String(255))
    
    # Tax field
    tax_sales_tax = Column(String(255))
    
    # Metadata fields
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    export_date = Column(DateTime)
    
    def __repr__(self):
        return f"<SquareItemLibraryExport(id={self.id}, item_name='{self.item_name}', sku='{self.sku}')>" 