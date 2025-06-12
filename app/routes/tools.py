from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates_config import templates
from app.services.square_catalog_service import SquareCatalogService
from app.database import get_session
from app.logger import logger
from sqlalchemy import text
from datetime import datetime, timezone

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def tools_index(request: Request):
    """Tools index page"""
    return templates.TemplateResponse("tools/index.html", {"request": request})

@router.get("/square-catalog-export", response_class=HTMLResponse)
async def square_catalog_export_tool(request: Request):
    """Square Catalog Export tool page"""
    try:
        logger.info("Loading Square Catalog Export tool page")
        
        # Get current export status
        async with get_session() as session:
            catalog_service = SquareCatalogService()
            status = await catalog_service.get_export_status(session)
        
        return templates.TemplateResponse("tools/square_catalog_export.html", {
            "request": request,
            "status": status
        })
    except Exception as e:
        logger.error(f"Error loading Square Catalog Export tool page: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/error.html", {
            "request": request,
            "title": "Square Catalog Export",
            "message": "Unable to load Square Catalog Export tool page"
        })

async def get_inventory_status_direct(session):
    """Get inventory status using direct database queries"""
    try:
        # Get total inventory records
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM catalog_inventory")
        )
        total_records = count_result.scalar()
        
        # Get latest update time
        latest_result = await session.execute(
            text("SELECT MAX(updated_at) FROM catalog_inventory")
        )
        latest_update = latest_result.scalar()
        
        # Get inventory by location
        location_result = await session.execute(
            text("""
                SELECT l.name, COUNT(ci.id) as item_count, SUM(ci.quantity) as total_qty
                FROM catalog_inventory ci
                JOIN locations l ON ci.location_id = l.id
                WHERE l.status = 'ACTIVE'
                GROUP BY l.name
                ORDER BY l.name
            """)
        )
        location_stats = [
            {
                'location': row[0],
                'item_count': row[1],
                'total_quantity': row[2]
            }
            for row in location_result.fetchall()
        ]
        
        # Format last update time
        last_update_iso = None
        if latest_update:
            if latest_update.tzinfo is None:
                # Database stores timezone-naive UTC, so add UTC timezone for display
                utc_update = latest_update.replace(tzinfo=timezone.utc)
            else:
                utc_update = latest_update.astimezone(timezone.utc)
            last_update_iso = utc_update.isoformat()
        
        return {
            'total_records': total_records,
            'last_update': last_update_iso,
            'has_data': total_records > 0,
            'location_stats': location_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting inventory status: {str(e)}")
        return {
            'total_records': 0,
            'last_update': None,
            'has_data': False,
            'location_stats': [],
            'error': str(e)
        }

@router.get("/square-inventory-update", response_class=HTMLResponse)
async def square_inventory_update_tool(request: Request):
    """Square Inventory Update tool page"""
    try:
        logger.info("Loading Square Inventory Update tool page")
        
        # Get current inventory status
        async with get_session() as session:
            status = await get_inventory_status_direct(session)
        
        return templates.TemplateResponse("tools/square_inventory_update.html", {
            "request": request,
            "status": status
        })
    except Exception as e:
        logger.error(f"Error loading Square Inventory Update tool page: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/error.html", {
            "request": request,
            "title": "Square Inventory Update",
            "message": "Unable to load Square Inventory Update tool page"
        })

@router.post("/square-inventory-update/start")
async def start_inventory_update(request: Request):
    """Start the Square inventory update process using complete sync"""
    try:
        logger.info("Starting Square inventory update via complete sync")
        
        # Use the complete sync endpoint for inventory updates
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/admin/complete-sync",
                json={"full_refresh": False},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return JSONResponse({
                        "success": True,
                        "message": "Inventory update completed via complete sync",
                        "data": result
                    })
                else:
                    error_text = await response.text()
                    return JSONResponse({
                        "success": False,
                        "message": f"Complete sync failed: {error_text}"
                    }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error starting inventory update: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Failed to start inventory update: {str(e)}"
        }, status_code=500)

@router.get("/square-inventory-update/status")
async def get_inventory_update_status(request: Request):
    """Get current inventory update status"""
    try:
        async with get_session() as session:
            status = await get_inventory_status_direct(session)
        
        return JSONResponse({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        logger.error(f"Error getting inventory status: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Failed to get status: {str(e)}"
        }, status_code=500)

@router.get("/square-inventory-update/status/component")
async def get_inventory_status_component(request: Request):
    """Get inventory status component for HTMX updates"""
    try:
        async with get_session() as session:
            status = await get_inventory_status_direct(session)
        
        return templates.TemplateResponse("tools/components/inventory_status.html", {
            "request": request,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"Error getting inventory status component: {str(e)}", exc_info=True)
        return templates.TemplateResponse("tools/components/error.html", {
            "request": request,
            "message": "Unable to load inventory status"
        })

@router.get("/catalog-export", response_class=HTMLResponse)
async def catalog_export_tool(request: Request):
    """Catalog Export tool page - redirect to square-catalog-export"""
    # Redirect old route to new route for backward compatibility
    return templates.TemplateResponse("tools/square_catalog_export.html", {"request": request})
