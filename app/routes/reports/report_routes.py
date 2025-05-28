from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse, HTMLResponse
import os
from app.services.reports.query_executor import QueryExecutor
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from pathlib import Path
from app.templates_config import templates
import logging

router = APIRouter(prefix="/reports", tags=["reports"])

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
    sort: str = None,
    direction: str = "asc",
    view: str = Query("total", description="View type: total or location")
):
    """Render the Low Stock Report page with toggle between total and location views."""
    try:
        # Define columns based on view type
        if view == "location":
            columns = [
                {"key": "item_name", "label": "Item Name", "sortable": True},
                {"key": "sku", "label": "SKU", "sortable": True},
                {"key": "vendor_name", "label": "Vendor", "sortable": True},
                {"key": "units_per_case", "label": "Units/Case", "sortable": True},
                {"key": "low_stock_threshold", "label": "Low Stock Threshold", "sortable": True},
                {"key": "aubrey_qty", "label": "Aubrey", "sortable": True, "type": "location"},
                {"key": "bridgefarmer_qty", "label": "Bridgefarmer", "sortable": True, "type": "location"},
                {"key": "building_qty", "label": "Building", "sortable": True, "type": "location"},
                {"key": "flomo_qty", "label": "FloMo", "sortable": True, "type": "location"},
                {"key": "justin_qty", "label": "Justin", "sortable": True, "type": "location"},
                {"key": "quinlan_qty", "label": "Quinlan", "sortable": True, "type": "location"},
                {"key": "terrell_qty", "label": "Terrell", "sortable": True, "type": "location"},
                {"key": "locations_with_low_stock", "label": "Low Stock Locations", "sortable": True},
            ]
        else:  # total view
            columns = [
                {"key": "item_name", "label": "Item Name", "sortable": True},
                {"key": "sku", "label": "SKU", "sortable": True},
                {"key": "vendor_name", "label": "Vendor", "sortable": True},
                {"key": "units_per_case", "label": "Units/Case", "sortable": True},
                {"key": "low_stock_threshold", "label": "Low Stock Threshold", "sortable": True},
                {"key": "total_qty", "label": "Total Quantity", "sortable": True},
                {"key": "case_percentage", "label": "% of Case", "sortable": True},
                {"key": "price", "label": "Price", "sortable": True},
                {"key": "cost", "label": "Cost", "sortable": True},
            ]
        
        # Use QueryExecutor to run the query
        executor = QueryExecutor()
        df = await executor.execute_query_to_df("low_stock_inventory")
        
        # Filter data based on view type
        if view == "location":
            # Show items that have low stock at any location
            df = df[df['has_location_low_stock'] == True]
        else:
            # Show items that have low stock in total inventory
            df = df[df['is_low_stock_total'] == True]
        
        # Apply sorting if requested and direction is not "none"
        if sort and sort in df.columns and direction != "none":
            ascending = direction.lower() == "asc"
            df = df.sort_values(by=sort, ascending=ascending)
        # If direction is "none", keep original order (no sorting)
        
        # Convert DataFrame to list of dicts
        items = df.to_dict('records')
        
        # Calculate statistics for the full page
        total_low_stock_items = len(items)
        
        # Convert generator to list to avoid potential recursion issues
        unique_vendors = []
        for item in items:
            if item.get("vendor_name"):
                unique_vendors.append(item["vendor_name"])
        unique_vendors = sorted(set(unique_vendors))
        
        if view == "location":
            # Calculate location statistics (but do it in Python, not template)
            location_stats = {}
            locations_with_issues = 0
            locations = ['aubrey', 'bridgefarmer', 'building', 'flomo', 'justin', 'quinlan', 'terrell']
            for location in locations:
                low_stock_col = f"{location}_low_stock"
                if low_stock_col in df.columns:
                    count = int(df[low_stock_col].sum())
                    location_stats[location.title()] = count
                    if count > 0:
                        locations_with_issues += 1
                else:
                    location_stats[location.title()] = 0
        else:
            location_stats = {}
            locations_with_issues = 0
        
        # Common template variables
        template_vars = {
            "request": request,
            "items": items,
            "columns": columns,
            "sort": sort if direction != "none" else None,
            "direction": direction,
            "view": view,
            "report_title": "Low Stock Report",
            "report_name": "low_stock_inventory",
            "total_items": total_low_stock_items,
            "vendors": unique_vendors,
            "location_stats": location_stats,
            "locations_with_issues": locations_with_issues,
            "view_type": "NyTex Inventory" if view == "total" else "Location Inventory"
        }
        
        # If this is an HTMX request, determine the type of request
        if request.headers.get("HX-Request"):
            # Check if this is a toggle request (has view parameter but no sort)
            if not sort:
                # Toggle request - return full content with header and statistics
                return templates.TemplateResponse(
                    "reports/inventory/low_stock_content.html",
                    template_vars
                )
            else:
                # Sorting request - return only the table
                return templates.TemplateResponse(
                    "reports/inventory/low_stock_table.html",
                    template_vars
                )
        
        # Return the template with test template for now
        return templates.TemplateResponse(
            "reports/inventory/low_stock.html",
            template_vars
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Low Stock Report: {str(e)}") 