"""
Square Catalog Export Service
A microservice for exporting Square catalog data to the database
"""
import os
import asyncio
import aiohttp
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text, Column, Integer, String, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
Base = declarative_base()

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
    location_data = Column(JSONB)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    export_date = Column(DateTime)

def get_database_url():
    """Get database URL from environment variables"""
    # For Cloud Run
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    if all([db_user, db_password, db_name, cloud_sql_connection_name]):
        return f"postgresql://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
    
    # For local development
    return "postgresql://postgres:password@localhost:5432/nytex_dashboard"

# Global variables for export status
export_status = {
    'running': False,
    'last_export': None,
    'total_items': 0,
    'error': None
}

class SquareCatalogExporter:
    """Handles Square catalog export operations"""
    
    def __init__(self):
        self.square_access_token = os.environ.get('SQUARE_ACCESS_TOKEN')
        self.square_environment = os.environ.get('SQUARE_ENVIRONMENT', 'sandbox')
        
        if self.square_environment.lower() == 'production':
            self.base_url = "https://connect.squareup.com"
        else:
            self.base_url = "https://connect.squareupsandbox.com"
    
    async def export_catalog_data(self):
        """Export catalog data from Square API to database"""
        global export_status
        
        try:
            export_status['running'] = True
            export_status['error'] = None
            
            logger.info("Starting Square catalog export...")
            
            if not self.square_access_token:
                raise Exception("Square access token not configured")
            
            # Get database connection
            database_url = get_database_url()
            engine = create_engine(database_url)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Clear existing data
            logger.info("Clearing existing catalog data...")
            session.execute(text("DELETE FROM square_item_library_export"))
            session.commit()
            
            # Fetch catalog data from Square
            all_items = []
            cursor = None
            page = 1
            
            async with aiohttp.ClientSession() as client_session:
                while True:
                    url = f"{self.base_url}/v2/catalog/search"
                    headers = {
                        'Authorization': f'Bearer {self.square_access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    body = {
                        "object_types": ["ITEM"],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    logger.info(f"Fetching catalog page {page}...")
                    
                    async with client_session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('objects', [])
                            all_items.extend(items)
                            
                            logger.info(f"Retrieved {len(items)} items on page {page} (total: {len(all_items)})")
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                            page += 1
                        else:
                            error_text = await response.text()
                            raise Exception(f"Square API error: {response.status} - {error_text}")
            
            # Process and save items
            logger.info(f"Processing {len(all_items)} catalog items...")
            
            for item in all_items:
                # Extract item data
                item_data = item.get('item_data', {})
                variations = item_data.get('variations', [])
                
                for variation in variations:
                    variation_data = variation.get('item_variation_data', {})
                    
                    # Create export record
                    export_record = SquareItemLibraryExport(
                        reference_handle=item.get('id'),
                        token=variation.get('id'),
                        item_name=item_data.get('name', ''),
                        variation_name=variation_data.get('name', ''),
                        sku=variation_data.get('sku', ''),
                        description=item_data.get('description', ''),
                        categories=','.join([cat.get('name', '') for cat in item_data.get('categories', [])]),
                        price=float(variation_data.get('price_money', {}).get('amount', 0)) / 100 if variation_data.get('price_money') else None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        export_date=datetime.utcnow(),
                        location_data={}  # Can be expanded later
                    )
                    
                    session.add(export_record)
            
            session.commit()
            session.close()
            
            export_status['running'] = False
            export_status['last_export'] = datetime.utcnow().isoformat()
            export_status['total_items'] = len(all_items)
            
            logger.info(f"Catalog export completed successfully: {len(all_items)} items")
            
            return {
                'success': True,
                'items_exported': len(all_items),
                'export_time': export_status['last_export']
            }
            
        except Exception as e:
            export_status['running'] = False
            export_status['error'] = str(e)
            logger.error(f"Catalog export failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e)
            }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'square-catalog-export'})

@app.route('/status', methods=['GET'])
def get_status():
    """Get current export status"""
    return jsonify({
        'running': export_status['running'],
        'last_export': export_status['last_export'],
        'total_items': export_status['total_items'],
        'error': export_status['error']
    })

@app.route('/export', methods=['POST'])
def start_export():
    """Start catalog export"""
    if export_status['running']:
        return jsonify({
            'success': False,
            'message': 'Export already in progress'
        }), 400
    
    try:
        # Run export in background
        exporter = SquareCatalogExporter()
        
        # For simplicity, we'll run this synchronously
        # In production, you might want to use a task queue
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(exporter.export_catalog_data())
        loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'status': 'completed',
                'message': f"Export completed successfully: {result['items_exported']} items",
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Export failed: {result['error']}",
                'data': result
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting export: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to start export: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False) 