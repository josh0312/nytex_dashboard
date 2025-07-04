from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_session
from app.services.items_service import ItemsService
from app.logger import logger
from fastapi import HTTPException
from app.config import Config

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
                "total_items": len(items),
                "debug": Config.DEBUG
            }
            
            return templates.TemplateResponse("items/index_tabulator.html", context)
        
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
            "error": f"Unable to load items data: {str(e)}",
            "debug": Config.DEBUG
        }
        return templates.TemplateResponse("items/index_tabulator.html", context)

@router.get("/data", response_class=JSONResponse)
async def items_data(
    request: Request,
    page: int = Query(1, description="Page number"),
    size: int = Query(50, description="Page size"),
    sort: Optional[str] = Query(None, description="Column to sort by"),
    dir: str = Query("asc", description="Sort direction"),
    global_search: Optional[str] = Query(None, description="Global search term"),
    category: Optional[str] = Query(None, description="Category filter"),
    locations: Optional[str] = Query(None, description="Location filter (comma-separated)")
):
    """
    JSON API endpoint for Tabulator table data with server-side processing
    """
    try:
        # Get database session
        async with get_session() as session:
            # Debug: Log all query parameters
            query_params = dict(request.query_params)
            logger.info(f"Tabulator query parameters: {query_params}")
            
            # Parse Tabulator's sorting parameters if they exist
            # Tabulator sends sort as sort[0][field] and sort[0][dir]
            
            # Extract sort field and direction from Tabulator format
            sort_field = None
            sort_dir = "asc"
            
            # Check for Tabulator's sort parameter format
            for key, value in query_params.items():
                if 'sort[0][field]' in key:
                    sort_field = value
                elif 'sort[0][dir]' in key:
                    sort_dir = value
            
            # Fall back to simple sort parameter if Tabulator format not found
            if not sort_field and sort:
                sort_field = sort
                sort_dir = dir
            
            # Parse filters - handle both mobile filters and Tabulator filters
            filters = {}
            
            # Handle mobile category filter
            if category:
                filters['category'] = category
                logger.info(f"Mobile category filter applied: {category}")
            
            # Handle mobile locations filter
            if locations:
                # Parse comma-separated location names
                location_list = [loc.strip() for loc in locations.split(',') if loc.strip()]
                if location_list:
                    filters['locations'] = location_list
                    logger.info(f"Mobile locations filter applied: {location_list}")
            
            # Parse Tabulator's filter parameters
            # Tabulator sends filters as filter[0][field], filter[0][type], filter[0][value]
            # For multi-select, it sends filter[0][value][0], filter[0][value][1], etc.
            filter_groups = {}
            
            for key, value in query_params.items():
                if key.startswith('filter[') and '[' in key and ']' in key:
                    import re
                    # Parse filter[0][field], filter[0][type], filter[0][value], or filter[0][value][0]
                    match = re.match(r'filter\[(\d+)\]\[(\w+)\](?:\[(\d+)\])?', key)
                    if match:
                        filter_index = match.group(1)
                        filter_property = match.group(2)  # field, type, or value
                        array_index = match.group(3)  # for multi-select values
                        
                        if filter_index not in filter_groups:
                            filter_groups[filter_index] = {}
                        
                        if filter_property == 'value' and array_index is not None:
                            # Handle multi-select values as arrays
                            if 'value' not in filter_groups[filter_index]:
                                filter_groups[filter_index]['value'] = []
                            filter_groups[filter_index]['value'].append(value)
                        else:
                            # Handle single values
                            filter_groups[filter_index][filter_property] = value
            
            # Convert filter groups to the format expected by ItemsService
            for filter_index, filter_data in filter_groups.items():
                if 'field' in filter_data and 'value' in filter_data:
                    field_name = filter_data['field']
                    field_value = filter_data['value']
                    
                    # Skip empty values
                    if not field_value:
                        continue
                    
                    # Handle arrays (multi-select)
                    if isinstance(field_value, list):
                        # Filter out empty values
                        non_empty_values = [v for v in field_value if v and str(v).strip()]
                        if not non_empty_values:
                            continue
                        field_value = non_empty_values
                    elif isinstance(field_value, str):
                        # Skip empty strings
                        if not field_value.strip():
                            continue
                    
                    # Map Tabulator field names to our service field names
                    field_mapping = {
                        'category': 'category',
                        'vendor_name': 'vendor_name',
                        'item_name': 'item_name',
                        'sku': 'sku',
                        'description': 'description',
                        'vendor_code': 'vendor_code',
                        'price': 'price',
                        'cost': 'cost',
                        'locations': 'locations'
                    }
                    
                    mapped_field = field_mapping.get(field_name, field_name)
                    filters[mapped_field] = field_value
            
            logger.info(f"Parsed sort: field={sort_field}, dir={sort_dir}")
            logger.info(f"Parsed filters: {filters}")
            
            # Get items data with filters
            items = await ItemsService.get_items(
                session=session,
                sort=sort_field,
                direction=sort_dir,
                search=global_search,
                filters=filters
            )
            
            # Calculate pagination
            total_count = len(items)
            start_index = (page - 1) * size
            end_index = start_index + size
            page_items = items[start_index:end_index]
            
            # Format response for Tabulator
            response_data = {
                "data": page_items,
                "last_page": (total_count + size - 1) // size,
                "last_row": total_count
            }
            
            logger.info(f"Retrieved page {page} with {len(page_items)} items (total: {total_count}) with {len(filters)} filters applied")
            return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Error in items data API: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            content={"error": f"Unable to load items data: {str(e)}"}, 
            status_code=500
        )

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

