from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from app.services.square_catalog_service import SquareCatalogService
from app.database import get_session
from app.logger import logger
from app.templates_config import templates
import aiohttp
import asyncio
from sqlalchemy import text
from datetime import timezone
import pytz
import pandas as pd
from fastapi.responses import FileResponse
import os
import tempfile
from app.config import Config

router = APIRouter(tags=["catalog"])

@router.get("/")
async def catalog_index(request: Request):
    """Catalog management page"""
    try:
        logger.info("Loading catalog management page")
        
        # Get current export status
        async with get_session() as session:
            catalog_service = SquareCatalogService()
            status = await catalog_service.get_export_status(session)
        
        return templates.TemplateResponse("catalog/index.html", {
            "request": request,
            "status": status
        })
    except Exception as e:
        logger.error(f"Error loading catalog page: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/error.html", {
            "request": request,
            "title": "Catalog Management",
            "message": "Unable to load catalog management page"
        })

@router.post("/export")
async def export_catalog(request: Request, background_tasks: BackgroundTasks):
    """Trigger catalog export to database"""
    try:
        logger.info("Starting catalog export via API")
        
        async with get_session() as session:
            catalog_service = SquareCatalogService()
            result = await catalog_service.export_catalog_to_database(session)
        
        if result['success']:
            # Handle different response types based on status
            if result.get('status') == 'running':
                logger.info(f"Catalog export started: {result.get('message', 'Export started')}")
                return JSONResponse({
                    "success": True,
                    "message": result.get('message', 'Export started successfully'),
                    "data": result
                })
            else:
                # Completed or other status
                items_count = result.get('items_exported', 'unknown')
                logger.info(f"Catalog export completed successfully: {items_count} items")
                return JSONResponse({
                    "success": True,
                    "message": f"Successfully exported {items_count} items",
                    "data": result
                })
        else:
            logger.error(f"Catalog export failed: {result.get('error', 'Unknown error')}")
            return JSONResponse({
                "success": False,
                "message": f"Export failed: {result.get('error', 'Unknown error')}",
                "data": result
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error during catalog export: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Export failed: {str(e)}"
        }, status_code=500)

@router.get("/status")
async def get_catalog_status(request: Request):
    """Get current catalog status from production sync tables"""
    try:
        async with get_session() as session:
            # Get real production data counts
            
            # Get total items from catalog_items table
            items_result = await session.execute(text("SELECT COUNT(*) FROM catalog_items WHERE is_deleted = false"))
            total_items = items_result.scalar()
            
            # Get total variations
            variations_result = await session.execute(text("SELECT COUNT(*) FROM catalog_variations WHERE is_deleted = false"))
            total_variations = variations_result.scalar()
            
            # Get total inventory records
            inventory_result = await session.execute(text("SELECT COUNT(*) FROM catalog_inventory"))
            total_inventory = inventory_result.scalar()
            
            # Get last sync time from the most recent updated_at across all tables
            last_sync_result = await session.execute(text("""
                SELECT MAX(last_updated) as last_sync FROM (
                    SELECT MAX(updated_at) as last_updated FROM catalog_items WHERE is_deleted = false
                    UNION ALL
                    SELECT MAX(updated_at) as last_updated FROM catalog_variations WHERE is_deleted = false
                    UNION ALL
                    SELECT MAX(updated_at) as last_updated FROM catalog_inventory
                    UNION ALL
                    SELECT MAX(updated_at) as last_updated FROM locations WHERE status = 'ACTIVE'
                ) as sync_times
            """))
            last_sync = last_sync_result.scalar()
            
            # Format last sync time in Central Time
            last_sync_iso = None
            last_sync_central = None
            if last_sync:
                # Ensure we have a UTC datetime
                if last_sync.tzinfo is None:
                    # Database stores timezone-naive UTC, so add UTC timezone
                    utc_sync = last_sync.replace(tzinfo=timezone.utc)
                else:
                    utc_sync = last_sync.astimezone(timezone.utc)
                
                # Convert to Central Time (handles daylight savings automatically)
                central_tz = pytz.timezone('US/Central')
                central_sync = utc_sync.astimezone(central_tz)
                
                # Format for API (ISO format)
                last_sync_iso = utc_sync.isoformat()
                
                # Format for display (Central Time)
                last_sync_central = central_sync.strftime('%Y-%m-%d %I:%M:%S %p %Z')
            
            # Determine if we have meaningful data
            has_data = total_items > 0 and total_variations > 0
            
            status_data = {
                'total_items': total_items,
                'total_variations': total_variations,
                'total_inventory': total_inventory,
                'last_export': last_sync_iso,  # Keep same field name for compatibility (UTC)
                'last_sync': last_sync_iso,    # UTC for API compatibility
                'last_sync_central': last_sync_central,  # Central Time for display
                'has_data': has_data
            }
        
        return JSONResponse({
            "success": True,
                "data": status_data
        })
        
    except Exception as e:
        logger.error(f"Error getting catalog status: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Failed to get status: {str(e)}"
        }, status_code=500)

