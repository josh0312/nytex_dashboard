from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_session
from app.services.items_service import ItemsService
from app.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def items_page(
    request: Request,
    sort: Optional[str] = Query(None, description="Column to sort by"),
    direction: str = Query("asc", description="Sort direction"),
    search: Optional[str] = Query(None, description="Global search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    item_type: Optional[str] = Query(None, description="Filter by item type")
):
    """
    Items page with comprehensive filtering, sorting, and search
    """
    try:
        # Get database session
        async with get_session() as session:
            # Build filters dictionary
            filters = {}
            if category:
                filters['category'] = category
            if vendor:
                filters['vendor_name'] = vendor
            if item_type:
                filters['item_type'] = item_type
            
            # Get items data
            items = await ItemsService.get_items(
                session=session,
                sort=sort,
                direction=direction,
                search=search,
                filters=filters
            )
            
            # Get filter options for dropdowns
            filter_options = await ItemsService.get_filter_options(session)
            
            # Prepare context
            context = {
                "request": request,
                "items": items,
                "filter_options": filter_options,
                "current_sort": sort,
                "current_direction": direction,
                "current_search": search or "",
                "current_filters": {
                    "category": category or "",
                    "vendor": vendor or "",
                    "item_type": item_type or ""
                },
                "total_items": len(items)
            }
            
            return templates.TemplateResponse("items/index.html", context)
        
    except Exception as e:
        logger.error(f"Error in items page: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return error page or basic template
        context = {
            "request": request,
            "items": [],
            "filter_options": {"categories": [], "vendors": [], "item_types": []},
            "current_sort": sort,
            "current_direction": direction,
            "current_search": search or "",
            "current_filters": {
                "category": category or "",
                "vendor": vendor or "",
                "item_type": item_type or ""
            },
            "total_items": 0,
            "error": f"Unable to load items data: {str(e)}"
        }
        return templates.TemplateResponse("items/index.html", context)

@router.get("/table", response_class=HTMLResponse)
async def items_table(
    request: Request,
    sort: Optional[str] = Query(None),
    direction: str = Query("asc"),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None)
):
    """
    HTMX endpoint for table updates (sorting, filtering, searching)
    """
    try:
        # Get database session
        async with get_session() as session:
            # Build filters dictionary
            filters = {}
            if category:
                filters['category'] = category
            if vendor:
                filters['vendor_name'] = vendor
            if item_type:
                filters['item_type'] = item_type
            
            # Get items data
            items = await ItemsService.get_items(
                session=session,
                sort=sort,
                direction=direction,
                search=search,
                filters=filters
            )
            
            # Prepare context for table partial
            context = {
                "request": request,
                "items": items,
                "current_sort": sort,
                "current_direction": direction,
                "total_items": len(items)
            }
            
            return templates.TemplateResponse("items/table.html", context)
        
    except Exception as e:
        logger.error(f"Error in items table: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        context = {
            "request": request,
            "items": [],
            "current_sort": sort,
            "current_direction": direction,
            "total_items": 0,
            "error": f"Unable to load items data: {str(e)}"
        }
        return templates.TemplateResponse("items/table.html", context) 