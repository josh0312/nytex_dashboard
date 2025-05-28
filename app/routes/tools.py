from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates_config import templates
from app.services.square_catalog_service import SquareCatalogService
from app.services.square_inventory_service import SquareInventoryService
from app.database import get_session
from app.logger import logger

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

@router.get("/square-inventory-update", response_class=HTMLResponse)
async def square_inventory_update_tool(request: Request):
    """Square Inventory Update tool page"""
    try:
        logger.info("Loading Square Inventory Update tool page")
        
        # Get current inventory status
        async with get_session() as session:
            inventory_service = SquareInventoryService()
            status = await inventory_service.get_inventory_status(session)
        
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
    """Start the Square inventory update process"""
    try:
        logger.info("Starting Square inventory update")
        
        async with get_session() as session:
            inventory_service = SquareInventoryService()
            result = await inventory_service.fetch_inventory_from_square(session)
        
        return JSONResponse(result)
        
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
            inventory_service = SquareInventoryService()
            status = await inventory_service.get_inventory_status(session)
        
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
            inventory_service = SquareInventoryService()
            status = await inventory_service.get_inventory_status(session)
        
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
