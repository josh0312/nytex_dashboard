import logging
import os
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.database import get_session
from app.config import Config
from app.templates_config import templates
from app.logger import logger
from sqlalchemy import text
import aiohttp
from sqlalchemy.ext.asyncio import create_async_engine

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/sync")
async def admin_sync_page(request: Request):
    """Admin page for data synchronization"""
    try:
        logger.info("Loading admin sync page")
        return templates.TemplateResponse("admin/sync.html", {
            "request": request,
            "title": "Data Sync Administration"
        })
    except Exception as e:
        logger.error(f"Error loading admin sync page: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/error.html", {
            "request": request,
            "title": "Admin Error",
            "message": "Unable to load admin sync page"
        })

@router.get("/status")
async def admin_status():
    """Get system status for debugging"""
    try:
        status = {
            "database": "disconnected",
            "square_config": "missing",
            "locations": [],
            "tables_exist": False
        }
        
        # Check Square configuration
        if hasattr(Config, 'SQUARE_ACCESS_TOKEN') and Config.SQUARE_ACCESS_TOKEN:
            status["square_config"] = "configured"
        
        # Check database connection and data
        try:
            async with get_session() as session:
                status["database"] = "connected"
                
                # Check if locations table exists and has data
                try:
                    result = await session.execute(text("SELECT COUNT(*) FROM locations"))
                    count = result.scalar()
                    status["tables_exist"] = True
                    status["location_count"] = count
                    
                    # Get location details if any exist
                    if count > 0:
                        result = await session.execute(text("SELECT name, status FROM locations LIMIT 10"))
                        status["locations"] = [{"name": row[0], "status": row[1]} for row in result.fetchall()]
                    
                except Exception as e:
                    status["table_error"] = str(e)
                    
        except Exception as e:
            status["database"] = f"error: {str(e)}"
        
        return JSONResponse(status)
        
    except Exception as e:
        logger.error(f"Error getting admin status: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": str(e),
            "database": "error",
            "square_config": "unknown"
        }, status_code=500)

@router.post("/create-tables")
async def create_tables():
    """Create all database tables"""
    try:
        from app.database import get_engine, Base, init_models
        
        # Initialize models
        init_models()
        
        # Get engine
        engine = get_engine()
        if not engine:
            return JSONResponse({
                "success": False,
                "message": "Database engine not available"
            }, status_code=500)
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        return JSONResponse({
            "success": True,
            "message": "Database tables created successfully"
        })
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Error creating tables: {str(e)}"
        }, status_code=500)

