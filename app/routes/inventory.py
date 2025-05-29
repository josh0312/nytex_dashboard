from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.services.square_inventory_service import SquareInventoryService
from app.logger import logger

router = APIRouter()

@router.post("/sync")
async def sync_inventory(request: Request, background_tasks: BackgroundTasks):
    """Trigger complete inventory and catalog sync from Square (includes inventory + Units Per Case)"""
    try:
        logger.info("Starting complete inventory and catalog sync via API")
        
        async with get_session() as session:
            inventory_service = SquareInventoryService()
            result = await inventory_service.fetch_inventory_from_square(session)
            
            # Explicitly commit the transaction if the sync was successful
            if result['success']:
                await session.commit()
        
        if result['success']:
            inventory_updated = result.get('total_inventory_updated', 0)
            catalog_updates = result.get('catalog_updates', {})
            
            items_updated = catalog_updates.get('items_updated', 0)
            variations_updated = catalog_updates.get('variations_updated', 0)
            items_with_units = catalog_updates.get('items_with_units', 0)
            variations_with_units = catalog_updates.get('variations_with_units', 0)
            
            total_catalog_updated = items_updated + variations_updated
            total_with_units = items_with_units + variations_with_units
            
            logger.info(f"Complete sync successful - Inventory: {inventory_updated} records, Catalog: {total_catalog_updated} updates, {total_with_units} with Units Per Case")
            
            return JSONResponse({
                "success": True,
                "message": f"Complete sync successful - {inventory_updated} inventory records, {total_catalog_updated} catalog updates, {total_with_units} items/variations with Units Per Case",
                "data": result
            })
        else:
            logger.error(f"Complete sync failed: {result.get('error', 'Unknown error')}")
            return JSONResponse({
                "success": False,
                "message": f"Sync failed: {result.get('error', 'Unknown error')}",
                "data": result
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error during complete sync: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"Sync failed: {str(e)}"
        }, status_code=500) 