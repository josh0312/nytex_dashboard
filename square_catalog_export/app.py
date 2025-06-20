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

# Configure logging first (before any other code that might use it)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secret Manager integration for production
try:
    from google.cloud import secretmanager
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
    
    def load_secrets_from_gcp():
        """Load secrets from Google Secret Manager in production"""
        if not GOOGLE_CLOUD_PROJECT or os.environ.get('ENVIRONMENT') != 'production':
            return
        
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_path = f"projects/{GOOGLE_CLOUD_PROJECT}"
            
            # Secret mappings (same as main application)
            secret_mappings = {
                "SQUARE_ACCESS_TOKEN": "square-access-token",
                "SQUARE_ENVIRONMENT": "square-environment", 
                "SQLALCHEMY_DATABASE_URI": "database-uri"
            }
            
            for env_key, secret_id in secret_mappings.items():
                if env_key not in os.environ:  # Only load if not already set
                    try:
                        name = f"{project_path}/secrets/{secret_id}/versions/latest"
                        response = client.access_secret_version(request={"name": name})
                        secret_value = response.payload.data.decode("UTF-8")
                        os.environ[env_key] = secret_value
                        logger.info(f"✅ Loaded secret: {env_key}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load secret {env_key}: {e}")
                        
        except Exception as e:
            logger.warning(f"⚠️ Secret Manager not available: {e}")
    
    # Load secrets on startup in production
    load_secrets_from_gcp()
    
except ImportError:
    logger.info("📝 Google Cloud Secret Manager not available (development mode)")

app = Flask(__name__)

# Database configuration
Base = declarative_base()

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

