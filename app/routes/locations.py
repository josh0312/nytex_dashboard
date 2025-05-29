from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.services.square_location_service import SquareLocationService
from app.logger import logger

router = APIRouter()

@router.post("/sync")
async def sync_locations(request: Request, background_tasks: BackgroundTasks):
    """Trigger location sync from Square"""
    try:
        logger.info("Starting locations sync via API")
        
        async with get_session() as session:
            location_service = SquareLocationService()
            result = await location_service.fetch_locations_from_square(session)
        
        if result['success']:
            locations_created = result.get('locations_created', 0)
            locations_updated = result.get('locations_updated', 0)
            total_locations = result.get('total_locations', 0)
            
            logger.info(f"Location sync successful - Created: {locations_created}, Updated: {locations_updated}, Total: {total_locations}")
            
            return JSONResponse({
                "success": True,
                "message": f"Location sync successful - Created: {locations_created}, Updated: {locations_updated}, Total: {total_locations}",
                "data": result
            })
        else:
            logger.error(f"Location sync failed: {result.get('error', 'Unknown error')}")
            return JSONResponse({
                "success": False,
                "message": f"Location sync failed: {result.get('error', 'Unknown error')}",
                "data": result
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error during location sync: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Location sync failed: {str(e)}"
        }, status_code=500)

@router.get("/status")
async def location_status():
    """Get current location status"""
    try:
        async with get_session() as session:
            location_service = SquareLocationService()
            result = await location_service.get_locations_status(session)
            
        return JSONResponse({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error getting location status: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500) 