@router.get("/status/component")
async def get_catalog_status_component(request: Request):
    """Get catalog status component for HTMX updates"""
    try:
        async with get_session() as session:
            catalog_service = SquareCatalogService()
            status = await catalog_service.get_export_status(session)
        
        return templates.TemplateResponse("catalog/components/status.html", {
            "request": request,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"Error getting catalog status component: {str(e)}", exc_info=True)
        return templates.TemplateResponse("catalog/components/error.html", {
            "request": request,
            "message": "Unable to load catalog status"
        })

@router.get("/export/status")
async def check_export_status(request: Request):
    """Check the status of the external export service"""
    try:
        catalog_service = SquareCatalogService()
        status = await catalog_service.check_export_status()
        
        return JSONResponse({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"Error checking export status: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Failed to check export status: {str(e)}"
        }, status_code=500)

@router.get("/api/health")
async def check_api_health():
    """Check if the external export API is running"""
    try:
        # Get the configured Square Catalog Export URL
        base_url = getattr(Config, 'SQUARE_CATALOG_EXPORT_URL', 'http://localhost:5001')
        
        # Support multiple URLs for different environments
        if base_url == 'http://localhost:5001':
            # Local development - try Docker-aware URLs
            api_urls = [
                "http://host.docker.internal:5001/health",
                "http://localhost:5001/health"
            ]
        else:
            # Production or custom URL - use the configured URL
            api_urls = [f"{base_url}/health"]
        
        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
        
        for api_url in api_urls:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(api_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            return JSONResponse({
                                "success": True,
                                "healthy": True,
                                "message": "API is healthy",
                                "data": data
                            })
                        else:
                            continue  # Try next URL
            except aiohttp.ClientConnectorError:
                continue  # Try next URL
            except asyncio.TimeoutError:
                continue  # Try next URL
        
        # If we get here, none of the URLs worked
        return JSONResponse({
            "success": True,
            "healthy": False,
            "message": "API is not running",
            "data": None
        })
        
    except Exception as e:
        logger.error(f"Error checking API health: {str(e)}")
        return JSONResponse({
            "success": False,
            "healthy": False,
            "message": f"Error checking API: {str(e)}",
            "data": None
        }, status_code=500)

@router.post("/api/start")
async def start_api_server():
    """Attempt to start the API server"""
    try:
        # For now, this will just return instructions
        # In a production environment, you might use subprocess or systemd
        return JSONResponse({
            "success": True,
            "message": "API server start command would be executed here",
            "instruction": "Please start the API server manually: python -m uvicorn main:app --port 5001"
        })
    except Exception as e:
        logger.error(f"Error starting API server: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Failed to start API server: {str(e)}"
        }, status_code=500)

@router.get("/export/excel")
async def export_to_excel():
    """Export the square_item_library_export table data to an Excel file"""
    try:
        logger.info("Starting Excel export of square_item_library_export table")
        
        async with get_session() as session:
            # Query all data from square_item_library_export table
            result = await session.execute(text("""
                SELECT 
                    reference_handle,
                    token,
                    item_name,
                    variation_name,
                    sku,
                    description,
                    categories,
                    reporting_category,
                    seo_title,
                    seo_description,
                    permalink,
                    gtin,
                    square_online_item_visibility,
                    item_type,
                    weight_lb,
                    social_media_link_title,
                    social_media_link_description,
                    shipping_enabled,
                    self_serve_ordering_enabled,
                    delivery_enabled,
                    pickup_enabled,
                    price,
                    online_sale_price,
                    archived,
                    sellable,
                    contains_alcohol,
                    stockable,
                    skip_detail_screen_in_pos,
                    option_name_1,
                    option_value_1,
                    default_unit_cost,
                    default_vendor_name,
                    default_vendor_code,
                    enabled_aubrey,
                    current_quantity_aubrey,
                    new_quantity_aubrey,
                    stock_alert_enabled_aubrey,
                    stock_alert_count_aubrey,
                    price_aubrey,
                    enabled_bridgefarmer,
                    current_quantity_bridgefarmer,
                    new_quantity_bridgefarmer,
                    stock_alert_enabled_bridgefarmer,
                    stock_alert_count_bridgefarmer,
                    price_bridgefarmer,
                    enabled_building,
                    current_quantity_building,
                    new_quantity_building,
                    stock_alert_enabled_building,
                    stock_alert_count_building,
                    price_building,
                    enabled_flomo,
                    current_quantity_flomo,
                    new_quantity_flomo,
                    stock_alert_enabled_flomo,
                    stock_alert_count_flomo,
                    price_flomo,
                    enabled_justin,
                    current_quantity_justin,
                    new_quantity_justin,
                    stock_alert_enabled_justin,
                    stock_alert_count_justin,
                    price_justin,
                    enabled_quinlan,
                    current_quantity_quinlan,
                    new_quantity_quinlan,
                    stock_alert_enabled_quinlan,
                    stock_alert_count_quinlan,
                    price_quinlan,
                    enabled_terrell,
                    current_quantity_terrell,
                    new_quantity_terrell,
                    stock_alert_enabled_terrell,
                    stock_alert_count_terrell,
                    price_terrell,
                    tax_sales_tax
                FROM square_item_library_export
                ORDER BY item_name, variation_name
            """))
            
            rows = result.fetchall()
            
            if not rows:
                return JSONResponse({
                    "success": False,
                    "message": "No data available to export. Please run a catalog export first."
                }, status_code=404)
            
            # Convert to DataFrame with exact column names matching Square's export
            df = pd.DataFrame(rows, columns=[
                'Reference Handle', 'Token', 'Item Name', 'Variation Name', 'SKU',
                'Description', 'Categories', 'Reporting Category', 'SEO Title', 'SEO Description',
                'Permalink', 'GTIN', 'Square Online Item Visibility', 'Item Type', 'Weight (lb)',
                'Social Media Link Title', 'Social Media Link Description', 'Shipping Enabled',
                'Self-serve Ordering Enabled', 'Delivery Enabled', 'Pickup Enabled', 'Price',
                'Online Sale Price', 'Archived', 'Sellable', 'Contains Alcohol', 'Stockable',
                'Skip Detail Screen in POS', 'Option Name 1', 'Option Value 1', 'Default Unit Cost',
                'Default Vendor Name', 'Default Vendor Code', 'Enabled Aubrey', 'Current Quantity Aubrey',
                'New Quantity Aubrey', 'Stock Alert Enabled Aubrey', 'Stock Alert Count Aubrey',
                'Price Aubrey', 'Enabled Bridgefarmer', 'Current Quantity Bridgefarmer',
                'New Quantity Bridgefarmer', 'Stock Alert Enabled Bridgefarmer', 'Stock Alert Count Bridgefarmer',
                'Price Bridgefarmer', 'Enabled Building', 'Current Quantity Building',
                'New Quantity Building', 'Stock Alert Enabled Building', 'Stock Alert Count Building',
                'Price Building', 'Enabled FloMo', 'Current Quantity FloMo', 'New Quantity FloMo',
                'Stock Alert Enabled FloMo', 'Stock Alert Count FloMo', 'Price FloMo', 'Enabled Justin',
                'Current Quantity Justin', 'New Quantity Justin', 'Stock Alert Enabled Justin',
                'Stock Alert Count Justin', 'Price Justin', 'Enabled Quinlan', 'Current Quantity Quinlan',
                'New Quantity Quinlan', 'Stock Alert Enabled Quinlan', 'Stock Alert Count Quinlan',
                'Price Quinlan', 'Enabled Terrell', 'Current Quantity Terrell', 'New Quantity Terrell',
                'Stock Alert Enabled Terrell', 'Stock Alert Count Terrell', 'Price Terrell',
                'Tax - Sales Tax (8.25%)'
            ])
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                # Write to Excel
                df.to_excel(tmp_file.name, index=False, engine='openpyxl')
                
                # Generate filename with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"square_catalog_export_{timestamp}.xlsx"
                
                logger.info(f"Excel export completed: {len(rows)} rows exported to {filename}")
                
                # Return file response
                return FileResponse(
                    path=tmp_file.name,
                    filename=filename,
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
    except Exception as e:
        logger.error(f"Error during Excel export: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Export failed: {str(e)}"
        }, status_code=500)