@router.get("/export", response_class=JSONResponse)
async def export_items(
    request: Request,
    format: str = Query("xlsx", description="Export format: xlsx, csv, or json"),
    global_search: Optional[str] = Query(None, description="Global search term"),
    # Filter parameters
    filter: Optional[List[str]] = Query(None, description="Filter definitions"),
    sort: Optional[List[str]] = Query(None, description="Sort definitions")
):
    """
    Export items data in specified format with current filters
    """
    try:
        async with get_session() as session:
            logger.info(f"Export request - format: {format}")
            logger.info(f"Global search: {global_search}")
            logger.info(f"Filters: {filter}")
            logger.info(f"Sort: {sort}")
            
            # Process filters if provided
            filters = {}
            if filter:
                for filter_def in filter:
                    # Parse filter format: field:type:value
                    try:
                        if isinstance(filter_def, str):
                            # Handle both single string and potential parsing
                            logger.info(f"Processing filter: {filter_def}")
                            # For now, we'll handle this in a simple way
                            # This needs to be expanded based on actual filter format
                            pass
                    except Exception as e:
                        logger.warning(f"Could not parse filter: {filter_def}, error: {e}")
                        continue
            
            # Get all items (no pagination for export)
            items = await ItemsService.get_items(
                session=session,
                sort=None,  # We'll handle sorting separately if needed
                direction="asc",
                search=global_search,
                filters=filters
            )
            
            logger.info(f"Retrieved {len(items)} items for export")
            
            if format.lower() == "xlsx":
                return JSONResponse(content={
                    "data": items,
                    "total": len(items),
                    "format": "xlsx"
                })
            elif format.lower() == "csv":
                return JSONResponse(content={
                    "data": items,
                    "total": len(items),
                    "format": "csv"
                })
            elif format.lower() == "json":
                return JSONResponse(content={
                    "data": items,
                    "total": len(items),
                    "format": "json"
                })
            else:
                return JSONResponse(
                    content={"error": f"Unsupported format: {format}"}, 
                    status_code=400
                )
                
    except Exception as e:
        logger.error(f"Error in items export: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            content={"error": f"Unable to export items: {str(e)}"}, 
            status_code=500
        )

@router.get("/comparison", response_class=HTMLResponse)
async def items_comparison(request: Request):
    """
    Show comparison between old and new table implementations
    """
    try:
        # Get database session
        async with get_session() as session:
            # Get filter options for dropdowns
            filter_options = await ItemsService.get_filter_options(session)
            
            # Prepare context
            context = {
                "request": request,
                "filter_options": filter_options
            }
            
            return templates.TemplateResponse("items/comparison.html", context)
        
    except Exception as e:
        logger.error(f"Error in items comparison page: {str(e)}")
        
        # Return error page
        context = {
            "request": request,
            "filter_options": {"categories": [], "vendors": [], "item_types": []},
            "error": f"Unable to load comparison page: {str(e)}"
        }
        return templates.TemplateResponse("items/comparison.html", context)

@router.get("/test", response_class=HTMLResponse)
async def test_tabulator(request: Request):
    """
    Simple test page for Tabulator
    """
    return templates.TemplateResponse("items/test_tabulator.html", {"request": request})

@router.get("/simple", response_class=HTMLResponse)
async def simple_tabulator(request: Request):
    """
    Simple test page for Tabulator debugging
    """
    return templates.TemplateResponse("items/index_simple.html", {"request": request})

@router.get("/test-mobile", response_class=HTMLResponse)
async def test_mobile(request: Request):
    """
    Mobile test page for debugging column hiding
    """
    return templates.TemplateResponse("items/test_mobile.html", {"request": request})



@router.get("/details/{item_sku}", response_class=JSONResponse)
async def get_item_details(
    item_sku: str,
    request: Request
):
    """
    Get detailed item information for mobile slide panel
    """
    try:
        async with get_session() as session:
            # Get single item by SKU
            items = await ItemsService.get_items(
                session=session,
                search=item_sku,  # Search by SKU
                filters={}
            )
            
            # Find exact SKU match
            item = None
            for candidate in items:
                if candidate.get('sku') == item_sku:
                    item = candidate
                    break
            
            if not item:
                logger.warning(f"Item not found for SKU: {item_sku}")
                raise HTTPException(status_code=404, detail="Item not found")
            
            logger.info(f"Retrieved item details for SKU: {item_sku}")
            return JSONResponse(content=item)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching item details for SKU {item_sku}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Unable to fetch item details: {str(e)}"
        ) 