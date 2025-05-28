from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from app.services.square_catalog_service import SquareCatalogService
from app.database import get_session
from app.logger import logger
from app.templates_config import templates
import aiohttp
import asyncio

router = APIRouter(prefix="/catalog", tags=["catalog"])

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
    """Get current catalog export status"""
    try:
        async with get_session() as session:
            catalog_service = SquareCatalogService()
            status = await catalog_service.get_export_status(session)
        
        return JSONResponse({
            "success": True,
            "data": status
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
        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("http://localhost:5001/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return JSONResponse({
                        "success": True,
                        "healthy": True,
                        "message": "API is healthy",
                        "data": data
                    })
                else:
                    return JSONResponse({
                        "success": True,
                        "healthy": False,
                        "message": f"API returned status {response.status}",
                        "data": None
                    })
    except aiohttp.ClientConnectorError:
        return JSONResponse({
            "success": True,
            "healthy": False,
            "message": "API is not running",
            "data": None
        })
    except asyncio.TimeoutError:
        return JSONResponse({
            "success": True,
            "healthy": False,
            "message": "API request timed out",
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