def get_database_url():
    """Get database URL from environment variables"""
    # Check for SQLALCHEMY_DATABASE_URI first (matches main app)
    db_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
    if db_url:
        # Convert asyncpg to regular postgresql for SQLAlchemy sync operations
        if 'postgresql+asyncpg://' in db_url:
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        # Handle Docker networking - only replace localhost with host.docker.internal if running in Docker
        # Check if we're running in Docker by looking for /.dockerenv file
        import os.path as path
        if path.exists('/.dockerenv') and 'localhost:' in db_url:
            db_url = db_url.replace('localhost:', 'host.docker.internal:')
        
        return db_url
    
    # For Cloud Run
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    if all([db_user, db_password, db_name, cloud_sql_connection_name]):
        return f"postgresql://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
    
    # For local development fallback
    return "postgresql://postgres:password@host.docker.internal:5432/nytex_dashboard"

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
        """Export catalog data from Square API to database with complete field mapping"""
        global export_status
        
        try:
            export_status['running'] = True
            export_status['error'] = None
            
            logger.info("Starting comprehensive Square catalog export...")
            
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
            
            # Get location mapping for inventory data
            location_mapping = {}
            locations_result = session.execute(text("""
                SELECT id, name FROM locations WHERE status = 'ACTIVE' ORDER BY name
            """))
            for row in locations_result:
                location_mapping[row[0]] = row[1].lower()
            
            logger.info(f"Found {len(location_mapping)} active locations: {list(location_mapping.values())}")
            
            # Fetch catalog data from Square
            all_items = []
            cursor = None
            page = 1
            
            async with aiohttp.ClientSession() as client_session:
                while True:
                    # Use SearchCatalogItems to properly filter archived items
                    url = f"{self.base_url}/v2/catalog/search-catalog-items"
                    headers = {
                        'Authorization': f'Bearer {self.square_access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    body = {
                        "limit": 100,  # Maximum allowed for SearchCatalogItems
                        "archived_state": "ARCHIVED_STATE_NOT_ARCHIVED",  # Exclude archived items
                        "include_related_objects": True  # Include variations and other related objects
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    logger.info(f"Fetching catalog page {page}...")
                    
                    async with client_session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('items', [])  # SearchCatalogItems returns 'items' not 'objects'
                            all_items.extend(items)
                            
                            # Also collect related objects (categories, etc.)
                            related_objects = data.get('related_objects', [])
                            all_items.extend(related_objects)
                            
                            logger.info(f"Retrieved {len(items)} items on page {page} (total: {len(all_items)})")
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                            page += 1
                        else:
                            error_text = await response.text()
                            raise Exception(f"Square API error: {response.status} - {error_text}")
            
            # Build a lookup for categories and other related objects
            categories_lookup = {}
            for obj in all_items:
                if obj.get('type') == 'CATEGORY':
                    categories_lookup[obj.get('id')] = obj.get('category_data', {}).get('name', '')
            
            logger.info(f"Found {len(categories_lookup)} categories in Square API response")
            
            # Debug: Log first few categories to see what we have
            category_sample = list(categories_lookup.items())[:5]
            logger.info(f"Sample categories: {category_sample}")
            
            # Process and save items with complete field mapping
            logger.info(f"Processing catalog items with full field mapping...")
            
            processed_count = 0
            for item in all_items:
                # Only process ITEM objects, skip related objects
                if item.get('type') != 'ITEM':
                    continue
                    
                # Extract item data
                item_data = item.get('item_data', {})
                variations = item_data.get('variations', [])
                
                # Get item-level fields
                item_name = item_data.get('name', '')
                description = item_data.get('description', '')
                
                # Debug: Log the full item_data structure for first few items
                if processed_count < 3:
                    logger.info(f"Full item_data for '{item_name}': {item_data}")
                
                # Extract categories from Square API
                # The categories are in item_data.categories as objects with 'id' and 'ordinal'
                categories_list = item_data.get('categories', [])
                category_names = []
                category_ids = []
                
                for cat_obj in categories_list:
                    cat_id = cat_obj.get('id')
                    if cat_id:
                        category_ids.append(cat_id)
                        if cat_id in categories_lookup:
                            category_names.append(categories_lookup[cat_id])
                
                categories_from_api = ','.join(category_names)
                
                # Debug logging for first few items
                if processed_count < 5:
                    logger.info(f"Item '{item_name}': categories_list={categories_list}, category_ids={category_ids}, categories_from_api='{categories_from_api}'")
                
                # Extract ecom data
                ecom_data = item_data.get('ecom_seo_data', {})
                seo_title = ecom_data.get('seo_title', '')
                seo_description = ecom_data.get('seo_description', '')
                permalink = ecom_data.get('permalink', '')
                
                # Extract item options
                item_options = item_data.get('item_options', [])
                option_name_1 = item_options[0].get('name', '') if item_options else ''
                
                for variation in variations:
                    variation_data = variation.get('item_variation_data', {})
                    variation_id = variation.get('id', '')
                    
                    # Extract vendor information from Square API
                    vendor_infos = variation_data.get('item_variation_vendor_infos', [])
                    api_vendor_code = ''
                    if vendor_infos:
                        # Get the first vendor info's SKU as the vendor code
                        vendor_info_data = vendor_infos[0].get('item_variation_vendor_info_data', {})
                        api_vendor_code = vendor_info_data.get('sku', '')
                    
                    # Get inventory data for this variation across all locations
                    inventory_data = {}
                    inventory_result = session.execute(text("""
                        SELECT l.name, ci.quantity 
                        FROM catalog_inventory ci
                        JOIN locations l ON ci.location_id = l.id
                        WHERE ci.variation_id = :variation_id AND l.status = 'ACTIVE'
                    """), {'variation_id': variation_id})
                    
                    for inv_row in inventory_result:
                        location_name = inv_row[0].lower()
                        quantity = inv_row[1] or 0
                        inventory_data[location_name] = str(quantity)
                    
                    # Get variation-level data from our production tables
                    variation_result = session.execute(text("""
                        SELECT cv.sellable, cv.stockable, cv.track_inventory,
                               cv.units_per_case, cv.default_unit_cost
                        FROM catalog_variations cv
                        WHERE cv.id = :variation_id
                    """), {'variation_id': variation_id})
                    
                    variation_row = variation_result.fetchone()
                    if variation_row:
                        sellable = 'Y' if variation_row[0] else 'N'
                        stockable = 'Y' if variation_row[1] else 'N'
                        track_inventory = variation_row[2]
                        units_per_case = variation_row[3]
                        
                        # Extract and convert default_unit_cost from JSONB
                        default_unit_cost_json = variation_row[4]
                        default_unit_cost = None
                        if default_unit_cost_json and isinstance(default_unit_cost_json, dict):
                            amount = default_unit_cost_json.get('amount')
                            if amount is not None:
                                # Convert from cents to dollars
                                default_unit_cost = float(amount) / 100
                    else:
                        sellable = 'Y'
                        stockable = 'Y'
                        track_inventory = True
                        units_per_case = None
                        default_unit_cost = None
                    
                    # Get location availability for this item from catalog_location_availability
                    item_id = item.get('id', '')
                    location_availability = {}
                    
                    availability_result = session.execute(text("""
                        SELECT l.name, cla.sold_out
                        FROM catalog_location_availability cla
                        JOIN locations l ON cla.location_id = l.id
                        WHERE cla.item_id = :item_id AND l.status = 'ACTIVE'
                    """), {'item_id': item_id})
                    
                    for avail_row in availability_result:
                        location_name = avail_row[0].lower()
                        is_sold_out = avail_row[1]
                        # Available = not sold out, so enabled = 'Y' if not sold out
                        location_availability[location_name] = 'N' if is_sold_out else 'Y'
                    
                    logger.debug(f"Location availability for {item_name}: {location_availability}")
                    
                    # Get item-level data from our production tables including categories
                    item_result = session.execute(text("""
                        SELECT ci.is_archived, ci.ecom_visibility, ci.is_taxable,
                               cc.name as category_name, rc.name as reporting_category_name
                        FROM catalog_items ci
                        LEFT JOIN catalog_categories cc ON ci.category_id = cc.id
                        LEFT JOIN catalog_categories rc ON ci.reporting_category_id = rc.id
                        WHERE ci.id = :item_id
                    """), {'item_id': item.get('id', '')})
                    
                    item_row = item_result.fetchone()
                    if item_row:
                        archived = 'Y' if item_row[0] else 'N'
                        ecom_visibility = item_row[1] or 'UNINDEXED'
                        is_taxable = item_row[2]
                        category_name = item_row[3] or ''
                        reporting_category_name = item_row[4] or ''
                    else:
                        archived = 'N'
                        ecom_visibility = 'UNINDEXED'
                        is_taxable = True
                        category_name = ''
                        reporting_category_name = ''
                    
                    # Get vendor information for this variation
                    vendor_result = session.execute(text("""
                        SELECT v.name as vendor_name, v.account_number as vendor_code
                        FROM catalog_vendor_info cvi
                        JOIN vendors v ON cvi.vendor_id = v.id
                        WHERE cvi.variation_id = :variation_id AND cvi.is_deleted = false
                        ORDER BY cvi.ordinal
                        LIMIT 1
                    """), {'variation_id': variation_id})
                    
                    vendor_row = vendor_result.fetchone()
                    if vendor_row:
                        default_vendor_name = vendor_row[0] or ''
                        default_vendor_code = vendor_row[1] or api_vendor_code  # Use API vendor code if DB is empty
                    else:
                        default_vendor_name = ''
                        default_vendor_code = api_vendor_code  # Use API vendor code as fallback
                    
                    # Extract price information
                    price_money = variation_data.get('price_money', {})
                    price = float(price_money.get('amount', 0)) / 100 if price_money else None
                    
                    # Extract option values
                    option_values = variation_data.get('item_option_values', [])
                    option_value_1 = option_values[0].get('option_value', '') if option_values else ''
                    
                    # Create export record with all fields
                    export_record = SquareItemLibraryExport(
                        # Core fields
                        reference_handle=item.get('id'),
                        token=variation.get('id'),
                        item_name=item_name,
                        variation_name=variation_data.get('name', ''),
                        sku=variation_data.get('sku', ''),
                        description=description,
                        categories=categories_from_api,  # Use categories from Square API
                        reporting_category=categories_from_api,  # Same as categories - should always match
                        seo_title=seo_title,
                        seo_description=seo_description,
                        permalink=permalink,
                        gtin='',  # Not available in API
                        square_online_item_visibility=ecom_visibility,
                        item_type='REGULAR',  # Default
                        weight_lb='',  # Not available in API
                        social_media_link_title='',  # Not available in API
                        social_media_link_description='',  # Not available in API
                        shipping_enabled='N',  # Square uses N, not TRUE
                        self_serve_ordering_enabled='N',  # Square uses N, not TRUE
                        delivery_enabled='N',  # Square uses N, not TRUE
                        pickup_enabled='Y',  # Most items support pickup
                        price=price,
                        online_sale_price=price,  # Same as regular price
                        archived=archived,  # Already in Y/N format
                        sellable=sellable,  # Already in Y/N format
                        contains_alcohol='N',  # Square uses N, not FALSE
                        stockable=stockable,  # Already in Y/N format
                        skip_detail_screen_in_pos='N',  # Square uses N, not FALSE
                        option_name_1=option_name_1,
                        option_value_1=option_value_1,
                        default_unit_cost=default_unit_cost,
                        default_vendor_name=default_vendor_name,
                        default_vendor_code=default_vendor_code,
                        
                        # Location-specific fields - Use actual location availability data
                        enabled_aubrey=location_availability.get('aubrey', 'N'),
                        current_quantity_aubrey=inventory_data.get('aubrey', '0'),
                        new_quantity_aubrey='',  # Leave blank for manual entry
                        stock_alert_enabled_aubrey='N',  # Square uses N, not FALSE
                        stock_alert_count_aubrey='0',
                        price_aubrey=str(price) if price else '',
                        
                        enabled_bridgefarmer=location_availability.get('bridgefarmer', 'N'),
                        current_quantity_bridgefarmer=inventory_data.get('bridgefarmer', '0'),
                        new_quantity_bridgefarmer='',  # Leave blank for manual entry
                        stock_alert_enabled_bridgefarmer='N',  # Square uses N, not FALSE
                        stock_alert_count_bridgefarmer='0',
                        price_bridgefarmer=str(price) if price else '',
                        
                        enabled_building=location_availability.get('building', 'N'),
                        current_quantity_building=inventory_data.get('building', '0'),
                        new_quantity_building='',  # Leave blank for manual entry
                        stock_alert_enabled_building='N',  # Square uses N, not FALSE
                        stock_alert_count_building='0',
                        price_building=str(price) if price else '',
                        
                        enabled_flomo=location_availability.get('flomo', 'N'),
                        current_quantity_flomo=inventory_data.get('flomo', '0'),
                        new_quantity_flomo='',  # Leave blank for manual entry
                        stock_alert_enabled_flomo='N',  # Square uses N, not FALSE
                        stock_alert_count_flomo='0',
                        price_flomo=str(price) if price else '',
                        
                        enabled_justin=location_availability.get('justin', 'N'),
                        current_quantity_justin=inventory_data.get('justin', '0'),
                        new_quantity_justin='',  # Leave blank for manual entry
                        stock_alert_enabled_justin='N',  # Square uses N, not FALSE
                        stock_alert_count_justin='0',
                        price_justin=str(price) if price else '',
                        
                        enabled_quinlan=location_availability.get('quinlan', 'N'),
                        current_quantity_quinlan=inventory_data.get('quinlan', '0'),
                        new_quantity_quinlan='',  # Leave blank for manual entry
                        stock_alert_enabled_quinlan='N',  # Square uses N, not FALSE
                        stock_alert_count_quinlan='0',
                        price_quinlan=str(price) if price else '',
                        
                        enabled_terrell=location_availability.get('terrell', 'N'),
                        current_quantity_terrell=inventory_data.get('terrell', '0'),
                        new_quantity_terrell='',  # Leave blank for manual entry
                        stock_alert_enabled_terrell='N',  # Square uses N, not FALSE
                        stock_alert_count_terrell='0',
                        price_terrell=str(price) if price else '',
                        
                        # Tax field
                        tax_sales_tax='Sales Tax (8.25%)' if is_taxable else '',
                        
                        # Metadata
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        export_date=datetime.utcnow()
                    )
                    
                    session.add(export_record)
                    processed_count += 1
                    
                    # Commit in batches for performance
                    if processed_count % 100 == 0:
                        session.commit()
                        logger.info(f"Processed {processed_count} variations...")
            
            session.commit()
            session.close()
            
            export_status['running'] = False
            export_status['last_export'] = datetime.utcnow().isoformat()
            export_status['total_items'] = processed_count
            
            logger.info(f"Comprehensive catalog export completed successfully: {processed_count} variations processed")
            
            return {
                'success': True,
                'items_exported': processed_count,
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

@app.route('/', methods=['GET'])
def service_info():
    """Root endpoint with service information and available endpoints"""
    return jsonify({
        'service': 'square-catalog-export',
        'version': '1.0.0',
        'status': 'running',
        'description': 'Square Catalog Export Service - Exports Square catalog data to database',
        'endpoints': {
            '/': 'Service information (this endpoint)',
            '/health': 'Health check',
            '/status': 'Export status',
            '/export': 'Start catalog export (POST)',
            '/query/categories': 'Check category data',
            '/query/category-comparison': 'Compare category fields',
            '/query/vendors': 'Check vendor data'
        },
        'usage': {
            'health_check': 'GET /',
            'start_export': 'POST /export',
            'check_status': 'GET /status'
        }
    })

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

@app.route('/query/categories', methods=['GET'])
def check_categories():
    """Check if categories are populated in the export data"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check categories
        result = session.execute(text("""
            SELECT 
                categories,
                COUNT(*) as count
            FROM square_item_library_export 
            WHERE categories IS NOT NULL AND categories != '' 
            GROUP BY categories 
            ORDER BY count DESC 
            LIMIT 10
        """))
        
        categories_data = []
        for row in result:
            categories_data.append({
                'category': row[0],
                'count': row[1]
            })
        
        # Also get total counts
        total_result = session.execute(text("""
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN categories IS NOT NULL AND categories != '' THEN 1 END) as items_with_categories,
                COUNT(CASE WHEN categories IS NULL OR categories = '' THEN 1 END) as items_without_categories
            FROM square_item_library_export
        """))
        
        totals = total_result.fetchone()
        
        session.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_items': totals[0],
                'items_with_categories': totals[1],
                'items_without_categories': totals[2],
                'top_categories': categories_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/query/category-comparison', methods=['GET'])
def check_category_comparison():
    """Check if categories and reporting_category columns have the same data"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if categories and reporting_category match
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN categories = reporting_category THEN 1 END) as matching_categories,
                COUNT(CASE WHEN categories != reporting_category THEN 1 END) as different_categories,
                COUNT(CASE WHEN categories IS NULL OR categories = '' THEN 1 END) as empty_categories,
                COUNT(CASE WHEN reporting_category IS NULL OR reporting_category = '' THEN 1 END) as empty_reporting_categories
            FROM square_item_library_export
        """))
        
        row = result.fetchone()
        
        # Get sample of different categories
        diff_result = session.execute(text("""
            SELECT categories, reporting_category, item_name
            FROM square_item_library_export 
            WHERE categories != reporting_category 
            LIMIT 5
        """))
        
        different_samples = []
        for row_diff in diff_result:
            different_samples.append({
                'item_name': row_diff[2],
                'categories': row_diff[0],
                'reporting_category': row_diff[1]
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_items': row[0],
                'matching_categories': row[1],
                'different_categories': row[2],
                'empty_categories': row[3],
                'empty_reporting_categories': row[4],
                'different_samples': different_samples
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking category comparison: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/query/vendors', methods=['GET'])
def check_vendors():
    """Check vendor data in the export"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check vendor data in export
        result = session.execute(text("""
            SELECT 
                default_vendor_name,
                default_vendor_code,
                COUNT(*) as count
            FROM square_item_library_export 
            WHERE default_vendor_name IS NOT NULL AND default_vendor_name != ''
            GROUP BY default_vendor_name, default_vendor_code 
            ORDER BY count DESC 
            LIMIT 10
        """))
        
        vendor_data = []
        for row in result:
            vendor_data.append({
                'vendor_name': row[0],
                'vendor_code': row[1] or 'EMPTY',
                'count': row[2]
            })
        
        # Also check the actual vendors table to see what account_number data exists
        vendors_result = session.execute(text("""
            SELECT 
                name,
                account_number,
                id
            FROM vendors 
            ORDER BY name
            LIMIT 10
        """))
        
        vendors_table_data = []
        for row in vendors_result:
            vendors_table_data.append({
                'name': row[0],
                'account_number': row[1] or 'EMPTY',
                'id': row[2]
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'data': {
                'export_vendor_data': vendor_data,
                'vendors_table_data': vendors_table_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking vendors: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False) 