from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
from datetime import datetime
from app.database.models.location import Location

class CatalogCategory(Base):
    __tablename__ = "catalog_categories"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(String)
    version = Column(BigInteger)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = relationship("CatalogItem", back_populates="category")

class CatalogItem(Base):
    __tablename__ = "catalog_items"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(String)
    description_html = Column(String)
    description_plaintext = Column(String)
    category_id = Column(String, ForeignKey("catalog_categories.id"))
    reporting_category_id = Column(String)
    product_type = Column(String)
    is_taxable = Column(Boolean, default=True)
    tax_ids = Column(JSONB, default=list)
    is_archived = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    ecom_visibility = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(BigInteger)
    present_at_all_locations = Column(Boolean, default=False)
    present_at_location_ids = Column(JSONB, default=list)
    
    category = relationship("CatalogCategory", back_populates="items")
    variations = relationship("CatalogVariation", back_populates="item")
    location_availability = relationship("CatalogLocationAvailability", back_populates="item")

class CatalogVariation(Base):
    __tablename__ = "catalog_variations"
    
    id = Column(String, primary_key=True)
    item_id = Column(String, ForeignKey("catalog_items.id"))
    name = Column(String)
    sku = Column(String)
    ordinal = Column(Integer)
    pricing_type = Column(String)
    price_money = Column(JSONB)
    sellable = Column(Boolean, default=True)
    stockable = Column(Boolean, default=True)
    track_inventory = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(BigInteger)
    present_at_all_locations = Column(Boolean, default=False)
    present_at_location_ids = Column(JSONB, default=list)
    
    item = relationship("CatalogItem", back_populates="variations")
    vendor_info = relationship("CatalogVendorInfo", back_populates="variation")
    inventory = relationship("CatalogInventory", back_populates="variation")

class CatalogVendorInfo(Base):
    __tablename__ = "catalog_vendor_info"
    
    id = Column(String, primary_key=True)
    variation_id = Column(String, ForeignKey("catalog_variations.id"))
    vendor_id = Column(String)
    ordinal = Column(Integer)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(BigInteger)
    present_at_all_locations = Column(Boolean, default=False)
    present_at_location_ids = Column(JSONB, default=list)
    
    variation = relationship("CatalogVariation", back_populates="vendor_info")

class CatalogLocationAvailability(Base):
    __tablename__ = "catalog_location_availability"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, ForeignKey("catalog_items.id"))
    location_id = Column(String, ForeignKey("locations.id"))
    sold_out = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    item = relationship("CatalogItem", back_populates="location_availability")
    location = relationship("Location", back_populates="catalog_availability") 

class CatalogInventory(Base):
    __tablename__ = "catalog_inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    variation_id = Column(String, ForeignKey("catalog_variations.id"))
    location_id = Column(String, ForeignKey("locations.id"))
    quantity = Column(Integer)
    calculated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    variation = relationship("CatalogVariation", back_populates="inventory")
    location = relationship("Location", back_populates="catalog_inventory") 