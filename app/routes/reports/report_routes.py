from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse, HTMLResponse
import os
from app.services.reports.query_executor import QueryExecutor
from app.services.reports.daily_sales_service import DailySalesService
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from pathlib import Path
from app.templates_config import templates
from app.logger import logger
from app.database import get_session
from datetime import datetime, date
import logging

router = APIRouter(tags=["reports"])

@router.get("/", response_class=HTMLResponse)
async def reports_index(request: Request):
    """Render the reports landing page."""
    return templates.TemplateResponse(
        "reports/index.html",
        {"request": request}
    )

@router.get("/export/{query_name}")
async def export_report(
    query_name: str, 
    format: str = Query("xlsx", description="Export format: xlsx or pdf"),
    sort: str = Query(None, description="Sort column"),
    direction: str = Query("asc", description="Sort direction: asc or desc")
):
    """Export a report query to Excel or PDF."""
    try:
        executor = QueryExecutor()
        
        # Prepare parameters for sorting
        params = {}
        if sort and direction and direction != "none":
            params['sort_column'] = sort
            params['sort_direction'] = direction
        
        # Export based on format
        if format.lower() == "pdf":
            filename = await executor.export_query_to_pdf(query_name, params)
            media_type = "application/pdf"
        else:  # Default to xlsx
            filename = await executor.export_query_to_excel(query_name, params)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Get the full path to the exported file
        exports_dir = os.path.join('app', 'static', 'exports')
        file_path = os.path.join(exports_dir, filename)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
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
                "report_name": "missing_sku_inventory",
                "total_items": len(items),
                "locations": sorted(set(item["location"] for item in items)),
                "categories": sorted(set(item["category_name"] for item in items if item["category_name"])),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Missing SKU Report: {str(e)}")

