from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.templates_config import templates
from app.logger import logger
from app.database import get_session
from app.config import Config
from sqlalchemy import text

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