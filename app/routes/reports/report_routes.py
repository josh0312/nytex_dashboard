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
async def missing_sku_report(request: Request):
    """Render the Missing SKU Report page."""
    try:
        # Use QueryExecutor to run the query
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("missing_sku_inventory")
        
        # Convert DataFrame to list of dicts
        items = df.to_dict('records')
        
        return templates.TemplateResponse(
            "reports/inventory/missing_sku.html",
            {
                "request": request,
                "items": items,
                "total_items": len(items),
                "locations": sorted(set(item["location"] for item in items)),
                "categories": sorted(set(item["category_name"] for item in items if item["category_name"])),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Missing SKU Report: {str(e)}") 