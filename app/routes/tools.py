from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from app.services.square_catalog_service import SquareCatalogService
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

@router.get("/catalog-export", response_class=HTMLResponse)
async def catalog_export_tool(request: Request):
    """Catalog Export tool page - redirect to square-catalog-export"""
    # Redirect old route to new route for backward compatibility
    return templates.TemplateResponse("tools/square_catalog_export.html", {"request": request})
