from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from app.services.reports.query_executor import QueryExecutor
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from pathlib import Path

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def reports_index(request: Request):
    """Render the reports landing page."""
    return templates.TemplateResponse(
        "reports/index.html",
        {"request": request}
    )

@router.get("/export/{query_name}")
async def export_report(query_name: str):
    """Export a report query to Excel."""
    try:
        executor = QueryExecutor()
        filename = await executor.export_query_to_excel(query_name)
        
        # Get the full path to the exported file
        exports_dir = os.path.join('app', 'static', 'exports')
        file_path = os.path.join(exports_dir, filename)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}") 

@router.get("/inventory/missing-sku", response_class=HTMLResponse)
async def missing_sku_report(
    request: Request,
    sort: str = None,
    direction: str = "asc"
):
    """Render the Missing SKU Report page."""
    try:
        # Define columns in one place - easy to modify
        columns = [
            {"key": "location", "label": "Location", "sortable": True},
            {"key": "item_name", "label": "Item Name", "sortable": True},
            {"key": "vendor_name", "label": "Vendor", "sortable": True},
            {"key": "sku", "label": "SKU", "sortable": True},
            {"key": "price", "label": "Price", "sortable": True},
            {"key": "category_name", "label": "Category", "sortable": True},
            {"key": "quantity", "label": "Quantity", "sortable": True},
        ]
        
        # Use QueryExecutor to run the query
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("missing_sku_inventory")
        
        # Apply sorting if requested and direction is not "none"
        if sort and sort in df.columns and direction != "none":
            ascending = direction.lower() == "asc"
            df = df.sort_values(by=sort, ascending=ascending)
        # If direction is "none", keep original order (no sorting)
        
        # Convert DataFrame to list of dicts
        items = df.to_dict('records')
        
        # Common template variables
        template_vars = {
            "request": request,
            "items": items,
            "columns": columns,  # Pass columns to template
            "sort": sort if direction != "none" else None,  # Clear sort when returning to original order
            "direction": direction
        }
        
        # If this is an HTMX request, return only the table
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "reports/inventory/missing_sku_table.html",
                template_vars
            )
        
        # Otherwise return the full page
        return templates.TemplateResponse(
            "reports/inventory/missing_sku.html",
            {
                **template_vars,
                "report_title": "Missing SKU Report",
                "total_items": len(items),
                "locations": sorted(set(item["location"] for item in items)),
                "categories": sorted(set(item["category_name"] for item in items if item["category_name"])),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Missing SKU Report: {str(e)}") 