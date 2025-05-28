from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from typing import Optional
from datetime import datetime
import logging
from sqlalchemy import text
from ...services.monitor_service import monitor, monitor_route
from ...database import get_session
from ...templates_config import templates
import os

router = APIRouter(tags=["inventory"])
logger = logging.getLogger(__name__)

# Load SQL queries
def load_sql_query(filename):
    """Load SQL query from file."""
    query_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'queries', filename)
    with open(query_path, 'r') as f:
        return f.read()

MISSING_SKU_QUERY = load_sql_query('missing_sku_inventory.sql')

@router.get("/test", response_class=PlainTextResponse)
@monitor_route
async def test():
    """Test endpoint for HTMX"""
    logger.info("Test endpoint called")
    return PlainTextResponse(
        "✓ HTMX is working correctly!", 
        headers={"HX-Trigger": "test-success"}
    )

@router.get("/missing-sku", response_class=HTMLResponse)
@monitor_route
async def missing_sku_report(
    request: Request,
    sort: Optional[str] = None,
    direction: Optional[str] = "asc",
    hx_request: Optional[str] = Header(None, alias="HX-Request")
):
    """Render the missing SKU report page."""
    logger.info(f"Loading missing SKU report with sort={sort}, direction={direction}, hx_request={hx_request}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    try:
        # Execute the query with sort parameters
        async with get_session() as session:
            result = await session.execute(
                text(MISSING_SKU_QUERY),
                {"sort": sort, "direction": direction}
            )
            items = result.mappings().all()
            total_items = len(items)
            logger.info(f"Query returned {total_items} items")
        
        # Prepare the context
        context = {
            "request": request,
            "total_items": total_items,
            "sort": sort,
            "direction": direction,
            "endpoint": "/reports/inventory/missing-sku",
            "items": items
        }
        
        # Log HTMX request if present
        if hx_request:
            monitor.log_htmx_event("missing-sku-refresh", {
                "sort": sort,
                "direction": direction,
                "is_htmx": True,
                "total_items": total_items
            })
            logger.info("HTMX request detected, returning rows template")
            return templates.TemplateResponse(
                "reports/inventory/missing_sku_rows.html",
                context
            )
        
        # Log regular page load
        monitor.log_htmx_event("missing-sku-load", {
            "sort": sort,
            "direction": direction,
            "is_htmx": False,
            "total_items": total_items
        })
        logger.info("Regular request, returning full page")
        return templates.TemplateResponse(
            "reports/inventory/missing_sku.html",
            context
        )
    except Exception as e:
        logger.error(f"Error in missing_sku_report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Comment out other endpoints for now until we fix the database queries
# We'll uncomment them once we verify HTMX is working 