@router.post("/complete-sync")
async def complete_sync(request: Request):
    """Trigger complete production data sync"""
    try:
        logger.info("Starting complete production data sync via API")
        
        # Get configuration
        square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
        square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'production')
        
        if not square_access_token:
            return JSONResponse({
                "success": False,
                "error": "Square access token not configured",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        
        # Determine Square API base URL
        if square_environment.lower() == 'production':
            base_url = "https://connect.squareup.com"
        else:
            base_url = "https://connect.squareupsandbox.com"
        
        # Get database URL for production
        db_url = Config.SQLALCHEMY_DATABASE_URI
        
        logger.info(f"Using Square environment: {square_environment}")
        logger.info(f"Square API base URL: {base_url}")
        
        # Step 1: Sync Locations
        logger.info("Step 1: Syncing locations...")
        locations_success = await sync_locations_direct(square_access_token, base_url, db_url)
        if not locations_success:
            return JSONResponse({
                "success": False,
                "error": "Location sync failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        
        # Step 2: Sync Catalog Data
        logger.info("Step 2: Syncing catalog data...")
        catalog_success = await sync_catalog_direct(square_access_token, base_url, db_url)
        if not catalog_success:
            return JSONResponse({
                "success": False,
                "error": "Catalog sync failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        
        # Step 3: Sync Inventory
        logger.info("Step 3: Syncing inventory...")
        inventory_success = await sync_inventory_direct(square_access_token, base_url, db_url)
        if not inventory_success:
            return JSONResponse({
                "success": False,
                "error": "Inventory sync failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        
        logger.info("Complete production sync successful")
        return JSONResponse({
            "success": True,
            "message": "Complete production sync successful - all data synced in proper order",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error during complete sync: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Complete sync error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

async def sync_locations_direct(access_token, base_url, db_url):
    """Sync locations directly"""
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        engine = create_async_engine(db_url, echo=False)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{base_url}/v2/locations"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    locations = data.get('locations', [])
                    
                    async with engine.begin() as conn:
                        # Clear existing data in correct order (child tables first)
                        await conn.execute(text("DELETE FROM catalog_inventory"))
                        await conn.execute(text("DELETE FROM catalog_variations"))
                        await conn.execute(text("DELETE FROM catalog_items"))
                        await conn.execute(text("DELETE FROM catalog_categories"))
                        await conn.execute(text("DELETE FROM locations"))
                        
                        # Insert locations
                        for location in locations:
                            await conn.execute(text("""
                                INSERT INTO locations (id, name, address, timezone, status, created_at, updated_at)
                                VALUES (:id, :name, :address, :timezone, :status, :created_at, :updated_at)
                            """), {
                                'id': location['id'],
                                'name': location.get('name', ''),
                                'address': json.dumps(location.get('address', {})),
                                'timezone': location.get('timezone', ''),
                                'status': location.get('status', 'ACTIVE'),
                                'created_at': datetime.now(),
                                'updated_at': datetime.now()
                            })
                    
                    logger.info(f"Synced {len(locations)} locations")
                    await engine.dispose()
                    return True
                else:
                    logger.error(f"Square API error: {response.status}")
                    await engine.dispose()
                    return False
                    
    except Exception as e:
        logger.error(f"Error syncing locations: {str(e)}")
        return False

async def sync_catalog_direct(access_token, base_url, db_url):
    """Sync catalog data directly"""
    try:
        timeout = aiohttp.ClientTimeout(total=600)
        engine = create_async_engine(db_url, echo=False)
        
        async with engine.begin() as conn:
            # Note: catalog data is already cleared in sync_locations_direct to maintain proper FK order
            
            # Sync categories
            categories = await fetch_catalog_objects_direct(access_token, base_url, "CATEGORY")
            for category in categories:
                await conn.execute(text("""
                    INSERT INTO catalog_categories (id, name, is_deleted, created_at, updated_at)
                    VALUES (:id, :name, :is_deleted, :created_at, :updated_at)
                """), {
                    'id': category['id'],
                    'name': category.get('category_data', {}).get('name', ''),
                    'is_deleted': False,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
            
            # Sync items
            items = await fetch_catalog_objects_direct(access_token, base_url, "ITEM")
            for item in items:
                item_data = item.get('item_data', {})
                await conn.execute(text("""
                    INSERT INTO catalog_items (id, name, description, category_id, is_deleted, created_at, updated_at)
                    VALUES (:id, :name, :description, :category_id, :is_deleted, :created_at, :updated_at)
                """), {
                    'id': item['id'],
                    'name': item_data.get('name', ''),
                    'description': item_data.get('description', ''),
                    'category_id': item_data.get('category_id'),
                    'is_deleted': False,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
            
            # Sync variations
            variations = await fetch_catalog_objects_direct(access_token, base_url, "ITEM_VARIATION")
            for variation in variations:
                variation_data = variation.get('item_variation_data', {})
                await conn.execute(text("""
                    INSERT INTO catalog_variations (id, name, item_id, sku, price_money, is_deleted, created_at, updated_at)
                    VALUES (:id, :name, :item_id, :sku, :price_money, :is_deleted, :created_at, :updated_at)
                """), {
                    'id': variation['id'],
                    'name': variation_data.get('name', ''),
                    'item_id': variation_data.get('item_id'),
                    'sku': variation_data.get('sku', ''),
                    'price_money': json.dumps(variation_data.get('price_money', {})),
                    'is_deleted': False,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
            
            logger.info(f"Synced {len(categories)} categories, {len(items)} items, {len(variations)} variations")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Error syncing catalog: {str(e)}")
        return False

async def sync_inventory_direct(access_token, base_url, db_url):
    """Sync inventory data directly"""
    try:
        timeout = aiohttp.ClientTimeout(total=600)
        engine = create_async_engine(db_url, echo=False)
        
        async with engine.begin() as conn:
            # Get locations
            locations_result = await conn.execute(text("SELECT id, name FROM locations WHERE status = 'ACTIVE'"))
            locations = locations_result.fetchall()
            
            if not locations:
                logger.error("No active locations found")
                return False
            
            # Note: inventory data is already cleared in sync_locations_direct to maintain proper FK order
            
            total_inventory = 0
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for location in locations:
                    location_id, location_name = location
                    
                    url = f"{base_url}/v2/inventory/counts/batch-retrieve"
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    body = {
                        'location_ids': [location_id],
                        'updated_after': '2020-01-01T00:00:00Z'
                    }
                    
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            counts = data.get('counts', [])
                            
                            for count in counts:
                                catalog_object_id = count.get('catalog_object_id')
                                quantity = int(count.get('quantity', 0))
                                
                                if catalog_object_id:
                                    await conn.execute(text("""
                                        INSERT INTO catalog_inventory (variation_id, location_id, quantity, calculated_at)
                                        VALUES (:variation_id, :location_id, :quantity, :calculated_at)
                                    """), {
                                        'variation_id': catalog_object_id,
                                        'location_id': location_id,
                                        'quantity': quantity,
                                        'calculated_at': datetime.now()
                                    })
                                    total_inventory += 1
                            
                            logger.info(f"Synced {len(counts)} inventory items for {location_name}")
                        else:
                            logger.error(f"Error fetching inventory for {location_name}: {response.status}")
            
            logger.info(f"Total inventory records: {total_inventory}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Error syncing inventory: {str(e)}")
        return False

async def fetch_catalog_objects_direct(access_token, base_url, object_type):
    """Fetch catalog objects from Square API"""
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        url = f"{base_url}/v2/catalog/search"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        all_objects = []
        cursor = None
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                body = {
                    "object_types": [object_type],
                    "limit": 1000,
                    "include_deleted_objects": False
                }
                
                if cursor:
                    body["cursor"] = cursor
                
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        objects = data.get('objects', [])
                        all_objects.extend(objects)
                        
                        cursor = data.get('cursor')
                        if not cursor:
                            break
                    else:
                        logger.error(f"Square API error for {object_type}: {response.status}")
                        break
        
        return all_objects
        
    except Exception as e:
        logger.error(f"Error fetching {object_type}: {str(e)}")
        return []

@router.get("/table-counts")
async def table_counts():
    """Get counts of all major tables for debugging"""
    try:
        async with get_session() as session:
            counts = {}
            
            tables = [
                "locations",
                "catalog_categories", 
                "catalog_items",
                "catalog_variations",
                "catalog_inventory"
            ]
            
            for table in tables:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                counts[table] = result.scalar()
            
            return JSONResponse(counts)
            
    except Exception as e:
        logger.error(f"Error getting table counts: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@router.get("/test-missing-sku")
async def test_missing_sku():
    """Test simplified missing SKU query for debugging"""
    try:
        async with get_session() as session:
            # Simplified version of the missing SKU query
            query = """
            SELECT 
                catalog_items.name AS item_name,
                catalog_variations.sku AS sku,
                catalog_variations.id AS variation_id,
                COUNT(catalog_inventory.id) as inventory_count
            FROM catalog_variations
            LEFT JOIN catalog_items ON catalog_variations.item_id = catalog_items.id
            LEFT JOIN catalog_inventory ON catalog_variations.id = catalog_inventory.variation_id
            WHERE (
                catalog_variations.sku IS NULL 
                OR catalog_variations.sku = '' 
                OR LENGTH(catalog_variations.sku) = 7
            )
            AND catalog_variations.is_deleted = false
            AND catalog_items.is_deleted = false
            GROUP BY catalog_items.name, catalog_variations.sku, catalog_variations.id
            LIMIT 10
            """
            
            result = await session.execute(text(query))
            items = result.mappings().all()
            
            return JSONResponse({
                "total_items": len(items),
                "items": [dict(item) for item in items]
            })
            
    except Exception as e:
        logger.error(f"Error in test missing SKU: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@router.get("/test-inventory-quantities")
async def test_inventory_quantities():
    """Test inventory quantities for missing SKU items"""
    try:
        async with get_session() as session:
            # Check inventory quantities for items with 7-character SKUs
            query = """
            SELECT 
                catalog_items.name AS item_name,
                catalog_variations.sku AS sku,
                locations.name AS location_name,
                catalog_inventory.quantity,
                CASE 
                    WHEN catalog_inventory.quantity > 0 THEN 'Has Stock'
                    WHEN catalog_inventory.quantity = 0 THEN 'Zero Stock'
                    WHEN catalog_inventory.quantity IS NULL THEN 'No Record'
                    ELSE 'Negative Stock'
                END AS stock_status
            FROM catalog_variations
            LEFT JOIN catalog_items ON catalog_variations.item_id = catalog_items.id
            LEFT JOIN catalog_inventory ON catalog_variations.id = catalog_inventory.variation_id
            LEFT JOIN locations ON catalog_inventory.location_id = locations.id
            WHERE LENGTH(catalog_variations.sku) = 7
            AND catalog_variations.is_deleted = false
            AND catalog_items.is_deleted = false
            AND catalog_items.name IN ('Big Win', 'Attack of The Clans')
            ORDER BY catalog_items.name, locations.name
            """
            
            result = await session.execute(text(query))
            items = result.mappings().all()
            
            return JSONResponse({
                "total_records": len(items),
                "items": [dict(item) for item in items]
            })
            
    except Exception as e:
        logger.error(f"Error in test inventory quantities: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": str(e)
        }, status_code=500) 