@router.get("/inventory/missing-category", response_class=HTMLResponse)
async def missing_category_report(
    request: Request,
    sort: str = None,
    direction: str = "asc"
):
    """Render the Missing Category Report page."""
    try:
        # Define columns in one place - easy to modify
        columns = [
            {"key": "item_name", "label": "Item Name", "sortable": True},
            {"key": "vendor_name", "label": "Vendor", "sortable": True},
            {"key": "price", "label": "Price", "sortable": True},
            {"key": "quantity", "label": "Quantity", "sortable": True},
            {"key": "category_status", "label": "Category Status", "sortable": True},
        ]
        
        # Use QueryExecutor to run the query
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("missing_category_inventory")
        
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
                "reports/inventory/missing_category_table.html",
                template_vars
            )
        
        # Otherwise return the full page
        return templates.TemplateResponse(
            "reports/inventory/missing_category.html",
            {
                **template_vars,
                "report_title": "Missing Category Report",
                "report_name": "missing_category_inventory",
                "total_items": len(items),
                "vendors": sorted(set(item["vendor_name"] for item in items if item["vendor_name"])),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Missing Category Report: {str(e)}")

@router.get("/inventory/missing-description", response_class=HTMLResponse)
async def missing_description_report(
    request: Request,
    sort: str = None,
    direction: str = "asc"
):
    """Render the Missing Description Report page."""
    try:
        # Define columns in one place - easy to modify
        columns = [
            {"key": "item_name", "label": "Item Name", "sortable": True},
            {"key": "vendor_name", "label": "Vendor", "sortable": True},
            {"key": "category_name", "label": "Category", "sortable": True},
            {"key": "price", "label": "Price", "sortable": True},
            {"key": "quantity", "label": "Quantity", "sortable": True},
        ]
        
        # Use QueryExecutor to run the query
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("missing_description_inventory")
        
        # Filter to only the columns we want to display (remove debugging columns)
        display_columns = [col["key"] for col in columns]
        df = df[display_columns]
        
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
                "reports/inventory/missing_description_table.html",
                template_vars
            )
        
        # Otherwise return the full page
        return templates.TemplateResponse(
            "reports/inventory/missing_description.html",
            {
                **template_vars,
                "report_title": "Missing Description Report",
                "report_name": "missing_description_inventory",
                "total_items": len(items),
                "vendors": sorted(set(item["vendor_name"] for item in items if item["vendor_name"])),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Missing Description Report: {str(e)}")

@router.get("/inventory/missing-vendor-info", response_class=HTMLResponse)
async def missing_vendor_info_report(
    request: Request,
    sort: str = None,
    direction: str = "asc"
):
    """Render the Missing Vendor Info Report page."""
    try:
        # Define columns in one place - easy to modify
        columns = [
            {"key": "item_name", "label": "Item Name", "sortable": True},
            {"key": "price", "label": "Price", "sortable": True},
            {"key": "vendor_name", "label": "Vendor", "sortable": True},
            {"key": "vendor_sku", "label": "Vendor Code", "sortable": True},
            {"key": "unit_cost", "label": "Unit Cost", "sortable": True},
        ]
        
        # Use QueryExecutor to run the query
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("missing_vendor_info_inventory")
        
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
                "reports/inventory/missing_vendor_info_table.html",
                template_vars
            )
        
        # Otherwise return the full page
        return templates.TemplateResponse(
            "reports/inventory/missing_vendor_info.html",
            {
                **template_vars,
                "report_title": "Missing Vendor Info Report",
                "report_name": "missing_vendor_info_inventory",
                "total_items": len(items),
                "vendors": sorted(set(item["vendor_name"] for item in items if item["vendor_name"] and item["vendor_name"] != "No Vendor")),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Missing Vendor Info Report: {str(e)}")

@router.get("/inventory/low-stock", response_class=HTMLResponse)
async def low_stock_report(
    request: Request, 
    view: str = "total",
    sort: str = None,
    direction: str = "asc"
):
    """Render the Low Item Stock Report page with toggle between total and location views."""
    try:
        # Define columns for different views
        total_columns = [
            {"key": "item_name", "label": "Item Name", "sortable": True},
            {"key": "vendor_name", "label": "Vendor", "sortable": True},
            {"key": "total_qty", "label": "Total Qty", "sortable": True},
            {"key": "units_per_case", "label": "Units/Case", "sortable": True},
            {"key": "case_percentage", "label": "Case %", "sortable": True},
            {"key": "low_stock_threshold", "label": "Low Item Stock Threshold", "sortable": True},
        ]
        
        location_columns = [
            {"key": "item_name", "label": "Item Name", "sortable": True},
            {"key": "vendor_name", "label": "Vendor", "sortable": True},
            {"key": "total_qty", "label": "Total Qty", "sortable": True},
            {"key": "units_per_case", "label": "Units/Case", "sortable": True},
            {"key": "aubrey_qty", "label": "Aubrey", "sortable": True},
            {"key": "bridgefarmer_qty", "label": "Bridgefarmer", "sortable": True},
            {"key": "building_qty", "label": "Building", "sortable": True},
            {"key": "flomo_qty", "label": "FloMo", "sortable": True},
            {"key": "justin_qty", "label": "Justin", "sortable": True},
            {"key": "quinlan_qty", "label": "Quinlan", "sortable": True},
            {"key": "terrell_qty", "label": "Terrell", "sortable": True},
        ]
        
        # Select columns based on view
        if view == "location":
            columns = location_columns
        else:
            columns = total_columns
        
        # Get the data
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("low_stock_inventory")
        
        # Apply sorting if requested and direction is not "none"
        if sort and sort in df.columns and direction != "none":
            ascending = direction.lower() == "asc"
            df = df.sort_values(by=sort, ascending=ascending)
        # If direction is "none", keep original order (no sorting)
        
        # Filter based on view
        if view == "location":
            # Show items that have low item stock at any location
            df = df[df['has_location_low_stock'] == True]
        else:
            # Show items that have low item stock in total inventory
            df = df[df['is_low_stock_total'] == True]
        
        # Convert to list of dictionaries for template
        items = df.to_dict('records') if not df.empty else []
        
        # Calculate statistics
        total_low_item_stock_items = len(items)
        
        # Get unique vendors
        vendors = df['vendor_name'].unique().tolist() if not df.empty else []
        
        # Calculate location statistics for location view
        location_stats = {}
        locations_with_issues = 0
        
        if view == "location" and not df.empty:
            # Get all location columns (those ending with '_low_stock')
            location_columns_in_df = [col for col in df.columns if col.endswith('_low_stock')]
            
            for col in location_columns_in_df:
                location = col.replace('_low_stock', '')
                low_item_stock_col = f"{location}_low_stock"
                if low_item_stock_col in df.columns:
                    count = int(df[low_item_stock_col].sum())
                    if count > 0:
                        location_stats[location] = count
                        locations_with_issues += 1
        
        # Calculate locations_with_issues for total view as well
        if view == "total" and not df.empty:
            location_columns_in_df = [col for col in df.columns if col.endswith('_low_stock')]
            for col in location_columns_in_df:
                if df[col].sum() > 0:
                    locations_with_issues += 1
        
        context = {
            "request": request,
            "report_title": "Low Item Stock Report",
            "report_name": "low_stock_inventory",
            "total_items": total_low_item_stock_items,
            "vendors": vendors,
            "location_stats": location_stats,
            "locations_with_issues": locations_with_issues,
            "view": view,
            "columns": columns,
            "items": items,
            "sort": sort if direction != "none" else None,
            "direction": direction,
        }
        
        # Return appropriate template based on request type
        if request.headers.get("HX-Request"):
            if request.headers.get("HX-Target") == "table-container":
                return templates.TemplateResponse(
                    "reports/inventory/low_stock_table.html",
                    context
                )
            else:
                return templates.TemplateResponse(
                    "reports/inventory/low_stock_content.html",
                    context
                )
        else:
            return templates.TemplateResponse(
                "reports/inventory/low_stock.html",
                context
            )
            
    except Exception as e:
        logger.error(f"Error in low_stock_report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load Low Item Stock Report: {str(e)}")

@router.get("/sales/daily", response_class=HTMLResponse)
async def daily_sales_report(
    request: Request,
    report_date: str = Query(None, description="Report date in YYYY-MM-DD format"),
    location_id: str = Query(None, description="Location ID or None for all locations")
):
    """Render the Daily Sales Report page."""
    try:
        # Parse report date or use today
        if report_date:
            try:
                parsed_date = datetime.strptime(report_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            from app.utils.timezone import get_central_now
            parsed_date = get_central_now().date()
        
        # Get the report data
        async with get_session() as session:
            daily_sales_service = DailySalesService(session)
            
            # Get the report data and available locations
            report_data = await daily_sales_service.get_daily_sales_report(parsed_date, location_id)
            available_locations = await daily_sales_service.get_available_locations()
        
        # Add location name for display
        selected_location_name = "All Locations"
        if location_id:
            for loc in available_locations:
                if loc['id'] == location_id:
                    selected_location_name = loc['name']
                    break
        
        # Common template variables
        template_vars = {
            "request": request,
            "report_data": report_data,
            "available_locations": available_locations,
            "selected_location_id": location_id,
            "selected_location_name": selected_location_name,
            "report_date": parsed_date,
            "report_title": f"Daily Sales Report - {parsed_date.strftime('%B %d, %Y')}",
        }
        
        # If this is an HTMX request, return only the content
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "reports/sales/daily_sales_content.html",
                template_vars
            )
        
        # Otherwise return the full page
        return templates.TemplateResponse(
            "reports/sales/daily_sales.html",
            template_vars
        )
        
    except Exception as e:
        logger.error(f"Error in daily_sales_report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load Daily Sales Report: {str(e)}") 