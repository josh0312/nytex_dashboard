import logging
import os
import json
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.database import get_session
from app.config import Config, get_database_url
from app.templates_config import templates
from app.logger import logger
from app.services.incremental_sync_service import IncrementalSyncService
from sqlalchemy import text
import aiohttp
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import List, Dict, Any

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
        
        # Add debug information
        import os
        
        status["debug"] = {
            "env_vars": {
                'DB_USER': os.environ.get('DB_USER', 'NOT_SET'),
                'DB_NAME': os.environ.get('DB_NAME', 'NOT_SET'),
                'CLOUD_SQL_CONNECTION_NAME': os.environ.get('CLOUD_SQL_CONNECTION_NAME', 'NOT_SET'),
            },
            "constructed_url": get_database_url()[:80] + "..." if len(get_database_url()) > 80 else get_database_url(),
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
    """Trigger complete production data sync with incremental updates by default"""
    try:
        # Parse request body to check for full_refresh flag
        request_body = {}
        try:
            request_body = await request.json()
        except:
            pass  # No JSON body is fine, use defaults
        
        full_refresh = request_body.get('full_refresh', False)
        sync_mode = "FULL REFRESH" if full_refresh else "INCREMENTAL"
        
        logger.info(f"Starting complete production data sync via API - Mode: {sync_mode}")
        
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
        db_url = Config.get_database_url()
        
        logger.info(f"Using Square environment: {square_environment}")
        logger.info(f"Square API base URL: {base_url}")
        logger.info(f"Sync mode: {sync_mode}")
        
        # Initialize sync statistics
        sync_stats = {
            "locations": {"created": 0, "updated": 0, "deleted": 0},
            "categories": {"created": 0, "updated": 0, "deleted": 0},
            "items": {"created": 0, "updated": 0, "deleted": 0},
            "variations": {"created": 0, "updated": 0, "deleted": 0},
            "inventory": {"created": 0, "updated": 0, "deleted": 0},
            "vendors": {"created": 0, "updated": 0, "deleted": 0}
        }
        
        # Step 1: Sync Locations
        logger.info("Step 1: Syncing locations...")
        locations_result = await sync_locations_incremental(square_access_token, base_url, db_url, full_refresh)
        if not locations_result["success"]:
            return JSONResponse({
                "success": False,
                "error": f"Location sync failed: {locations_result['error']}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        sync_stats["locations"] = locations_result["stats"]
        
        # Step 2: Sync Catalog Data
        logger.info("Step 2: Syncing catalog data...")
        catalog_result = await sync_catalog_incremental(square_access_token, base_url, db_url, full_refresh)
        if not catalog_result["success"]:
            return JSONResponse({
                "success": False,
                "error": f"Catalog sync failed: {catalog_result['error']}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        sync_stats["categories"] = catalog_result["stats"]["categories"]
        sync_stats["items"] = catalog_result["stats"]["items"]
        sync_stats["variations"] = catalog_result["stats"]["variations"]
        
        # Step 3: Sync Inventory (Enhanced with Units Per Case and deduplication)
        logger.info("Step 3: Syncing inventory with advanced features...")
        inventory_result = await sync_inventory_incremental(square_access_token, base_url, db_url, full_refresh)
        if not inventory_result["success"]:
            return JSONResponse({
                "success": False,
                "error": f"Inventory sync failed: {inventory_result['error']}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=500)
        sync_stats["inventory"] = inventory_result["stats"]
        
        # Add catalog updates from inventory sync to the overall stats
        if "catalog_updates" in inventory_result:
            catalog_updates = inventory_result["catalog_updates"]
            # Add to existing catalog stats - ensure type safety
            items_updated = catalog_updates.get("items_updated", 0)
            variations_updated = catalog_updates.get("variations_updated", 0)
            
            # Ensure we're adding integers to integers
            if isinstance(items_updated, int) and isinstance(sync_stats["categories"]["updated"], int):
                sync_stats["categories"]["updated"] += items_updated
            if isinstance(variations_updated, int) and isinstance(sync_stats["variations"]["updated"], int):
                sync_stats["variations"]["updated"] += variations_updated
            
            # Log the enhanced features
            logger.info(f"📋 Catalog enhancements: {catalog_updates['items_updated']} items updated with Units Per Case, {catalog_updates['variations_updated']} variations updated")
            logger.info(f"📊 Inventory processing: {inventory_result.get('total_raw_items', 0)} raw items deduplicated to {inventory_result.get('unique_records', 0)} unique records")
        
        # Step 4: Sync Vendors
        logger.info("Step 4: Syncing vendors...")
        vendor_result = await sync_vendors_incremental(square_access_token, base_url, db_url, full_refresh)
        if not vendor_result["success"]:
            # Log vendor sync failure but don't fail entire sync since vendors might not be available
            logger.warning(f"Vendor sync failed (continuing with other data): {vendor_result['error']}")
            sync_stats["vendors"]["error"] = vendor_result["error"]
        else:
            sync_stats["vendors"] = vendor_result["stats"]
        
        # Calculate totals
        total_changes = sum(
            stats["created"] + stats["updated"] + stats["deleted"] 
            for stats in sync_stats.values() 
            if isinstance(stats, dict) and "created" in stats and "error" not in stats
        )
        
        success_message = f"Complete production sync successful ({sync_mode}) - {total_changes} total changes"
        logger.info(success_message)
        
        # Enhanced response with catalog updates
        response_data = {
            "success": True,
            "message": success_message,
            "sync_mode": sync_mode,
            "sync_stats": sync_stats,
            "total_changes": total_changes,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add enhanced inventory details if available
        if "catalog_updates" in inventory_result:
            response_data["enhanced_features"] = {
                "units_per_case_updates": inventory_result["catalog_updates"],
                "inventory_deduplication": {
                    "raw_items": inventory_result.get("total_raw_items", 0),
                    "unique_records": inventory_result.get("unique_records", 0)
                }
            }
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error during complete sync: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Complete sync error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

@router.post("/incremental-sync")
async def incremental_sync_api(request: Request):
    """API endpoint for incremental sync operations"""
    try:
        logger.info("🔄 Starting incremental sync via API")
        
        sync_service = IncrementalSyncService()
        
        async with get_session() as session:
            result = await sync_service.run_incremental_sync(session)
            await session.commit()
            
            if result['success']:
                logger.info(f"✅ Incremental sync completed: {result['total_changes']} changes applied")
                return JSONResponse({
                    "success": True,
                    "message": f"Incremental sync completed successfully - {result['total_changes']} changes applied",
                    "total_changes": result['total_changes'],
                    "results": result['results'],
                    "timestamp": result['timestamp']
                })
            else:
                logger.error(f"❌ Incremental sync failed: {result['error']}")
                return JSONResponse({
                    "success": False,
                    "error": result['error'],
                    "timestamp": result['timestamp']
                }, status_code=500)
        
    except Exception as e:
        logger.error(f"❌ Error during incremental sync API: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Incremental sync API error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

@router.post("/foundation-sync")
async def foundation_sync_api(request: Request):
    """API endpoint to establish foundation data for incremental syncing"""
    try:
        logger.info("🚀 Starting foundation sync via API")
        
        # Run the existing complete sync but with enhanced logging
        sync_service = IncrementalSyncService()
        
        async with get_session() as session:
            # First ensure sync state table exists
            await sync_service._ensure_sync_state_table(session)
            
            # Run foundation sync (use the existing complete sync for now)
            result = await complete_sync(request)
            
            if hasattr(result, 'status_code') and result.status_code == 200:
                # If successful, initialize sync state tracking
                await sync_service._update_sync_status(session, 'foundation_sync', 0)
                await session.commit()
                
                logger.info("✅ Foundation sync completed successfully")
                return JSONResponse({
                    "success": True,
                    "message": "Foundation sync completed - baseline data established for incremental syncing",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                return result
        
    except Exception as e:
        logger.error(f"❌ Error during foundation sync API: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Foundation sync API error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

@router.get("/sync-status")
async def get_sync_status_api():
    """Get detailed sync status and metrics"""
    try:
        logger.info("📊 Getting sync status via API")
        
        sync_service = IncrementalSyncService()
        
        async with get_session() as session:
            status = await sync_service.get_sync_status(session)
            
            # Also get table counts for comparison
            table_counts = {}
            tables_to_check = [
                'locations', 'catalog_categories', 'catalog_items', 
                'catalog_variations', 'catalog_inventory', 'vendors'
            ]
            
            for table in tables_to_check:
                try:
                    result = await session.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    table_counts[table] = count
                except Exception as e:
                    table_counts[table] = f"Error: {str(e)}"
            
            return JSONResponse({
                "success": True,
                "sync_status": status,
                "table_counts": table_counts,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
    except Exception as e:
        logger.error(f"❌ Error getting sync status: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Sync status API error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

@router.post("/table-migration")
async def migrate_missing_tables():
    """Create missing table schemas in production"""
    try:
        logger.info("🔧 Starting table migration for missing schemas")
        
        from app.database import get_engine, Base, init_models
        
        # Initialize models to register all tables
        init_models()
        
        # Get engine
        engine = get_engine()
        if not engine:
            return JSONResponse({
                "success": False,
                "message": "Database engine not available"
            }, status_code=500)
        
        # Create all tables (only missing ones will be created)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Table migration completed successfully")
        return JSONResponse({
            "success": True,
            "message": "Table migration completed - all missing schemas created",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error during table migration: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Table migration error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

@router.post("/bulk-data-sync")
async def bulk_data_sync_api(request: Request):
    """API endpoint for bulk data synchronization from local to production"""
    try:
        logger.info("🚛 Starting bulk data sync from local database")
        
        # Tables to sync in priority order
        sync_tables = [
            'orders',
            'order_line_items', 
            'payments',
            'tenders',
            'operating_seasons',
            'catalog_location_availability',
            'catalog_vendor_info',
            'inventory_counts',
            'square_item_library_export'
        ]
        
        total_synced = 0
        sync_results = {}
        
        async with get_session() as session:
            for table_name in sync_tables:
                logger.info(f"🔄 Syncing table: {table_name}")
                
                try:
                    # Get count first
                    count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    total_count = count_result.scalar()
                    
                    if total_count == 0:
                        logger.info(f"⏭️ Skipping {table_name} - no data")
                        sync_results[table_name] = {"status": "skipped", "records": 0}
                        continue
                    
                    # For large tables, use batching
                    batch_size = 1000 if total_count > 10000 else total_count
                    synced_count = 0
                    
                    for offset in range(0, total_count, batch_size):
                        # Get batch of data
                        data_result = await session.execute(text(f"""
                            SELECT * FROM "{table_name}" 
                            ORDER BY (SELECT NULL) 
                            LIMIT {batch_size} OFFSET {offset}
                        """))
                        
                        batch_data = data_result.fetchall()
                        columns = data_result.keys()
                        
                        if not batch_data:
                            break
                        
                        # Convert to dict format
                        batch_records = []
                        for row in batch_data:
                            record = {}
                            for i, col in enumerate(columns):
                                value = row[i]
                                # Handle JSON columns
                                if isinstance(value, dict) or isinstance(value, list):
                                    record[col] = json.dumps(value)
                                elif value is not None:
                                    record[col] = value
                                else:
                                    record[col] = None
                            batch_records.append(record)
                        
                        # Apply batch using upsert
                        batch_synced = await apply_bulk_upsert(session, table_name, batch_records, columns)
                        synced_count += batch_synced
                        
                        logger.info(f"  📦 Batch {offset//batch_size + 1}: {batch_synced} records")
                    
                    await session.commit()
                    sync_results[table_name] = {"status": "completed", "records": synced_count}
                    total_synced += synced_count
                    logger.info(f"✅ {table_name}: {synced_count:,} records synced")
                    
                except Exception as e:
                    await session.rollback()
                    error_msg = str(e)[:100]
                    logger.error(f"❌ Error syncing {table_name}: {error_msg}")
                    sync_results[table_name] = {"status": "error", "error": error_msg}
        
        logger.info(f"🎉 Bulk sync completed: {total_synced:,} total records")
        
        return JSONResponse({
            "success": True,
            "message": f"Bulk data sync completed successfully",
            "total_records_synced": total_synced,
            "table_results": sync_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error during bulk data sync: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Bulk sync error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

@router.post("/import-table-data")
async def import_table_data_api(request: Request):
    """API endpoint to import table data from JSON export"""
    try:
        # Get JSON data from request
        import_data = await request.json()
        
        table_name = import_data.get('table')
        columns = import_data.get('columns', [])
        data_records = import_data.get('data', [])
        
        if not table_name or not data_records:
            return JSONResponse({
                "success": False,
                "error": "Invalid import data - missing table name or data"
            }, status_code=400)
        
        logger.info(f"📥 Importing {len(data_records):,} records into {table_name}")
        
        async with get_session() as session:
            # Process in batches for large datasets
            batch_size = 1000
            total_imported = 0
            
            for i in range(0, len(data_records), batch_size):
                batch = data_records[i:i + batch_size]
                batch_imported = await apply_bulk_upsert(session, table_name, batch, columns)
                total_imported += batch_imported
                
                logger.info(f"  📦 Batch {i//batch_size + 1}: {batch_imported} records imported")
            
            await session.commit()
            
        logger.info(f"✅ Import completed: {total_imported:,} records imported into {table_name}")
        
        return JSONResponse({
            "success": True,
            "message": f"Successfully imported {total_imported:,} records into {table_name}",
            "table": table_name,
            "records_imported": total_imported,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error importing table data: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Import error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

async def apply_bulk_upsert(session: AsyncSession, table_name: str, records: List[Dict], columns: List[str]) -> int:
    """Apply bulk upsert for any table"""
    if not records:
        return 0
    
    # Build dynamic upsert query
    columns_list = list(columns)
    placeholders = ', '.join([f':{col}' for col in columns_list])
    columns_str = ', '.join([f'"{col}"' for col in columns_list])
    
    # Determine primary key (assume first column or 'id')
    pk_column = 'id' if 'id' in columns_list else columns_list[0]
    
    # Build UPDATE SET clause (exclude primary key)
    update_columns = [col for col in columns_list if col != pk_column]
    update_set = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in update_columns])
    
    query = f"""
        INSERT INTO "{table_name}" ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT ("{pk_column}") DO UPDATE SET
        {update_set}
    """
    
    changes = 0
    for record in records:
        try:
            await session.execute(text(query), record)
            changes += 1
        except Exception as e:
            logger.warning(f"Failed to upsert record in {table_name}: {str(e)[:50]}")
    
    return changes

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
                        await conn.execute(text("DELETE FROM catalog_vendor_info"))
                        await conn.execute(text("DELETE FROM vendors"))
                        await conn.execute(text("DELETE FROM catalog_location_availability"))
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

@router.get("/debug-db-config")
async def debug_db_config():
    """Debug endpoint to show database configuration"""
    try:
        import os
        from app.config import Config, get_database_url
        
        # Get environment variables
        env_vars = {
            'SQLALCHEMY_DATABASE_URI': os.environ.get('SQLALCHEMY_DATABASE_URI', 'NOT_SET'),
            'DATABASE_URL': os.environ.get('DATABASE_URL', 'NOT_SET'),
            'DB_USER': os.environ.get('DB_USER', 'NOT_SET'),
            'DB_PASS': os.environ.get('DB_PASS', 'NOT_SET')[:10] + '...' if os.environ.get('DB_PASS') else 'NOT_SET',
            'DB_NAME': os.environ.get('DB_NAME', 'NOT_SET'),
            'CLOUD_SQL_CONNECTION_NAME': os.environ.get('CLOUD_SQL_CONNECTION_NAME', 'NOT_SET'),
        }
        
        # Get constructed URLs
        runtime_url = get_database_url()
        config_url = Config.get_database_url()
        static_url = getattr(Config, 'SQLALCHEMY_DATABASE_URI', 'NOT_SET')
        
        return JSONResponse({
            "environment_variables": env_vars,
            "constructed_urls": {
                "runtime_function": runtime_url[:50] + "..." if len(runtime_url) > 50 else runtime_url,
                "config_method": config_url[:50] + "..." if len(config_url) > 50 else config_url,
                "static_attribute": static_url[:50] + "..." if len(static_url) > 50 else static_url,
            },
            "url_matches": {
                "runtime_vs_config": runtime_url == config_url,
                "runtime_vs_static": runtime_url == static_url,
            }
        })
        
    except Exception as e:
        return JSONResponse({
            "error": str(e)
        }, status_code=500) 

async def sync_locations_incremental(access_token, base_url, db_url, full_refresh=False):
    """Sync locations with incremental updates or full refresh"""
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        engine = create_async_engine(db_url, echo=False)
        stats = {"created": 0, "updated": 0, "deleted": 0}
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{base_url}/v2/locations"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Square API error: {response.status}")
                    await engine.dispose()
                    return {"success": False, "error": f"Square API error: {response.status}", "stats": stats}
                
                data = await response.json()
                locations = data.get('locations', [])
                square_location_ids = {loc['id'] for loc in locations}
                
                async with engine.begin() as conn:
                    if full_refresh:
                        # Full refresh mode - clear all data using TRUNCATE CASCADE
                        logger.info("🔥 FULL REFRESH MODE: Truncating all tables with CASCADE")
                        # Use TRUNCATE CASCADE to automatically handle all foreign key constraints
                        await conn.execute(text("TRUNCATE TABLE locations, catalog_categories, catalog_items, catalog_variations, catalog_inventory, catalog_location_availability, catalog_vendor_info, vendors CASCADE"))
                        stats["deleted"] = 0  # Reset to 0 since we truncated everything
                    else:
                        # Incremental mode - get existing locations
                        existing_result = await conn.execute(text("SELECT id FROM locations"))
                        existing_ids = {row[0] for row in existing_result.fetchall()}
                        
                        # Mark locations as deleted if they're no longer in Square
                        deleted_ids = existing_ids - square_location_ids
                        for deleted_id in deleted_ids:
                            await conn.execute(text("""
                                UPDATE locations SET status = 'INACTIVE', updated_at = :updated_at
                                WHERE id = :id
                            """), {
                                'id': deleted_id,
                                'updated_at': datetime.now()
                            })
                            stats["deleted"] += 1
                            logger.info(f"📍 Marked location as INACTIVE: {deleted_id}")
                    
                    # Process each location from Square
                    for location in locations:
                        location_data = {
                            'id': location['id'],
                            'name': location.get('name', ''),
                            'address': json.dumps(location.get('address', {})),
                            'timezone': location.get('timezone', ''),
                            'status': location.get('status', 'ACTIVE'),
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        }
                        
                        if full_refresh:
                            # Insert all locations
                            await conn.execute(text("""
                                INSERT INTO locations (id, name, address, timezone, status, created_at, updated_at)
                                VALUES (:id, :name, :address, :timezone, :status, :created_at, :updated_at)
                            """), location_data)
                            stats["created"] += 1
                        else:
                            # Upsert location
                            result = await conn.execute(text("""
                                INSERT INTO locations (id, name, address, timezone, status, created_at, updated_at)
                                VALUES (:id, :name, :address, :timezone, :status, :created_at, :updated_at)
                                ON CONFLICT (id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    address = EXCLUDED.address,
                                    timezone = EXCLUDED.timezone,
                                    status = EXCLUDED.status,
                                    updated_at = EXCLUDED.updated_at
                                RETURNING (xmax = 0) AS inserted
                            """), location_data)
                            
                            row = result.fetchone()
                            if row and row[0]:  # xmax = 0 means it was an INSERT
                                stats["created"] += 1
                                logger.info(f"📍 Created location: {location['name']}")
                            else:
                                stats["updated"] += 1
                                logger.info(f"📍 Updated location: {location['name']}")
                
                mode_text = "FULL REFRESH" if full_refresh else "INCREMENTAL"
                logger.info(f"✅ Locations sync completed ({mode_text}): {stats}")
                await engine.dispose()
                return {"success": True, "stats": stats}
                    
    except Exception as e:
        logger.error(f"Error syncing locations: {str(e)}")
        return {"success": False, "error": str(e), "stats": stats}

async def sync_catalog_incremental(access_token, base_url, db_url, full_refresh=False):
    """Sync catalog data with incremental updates or full refresh"""
    try:
        timeout = aiohttp.ClientTimeout(total=600)
        engine = create_async_engine(db_url, echo=False)
        stats = {
            "categories": {"created": 0, "updated": 0, "deleted": 0},
            "items": {"created": 0, "updated": 0, "deleted": 0},
            "variations": {"created": 0, "updated": 0, "deleted": 0}
        }
        
        async with engine.begin() as conn:
            if full_refresh:
                # Full refresh mode - catalog data already cleared in locations sync
                logger.info("🔥 FULL REFRESH MODE: Catalog tables already cleared")
            
            # Fetch all catalog data from Square
            categories = await fetch_catalog_objects_direct(access_token, base_url, "CATEGORY")
            items = await fetch_catalog_objects_direct(access_token, base_url, "ITEM")
            variations = await fetch_catalog_objects_direct(access_token, base_url, "ITEM_VARIATION")
            
            square_category_ids = {cat['id'] for cat in categories}
            square_item_ids = {item['id'] for item in items}
            square_variation_ids = {var['id'] for var in variations}
            
            if not full_refresh:
                # Mark deleted categories
                existing_result = await conn.execute(text("SELECT id FROM catalog_categories WHERE is_deleted = false"))
                existing_category_ids = {row[0] for row in existing_result.fetchall()}
                deleted_category_ids = existing_category_ids - square_category_ids
                for deleted_id in deleted_category_ids:
                    await conn.execute(text("""
                        UPDATE catalog_categories SET is_deleted = true, updated_at = :updated_at
                        WHERE id = :id
                    """), {'id': deleted_id, 'updated_at': datetime.now()})
                    stats["categories"]["deleted"] += 1
                
                # Mark deleted items
                existing_result = await conn.execute(text("SELECT id FROM catalog_items WHERE is_deleted = false"))
                existing_item_ids = {row[0] for row in existing_result.fetchall()}
                deleted_item_ids = existing_item_ids - square_item_ids
                for deleted_id in deleted_item_ids:
                    await conn.execute(text("""
                        UPDATE catalog_items SET is_deleted = true, updated_at = :updated_at
                        WHERE id = :id
                    """), {'id': deleted_id, 'updated_at': datetime.now()})
                    stats["items"]["deleted"] += 1
                
                # Mark deleted variations
                existing_result = await conn.execute(text("SELECT id FROM catalog_variations WHERE is_deleted = false"))
                existing_variation_ids = {row[0] for row in existing_result.fetchall()}
                deleted_variation_ids = existing_variation_ids - square_variation_ids
                for deleted_id in deleted_variation_ids:
                    await conn.execute(text("""
                        UPDATE catalog_variations SET is_deleted = true, updated_at = :updated_at
                        WHERE id = :id
                    """), {'id': deleted_id, 'updated_at': datetime.now()})
                    stats["variations"]["deleted"] += 1
            
            # Sync categories
            for category in categories:
                category_data = {
                    'id': category['id'],
                    'name': category.get('category_data', {}).get('name', ''),
                    'is_deleted': False,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                if full_refresh:
                    await conn.execute(text("""
                        INSERT INTO catalog_categories (id, name, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :is_deleted, :created_at, :updated_at)
                    """), category_data)
                    stats["categories"]["created"] += 1
                else:
                    result = await conn.execute(text("""
                        INSERT INTO catalog_categories (id, name, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :is_deleted, :created_at, :updated_at)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            is_deleted = EXCLUDED.is_deleted,
                            updated_at = EXCLUDED.updated_at
                        RETURNING (xmax = 0) AS inserted
                    """), category_data)
                    
                    row = result.fetchone()
                    if row and row[0]:
                        stats["categories"]["created"] += 1
                    else:
                        stats["categories"]["updated"] += 1
            
            # Sync items
            for item in items:
                item_data_obj = item.get('item_data', {})
                item_data = {
                    'id': item['id'],
                    'name': item_data_obj.get('name', ''),
                    'description': item_data_obj.get('description', ''),
                    'category_id': item_data_obj.get('category_id'),
                    'is_deleted': False,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                if full_refresh:
                    await conn.execute(text("""
                        INSERT INTO catalog_items (id, name, description, category_id, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :description, :category_id, :is_deleted, :created_at, :updated_at)
                    """), item_data)
                    stats["items"]["created"] += 1
                else:
                    result = await conn.execute(text("""
                        INSERT INTO catalog_items (id, name, description, category_id, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :description, :category_id, :is_deleted, :created_at, :updated_at)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            category_id = EXCLUDED.category_id,
                            is_deleted = EXCLUDED.is_deleted,
                            updated_at = EXCLUDED.updated_at
                        RETURNING (xmax = 0) AS inserted
                    """), item_data)
                    
                    row = result.fetchone()
                    if row and row[0]:
                        stats["items"]["created"] += 1
                    else:
                        stats["items"]["updated"] += 1
            
            # Sync variations
            for variation in variations:
                variation_data_obj = variation.get('item_variation_data', {})
                variation_data = {
                    'id': variation['id'],
                    'name': variation_data_obj.get('name', ''),
                    'item_id': variation_data_obj.get('item_id'),
                    'sku': variation_data_obj.get('sku', ''),
                    'price_money': json.dumps(variation_data_obj.get('price_money', {})),
                    'is_deleted': False,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                if full_refresh:
                    await conn.execute(text("""
                        INSERT INTO catalog_variations (id, name, item_id, sku, price_money, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :item_id, :sku, :price_money, :is_deleted, :created_at, :updated_at)
                    """), variation_data)
                    stats["variations"]["created"] += 1
                else:
                    result = await conn.execute(text("""
                        INSERT INTO catalog_variations (id, name, item_id, sku, price_money, is_deleted, created_at, updated_at)
                        VALUES (:id, :name, :item_id, :sku, :price_money, :is_deleted, :created_at, :updated_at)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            item_id = EXCLUDED.item_id,
                            sku = EXCLUDED.sku,
                            price_money = EXCLUDED.price_money,
                            is_deleted = EXCLUDED.is_deleted,
                            updated_at = EXCLUDED.updated_at
                        RETURNING (xmax = 0) AS inserted
                    """), variation_data)
                    
                    row = result.fetchone()
                    if row and row[0]:
                        stats["variations"]["created"] += 1
                    else:
                        stats["variations"]["updated"] += 1
            
            mode_text = "FULL REFRESH" if full_refresh else "INCREMENTAL"
            logger.info(f"✅ Catalog sync completed ({mode_text}): {stats}")
        
        await engine.dispose()
        return {"success": True, "stats": stats}
        
    except Exception as e:
        logger.error(f"Error syncing catalog: {str(e)}")
        return {"success": False, "error": str(e), "stats": stats}

async def sync_inventory_incremental(access_token, base_url, db_url, full_refresh=False):
    """Enhanced inventory sync with Units Per Case, deduplication, and catalog updates"""
    try:
        timeout = aiohttp.ClientTimeout(total=600)
        engine = create_async_engine(db_url, echo=False)
        stats = {"created": 0, "updated": 0, "deleted": 0}
        catalog_updates = {
            'items_updated': 0,
            'variations_updated': 0,
            'items_with_units': 0,
            'variations_with_units': 0
        }
        
        # Units Per Case attribute ID
        units_per_case_id = "WLEIG6KKOKGRMX2PG2TCZFP7"
        
        def extract_units_per_case(obj: Dict[str, Any]) -> int:
            """Extract Units Per Case value from a catalog object's custom attributes"""
            try:
                if 'custom_attribute_values' in obj:
                    custom_attrs = obj['custom_attribute_values']
                    
                    # Look for Units Per Case specifically
                    for attr_key, attr_data in custom_attrs.items():
                        if (attr_data.get('custom_attribute_definition_id') == units_per_case_id or
                            attr_data.get('name') == 'Units Per Case'):
                            units_value = attr_data.get('number_value')
                            if units_value is not None:
                                try:
                                    # Convert to float first, then to int (handles decimal values from Square)
                                    return int(float(units_value))
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid Units Per Case value: {units_value} for object {obj.get('id')}")
                                    return None
                            break
                
                return None
            except Exception as e:
                logger.error(f"Error extracting Units Per Case from object {obj.get('id')}: {str(e)}")
                return None
        
        async with engine.begin() as conn:
            # Get active locations
            locations_result = await conn.execute(text("SELECT id, name FROM locations WHERE status = 'ACTIVE'"))
            locations = locations_result.fetchall()
            
            if not locations:
                logger.error("No active locations found")
                await engine.dispose()
                return {"success": False, "error": "No active locations found", "stats": stats}
            
            if full_refresh:
                # Full refresh mode - inventory data already cleared in locations sync
                logger.info("🔥 FULL REFRESH MODE: Inventory table already cleared")
            
            # Step 1: Update catalog items and variations with Units Per Case
            logger.info("📋 Updating catalog with Units Per Case data...")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                catalog_url = f"{base_url}/v2/catalog/search"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Get existing catalog items for comparison
                db_items_result = await conn.execute(text("SELECT id, units_per_case FROM catalog_items WHERE is_deleted = false"))
                db_items = {row[0]: row[1] for row in db_items_result.fetchall()}
                
                # Fetch and update items
                all_items = []
                cursor = None
                page = 1
                
                while True:
                    body = {
                        "object_types": ["ITEM"],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    logger.info(f"📋 Fetching catalog items page {page} for Units Per Case sync...")
                    
                    async with session.post(catalog_url, headers=headers, json=body) as response:
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
                            logger.error(f"Square API error fetching items: {response.status} - {error_text}")
                            break
                
                # Process items and update Units Per Case
                for square_item in all_items:
                    item_id = square_item.get('id')
                    
                    if not item_id or item_id not in db_items:
                        continue
                    
                    units_per_case = extract_units_per_case(square_item)
                    
                    if units_per_case is not None:
                        catalog_updates['items_with_units'] += 1
                    
                    # Update if different
                    current_units = db_items[item_id]
                    if current_units != units_per_case:
                        await conn.execute(text("""
                            UPDATE catalog_items 
                            SET units_per_case = :units_per_case, updated_at = :updated_at
                            WHERE id = :id
                        """), {
                            'id': item_id,
                            'units_per_case': units_per_case,
                            'updated_at': datetime.now()
                        })
                        catalog_updates['items_updated'] += 1
                
                # Get existing catalog variations for comparison
                db_variations_result = await conn.execute(text("SELECT id, units_per_case FROM catalog_variations WHERE is_deleted = false"))
                db_variations = {row[0]: row[1] for row in db_variations_result.fetchall()}
                
                # Fetch and update variations
                all_variations = []
                cursor = None
                page = 1
                
                while True:
                    body = {
                        "object_types": ["ITEM_VARIATION"],
                        "limit": 1000,
                        "include_deleted_objects": False
                    }
                    
                    if cursor:
                        body["cursor"] = cursor
                    
                    logger.info(f"🔧 Fetching catalog variations page {page} for Units Per Case sync...")
                    
                    async with session.post(catalog_url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            variations = data.get('objects', [])
                            all_variations.extend(variations)
                            
                            logger.info(f"Retrieved {len(variations)} variations on page {page} (total: {len(all_variations)})")
                            
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                            page += 1
                        else:
                            error_text = await response.text()
                            logger.error(f"Square API error fetching variations: {response.status} - {error_text}")
                            break
                
                # Process variations and update Units Per Case
                for square_variation in all_variations:
                    variation_id = square_variation.get('id')
                    
                    if not variation_id or variation_id not in db_variations:
                        continue
                    
                    units_per_case = extract_units_per_case(square_variation)
                    
                    if units_per_case is not None:
                        catalog_updates['variations_with_units'] += 1
                    
                    # Update if different
                    current_units = db_variations[variation_id]
                    if current_units != units_per_case:
                        await conn.execute(text("""
                            UPDATE catalog_variations 
                            SET units_per_case = :units_per_case, updated_at = :updated_at
                            WHERE id = :id
                        """), {
                            'id': variation_id,
                            'units_per_case': units_per_case,
                            'updated_at': datetime.now()
                        })
                        catalog_updates['variations_updated'] += 1
                
                logger.info(f"📋 Catalog updates completed - Items: {catalog_updates['items_updated']} updated ({catalog_updates['items_with_units']} with units), Variations: {catalog_updates['variations_updated']} updated ({catalog_updates['variations_with_units']} with units)")
                
                # Step 2: Fetch inventory data with advanced deduplication
                logger.info("📦 Fetching inventory data with deduplication...")
                
                # Get catalog to variation mapping for validation
                catalog_to_variation_result = await conn.execute(text("SELECT id FROM catalog_variations WHERE is_deleted = false"))
                catalog_to_variation = {row[0] for row in catalog_to_variation_result.fetchall()}
                
                # Collect all inventory data first for deduplication
                location_inventory = {}
                total_raw_items = 0
                
                for location in locations:
                    location_id, location_name = location
                    
                    location_inventory_items = []
                    cursor = None
                    
                    inventory_url = f"{base_url}/v2/inventory/counts/batch-retrieve"
                    
                    request_body = {
                        'location_ids': [location_id],
                        'updated_after': '2020-01-01T00:00:00Z'
                    }
                    
                    while True:
                        if cursor:
                            request_body["cursor"] = cursor
                        
                        async with session.post(inventory_url, headers=headers, json=request_body) as response:
                            if response.status == 200:
                                data = await response.json()
                                counts = data.get('counts', [])
                                
                                logger.info(f"📦 Retrieved {len(counts)} inventory items for {location_name}")
                                location_inventory_items.extend(counts)
                                total_raw_items += len(counts)
                                
                                # Check for more pages
                                cursor = data.get('cursor')
                                if not cursor:
                                    break
                            else:
                                error_text = await response.text()
                                logger.error(f"Error fetching inventory for {location_name}: {response.status} - {error_text}")
                                break
                    
                    location_inventory[location_id] = location_inventory_items
                    logger.info(f"📦 Total inventory items for {location_name}: {len(location_inventory_items)}")
                
                # Advanced deduplication logic
                logger.info(f"📊 Processing {total_raw_items} raw inventory items for deduplication...")
                unique_inventory = {}
                
                for location_id, inventory_items in location_inventory.items():
                    for item in inventory_items:
                        catalog_object_id = item.get('catalog_object_id')
                        quantity = item.get('quantity', '0')
                        calculated_at = item.get('calculated_at')
                        
                        # Convert quantity to integer
                        try:
                            quantity_int = int(quantity)
                        except (ValueError, TypeError):
                            quantity_int = 0
                        
                        # Parse calculated_at timestamp
                        calculated_datetime = None
                        if calculated_at:
                            try:
                                calculated_datetime = datetime.fromisoformat(calculated_at.replace('Z', '+00:00'))
                                # Convert to timezone-naive UTC for database storage
                                if calculated_datetime.tzinfo is not None:
                                    calculated_datetime = calculated_datetime.astimezone(timezone.utc).replace(tzinfo=None)
                            except ValueError:
                                calculated_datetime = datetime.now(timezone.utc).replace(tzinfo=None)
                        else:
                            calculated_datetime = datetime.now(timezone.utc).replace(tzinfo=None)
                        
                        # Only process if we have a matching variation and valid catalog object ID
                        if catalog_object_id and catalog_object_id in catalog_to_variation:
                            # Create unique key for deduplication
                            unique_key = (catalog_object_id, location_id)
                            
                            # If this combination doesn't exist or has a newer timestamp, update it
                            if (unique_key not in unique_inventory or 
                                (calculated_datetime and 
                                 unique_inventory[unique_key]['calculated_at'] < calculated_datetime)):
                                
                                unique_inventory[unique_key] = {
                                    'variation_id': catalog_object_id,
                                    'location_id': location_id,
                                    'quantity': quantity_int,
                                    'calculated_at': calculated_datetime
                                }
                
                logger.info(f"📊 Deduplicated to {len(unique_inventory)} unique inventory records")
                
                # Step 3: Update database with deduplicated inventory
                if full_refresh:
                    # Full refresh mode - inventory already cleared
                    for inventory_data in unique_inventory.values():
                        await conn.execute(text("""
                            INSERT INTO catalog_inventory (variation_id, location_id, quantity, calculated_at)
                            VALUES (:variation_id, :location_id, :quantity, :calculated_at)
                        """), inventory_data)
                        stats["created"] += 1
                else:
                    # Incremental mode - check for changes
                    for inventory_data in unique_inventory.values():
                        # Check if record exists and if quantity changed
                        existing_result = await conn.execute(text("""
                            SELECT quantity FROM catalog_inventory 
                            WHERE variation_id = :variation_id AND location_id = :location_id
                        """), {
                            'variation_id': inventory_data['variation_id'],
                            'location_id': inventory_data['location_id']
                        })
                        existing = existing_result.fetchone()
                        
                        if existing is None:
                            # Insert new record
                            await conn.execute(text("""
                                INSERT INTO catalog_inventory (variation_id, location_id, quantity, calculated_at)
                                VALUES (:variation_id, :location_id, :quantity, :calculated_at)
                            """), inventory_data)
                            stats["created"] += 1
                        elif existing[0] != inventory_data['quantity']:
                            # Update existing record only if quantity changed
                            await conn.execute(text("""
                                UPDATE catalog_inventory 
                                SET quantity = :quantity, calculated_at = :calculated_at, updated_at = :updated_at
                                WHERE variation_id = :variation_id AND location_id = :location_id
                            """), {
                                **inventory_data,
                                'updated_at': datetime.now()
                            })
                            stats["updated"] += 1
            
            mode_text = "FULL REFRESH" if full_refresh else "INCREMENTAL"
            logger.info(f"✅ Enhanced inventory sync completed ({mode_text}): {stats}")
            logger.info(f"📋 Catalog updates: {catalog_updates}")
        
        await engine.dispose()
        return {
            "success": True, 
            "stats": stats,
            "catalog_updates": catalog_updates,
            "total_raw_items": total_raw_items,
            "unique_records": len(unique_inventory) if 'unique_inventory' in locals() else 0
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced inventory sync: {str(e)}")
        return {"success": False, "error": str(e), "stats": stats}

@router.get("/logs")
async def get_recent_logs():
    """Get recent log entries for the admin log viewer"""
    try:
        import os
        
        # Try to read from the app.log file
        log_file_path = "app.log"
        
        if os.path.exists(log_file_path):
            # Read the last 50 lines of the log file
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                log_content = ''.join(recent_lines)
            
            return JSONResponse({
                "success": True,
                "logs": log_content,
                "lines_count": len(recent_lines),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Log file not found. Logs may be configured differently in production.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error reading logs: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Error reading logs: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)

async def sync_vendors_incremental(access_token, base_url, db_url, full_refresh=False):
    """Sync vendor data with incremental updates or full refresh"""
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        engine = create_async_engine(db_url, echo=False)
        stats = {"created": 0, "updated": 0, "deleted": 0}
        
        async with engine.begin() as conn:
            if full_refresh:
                # Full refresh mode - clear vendor tables
                logger.info("🔥 FULL REFRESH MODE: Clearing vendor tables")
                await conn.execute(text("DELETE FROM catalog_vendor_info"))
                await conn.execute(text("DELETE FROM vendors"))
            
            # Fetch vendors from Square using correct API endpoint
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{base_url}/v2/vendors/search"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Use search endpoint with empty query to get all vendors
                payload = {
                    "filter": {
                        "status": ["ACTIVE", "INACTIVE"]
                    }
                }
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        vendors = data.get('vendors', [])
                        logger.info(f"📦 Retrieved {len(vendors)} vendors from Square")
                        
                        # Process vendors
                        for vendor_data in vendors:
                            vendor_id = vendor_data['id']
                            vendor_name = vendor_data.get('name', '')
                            account_number = vendor_data.get('account_number', '')
                            status = vendor_data.get('status', 'ACTIVE')
                            
                            if full_refresh:
                                # Insert new vendor
                                await conn.execute(text("""
                                    INSERT INTO vendors (id, name, account_number, status, created_at, updated_at)
                                    VALUES (:id, :name, :account_number, :status, :created_at, :updated_at)
                                """), {
                                    'id': vendor_id,
                                    'name': vendor_name,
                                    'account_number': account_number,
                                    'status': status,
                                    'created_at': datetime.now(),
                                    'updated_at': datetime.now()
                                })
                                stats["created"] += 1
                            else:
                                # Incremental mode - check if vendor exists
                                existing_result = await conn.execute(text("""
                                    SELECT name, account_number, status FROM vendors WHERE id = :id
                                """), {'id': vendor_id})
                                existing = existing_result.fetchone()
                                
                                if existing is None:
                                    # Insert new vendor
                                    await conn.execute(text("""
                                        INSERT INTO vendors (id, name, account_number, status, created_at, updated_at)
                                        VALUES (:id, :name, :account_number, :status, :created_at, :updated_at)
                                    """), {
                                        'id': vendor_id,
                                        'name': vendor_name,
                                        'account_number': account_number,
                                        'status': status,
                                        'created_at': datetime.now(),
                                        'updated_at': datetime.now()
                                    })
                                    stats["created"] += 1
                                elif (existing[0] != vendor_name or 
                                      existing[1] != account_number or 
                                      existing[2] != status):
                                    # Update existing vendor
                                    await conn.execute(text("""
                                        UPDATE vendors 
                                        SET name = :name, account_number = :account_number, 
                                            status = :status, updated_at = :updated_at
                                        WHERE id = :id
                                    """), {
                                        'id': vendor_id,
                                        'name': vendor_name,
                                        'account_number': account_number,
                                        'status': status,
                                        'updated_at': datetime.now()
                                    })
                                    stats["updated"] += 1
                        
                        mode_text = "FULL REFRESH" if full_refresh else "INCREMENTAL"
                        logger.info(f"✅ Vendor sync completed ({mode_text}): {stats}")
                        
                    elif response.status == 404:
                        # Vendors API not available or no permission
                        error_text = await response.text()
                        logger.warning(f"Vendors API not available (404): {error_text}")
                        return {
                            "success": False, 
                            "error": "Vendors API not available - may require special permissions or account upgrade",
                            "stats": stats
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Error fetching vendors: {response.status} - {error_text}")
                        return {
                            "success": False, 
                            "error": f"Square API error: {response.status} - {error_text}",
                            "stats": stats
                        }
        
        await engine.dispose()
        return {"success": True, "stats": stats}
        
    except Exception as e:
        logger.error(f"Error in vendor sync: {str(e)}")
        return {"success": False, "error": str(e), "stats": stats}

@router.post("/historical-orders-sync")
async def historical_orders_sync_api(request: Request):
    """API endpoint to trigger historical orders sync from January 2018 to present"""
    try:
        logger.info("🚛 Starting historical orders sync from January 2018...")
        
        # Import required modules
        import aiohttp
        import time
        from datetime import datetime, timezone, timedelta
        from typing import List, Dict, Any, Optional, Tuple
        from dataclasses import dataclass
        
        @dataclass
        class SyncConfig:
            """Configuration for the historical sync"""
            start_date: datetime = datetime(2018, 1, 1, tzinfo=timezone.utc)
            end_date: datetime = datetime.now(timezone.utc)
            chunk_size_days: int = 30  # Process 30 days at a time
            batch_size: int = 100      # Insert 100 orders at a time
            max_requests_per_minute: int = 100  # Square API rate limit
            request_delay: float = 0.6  # Delay between requests (60s / 100 requests)
        
        # Initialize configuration
        config = SyncConfig()
        square_access_token = os.getenv('SQUARE_ACCESS_TOKEN')
        square_base_url = os.getenv('SQUARE_BASE_URL', 'https://connect.squareup.com')
        
        if not square_access_token:
            raise ValueError("SQUARE_ACCESS_TOKEN environment variable is required")
        
        # Track progress
        total_orders_synced = 0
        total_chunks_processed = 0
        errors = []
        
        def generate_date_chunks() -> List[Tuple[datetime, datetime]]:
            """Generate date chunks for processing"""
            chunks = []
            current_date = config.start_date
            
            while current_date < config.end_date:
                chunk_end = min(
                    current_date + timedelta(days=config.chunk_size_days),
                    config.end_date
                )
                chunks.append((current_date, chunk_end))
                current_date = chunk_end
            
            return chunks
        
        async def get_active_locations() -> List[Dict[str, Any]]:
            """Get active locations from Square API"""
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{square_base_url}/v2/locations"
                headers = {
                    'Authorization': f'Bearer {square_access_token}',
                    'Content-Type': 'application/json'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        locations = data.get('locations', [])
                        # Filter for active locations
                        active_locations = [loc for loc in locations if loc.get('status') == 'ACTIVE']
                        return active_locations
                    else:
                        error_text = await response.text()
                        raise Exception(f"Square API error getting locations: {response.status} - {error_text}")
        
        async def fetch_orders_for_period(location_ids: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
            """Fetch all orders for a specific date period"""
            all_orders = []
            
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{square_base_url}/v2/orders/search"
                headers = {
                    'Authorization': f'Bearer {square_access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Build query
                base_query = {
                    "location_ids": location_ids,
                    "query": {
                        "filter": {
                            "date_time_filter": {
                                "created_at": {
                                    "start_at": start_date.isoformat(),
                                    "end_at": end_date.isoformat()
                                }
                            },
                            "state_filter": {
                                "states": ["COMPLETED", "OPEN", "CANCELED"]  # Include all states for historical data
                            }
                        }
                    },
                    "limit": 500  # Maximum allowed by Square API
                }
                
                cursor = None
                page = 1
                
                while True:
                    # Add cursor if we have one
                    body = base_query.copy()
                    if cursor:
                        body["cursor"] = cursor
                    
                    # Rate limiting
                    await asyncio.sleep(config.request_delay)
                    
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            orders = data.get('orders', [])
                            all_orders.extend(orders)
                            
                            logger.info(f"  📄 Page {page}: retrieved {len(orders)} orders (total: {len(all_orders)})")
                            
                            # Check for more pages
                            cursor = data.get('cursor')
                            if not cursor:
                                break
                                
                            page += 1
                            
                        elif response.status == 429:
                            # Rate limited - wait longer
                            logger.warning("⏳ Rate limited, waiting 60 seconds...")
                            await asyncio.sleep(60)
                            continue
                            
                        else:
                            error_text = await response.text()
                            raise Exception(f"Square API error: {response.status} - {error_text}")
            
            return all_orders
        
        def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
            """Parse ISO timestamp string to datetime object"""
            if not timestamp_str:
                return None
            try:
                # Handle RFC3339 format from Square API
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Convert timezone-aware datetime to UTC, but keep timezone info
                # This preserves the original timezone context for proper conversion
                if dt.tzinfo:
                    # Convert to UTC but keep as timezone-aware
                    dt = dt.astimezone(timezone.utc)
                    # For database storage, we need to strip timezone but preserve the UTC conversion
                    dt = dt.replace(tzinfo=None)
                return dt
            except Exception as e:
                logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
                return None
        
        async def insert_orders_batch(session, orders: List[Dict[str, Any]]):
            """Insert orders using upsert"""
            for order_data in orders:
                await session.execute(text("""
                    INSERT INTO orders (
                        id, location_id, created_at, updated_at, closed_at,
                        state, version, total_money, total_tax_money, total_discount_money,
                        net_amounts, source, return_amounts, order_metadata
                    ) VALUES (
                        :id, :location_id, :created_at, :updated_at, :closed_at,
                        :state, :version, :total_money, :total_tax_money, :total_discount_money,
                        :net_amounts, :source, :return_amounts, :order_metadata
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        location_id = EXCLUDED.location_id,
                        updated_at = EXCLUDED.updated_at,
                        closed_at = EXCLUDED.closed_at,
                        state = EXCLUDED.state,
                        version = EXCLUDED.version,
                        total_money = EXCLUDED.total_money,
                        total_tax_money = EXCLUDED.total_tax_money,
                        total_discount_money = EXCLUDED.total_discount_money,
                        net_amounts = EXCLUDED.net_amounts,
                        source = EXCLUDED.source,
                        return_amounts = EXCLUDED.return_amounts,
                        order_metadata = EXCLUDED.order_metadata
                """), {
                    'id': order_data['id'],
                    'location_id': order_data.get('location_id'),
                    'created_at': parse_timestamp(order_data.get('created_at')),
                    'updated_at': parse_timestamp(order_data.get('updated_at')),
                    'closed_at': parse_timestamp(order_data.get('closed_at')),
                    'state': order_data.get('state'),
                    'version': order_data.get('version'),
                    'total_money': json.dumps(order_data.get('total_money', {})),
                    'total_tax_money': json.dumps(order_data.get('total_tax_money', {})),
                    'total_discount_money': json.dumps(order_data.get('total_discount_money', {})),
                    'net_amounts': json.dumps(order_data.get('net_amounts', {})),
                    'source': json.dumps(order_data.get('source', {})),
                    'return_amounts': json.dumps(order_data.get('return_amounts', {})),
                    'order_metadata': json.dumps(order_data.get('metadata', {}))
                })
        
        async def insert_order_line_items_batch(session, orders: List[Dict[str, Any]]):
            """Insert order line items"""
            for order_data in orders:
                line_items = order_data.get('line_items', [])
                for line_item in line_items:
                    await session.execute(text("""
                        INSERT INTO order_line_items (
                            uid, order_id, catalog_object_id, catalog_version, name, 
                            quantity, item_type, base_price_money, variation_total_price_money,
                            gross_sales_money, total_discount_money, total_tax_money, total_money,
                            variation_name, item_variation_metadata, note, applied_taxes, 
                            applied_discounts, modifiers, pricing_blocklists
                        ) VALUES (
                            :uid, :order_id, :catalog_object_id, :catalog_version, :name,
                            :quantity, :item_type, :base_price_money, :variation_total_price_money,
                            :gross_sales_money, :total_discount_money, :total_tax_money, :total_money,
                            :variation_name, :item_variation_metadata, :note, :applied_taxes,
                            :applied_discounts, :modifiers, :pricing_blocklists
                        )
                        ON CONFLICT (order_id, uid) DO UPDATE SET
                            catalog_object_id = EXCLUDED.catalog_object_id,
                            catalog_version = EXCLUDED.catalog_version,
                            name = EXCLUDED.name,
                            quantity = EXCLUDED.quantity,
                            item_type = EXCLUDED.item_type,
                            base_price_money = EXCLUDED.base_price_money,
                            variation_total_price_money = EXCLUDED.variation_total_price_money,
                            gross_sales_money = EXCLUDED.gross_sales_money,
                            total_discount_money = EXCLUDED.total_discount_money,
                            total_tax_money = EXCLUDED.total_tax_money,
                            total_money = EXCLUDED.total_money,
                            variation_name = EXCLUDED.variation_name,
                            item_variation_metadata = EXCLUDED.item_variation_metadata,
                            note = EXCLUDED.note,
                            applied_taxes = EXCLUDED.applied_taxes,
                            applied_discounts = EXCLUDED.applied_discounts,
                            modifiers = EXCLUDED.modifiers,
                            pricing_blocklists = EXCLUDED.pricing_blocklists
                    """), {
                        'uid': line_item['uid'],
                        'order_id': order_data['id'],
                        'catalog_object_id': line_item.get('catalog_object_id'),
                        'catalog_version': line_item.get('catalog_version'),
                        'name': line_item.get('name'),
                        'quantity': line_item.get('quantity'),
                        'item_type': line_item.get('item_type'),
                        'base_price_money': json.dumps(line_item.get('base_price_money', {})),
                        'variation_total_price_money': json.dumps(line_item.get('variation_total_price_money', {})),
                        'gross_sales_money': json.dumps(line_item.get('gross_sales_money', {})),
                        'total_discount_money': json.dumps(line_item.get('total_discount_money', {})),
                        'total_tax_money': json.dumps(line_item.get('total_tax_money', {})),
                        'total_money': json.dumps(line_item.get('total_money', {})),
                        'variation_name': line_item.get('variation_name'),
                        'item_variation_metadata': json.dumps(line_item.get('metadata', {})),
                        'note': line_item.get('note'),
                        'applied_taxes': json.dumps(line_item.get('applied_taxes', [])),
                        'applied_discounts': json.dumps(line_item.get('applied_discounts', [])),
                        'modifiers': json.dumps(line_item.get('modifiers', [])),
                        'pricing_blocklists': json.dumps(line_item.get('pricing_blocklists', {}))
                    })
        
        # Start the actual sync process
        start_time = time.time()
        logger.info("🚀 Starting historical orders sync...")
        
        # Get active locations first
        locations = await get_active_locations()
        if not locations:
            raise Exception("No active locations found")
        
        location_ids = [loc['id'] for loc in locations]
        logger.info(f"Found {len(location_ids)} active locations: {[loc['name'] for loc in locations]}")
        
        # Generate date chunks
        date_chunks = generate_date_chunks()
        logger.info(f"Generated {len(date_chunks)} date chunks to process")
        
        # Process each chunk
        async with get_session() as db_session:
            for i, (start_date, end_date) in enumerate(date_chunks, 1):
                logger.info(f"\n📅 Processing chunk {i}/{len(date_chunks)}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                
                try:
                    chunk_orders = await fetch_orders_for_period(location_ids, start_date, end_date)
                    
                    if chunk_orders:
                        # Process orders in batches
                        for j in range(0, len(chunk_orders), config.batch_size):
                            batch = chunk_orders[j:j + config.batch_size]
                            
                            # Insert orders
                            await insert_orders_batch(db_session, batch)
                            
                            # Insert line items for these orders
                            await insert_order_line_items_batch(db_session, batch)
                            
                            total_orders_synced += len(batch)
                            logger.info(f"  💾 Inserted batch of {len(batch)} orders (total: {total_orders_synced})")
                        
                        logger.info(f"✅ Processed {len(chunk_orders)} orders for period")
                    else:
                        logger.info(f"📭 No orders found for period")
                    
                    total_chunks_processed += 1
                    
                    # Commit after each chunk
                    await db_session.commit()
                    
                    # Rate limiting delay
                    await asyncio.sleep(config.request_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing chunk {i}: {str(e)}")
                    errors.append(f"Chunk {i} ({start_date} to {end_date}): {str(e)}")
                    await db_session.rollback()
                    # Continue with next chunk
                    continue
        
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            'success': True,
            'total_orders_synced': total_orders_synced,
            'total_chunks_processed': total_chunks_processed,
            'total_chunks': len(date_chunks),
            'duration_seconds': duration,
            'errors': errors
        }
        
        logger.info(f"\n🎉 Historical sync completed!")
        logger.info(f"Total orders synced: {total_orders_synced}")
        logger.info(f"Chunks processed: {total_chunks_processed}/{len(date_chunks)}")
        logger.info(f"Duration: {duration:.2f} seconds")
        
        return {
            "success": True,
            "message": f"Historical orders sync completed successfully",
            "total_orders_synced": result['total_orders_synced'],
            "total_chunks_processed": result['total_chunks_processed'],
            "total_chunks": result['total_chunks'],
            "duration_seconds": result['duration_seconds'],
            "errors": result.get('errors', [])
        }
            
    except Exception as e:
        logger.error(f"❌ Error in historical orders sync: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        } 