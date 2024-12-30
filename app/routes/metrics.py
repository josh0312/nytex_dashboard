from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, extract, text
from datetime import datetime
from typing import Dict, List, Union
from ..database import get_session
from ..models.operating_season import OperatingSeason
from ..models.order import Order
from ..logger import logger
from ..routes.dashboard import get_cached_seasonal_sales
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/seasonal_sales")
async def get_seasonal_sales(request: Request):
    """Get seasonal sales data for the chart"""
    try:
        sales_data, current_season = await get_cached_seasonal_sales()
        
        if not sales_data or not current_season:
            return templates.TemplateResponse("dashboard/components/annual_sales.html", {
                "request": request,
                "sales_data": None,
                "current_season": None,
                "dates": [],
                "amounts": [],
                "transactions": []
            })
        
        # Format dates for display
        dates = [d.strftime('%b %d') for d in sales_data['dates']]
        amounts = sales_data['amounts']
        transactions = sales_data['transactions']
        
        return templates.TemplateResponse("dashboard/components/annual_sales.html", {
            "request": request,
            "sales_data": sales_data,
            "current_season": current_season,
            "dates": dates,
            "amounts": amounts,
            "transactions": transactions
        })
    except Exception as e:
        logger.error(f"Error fetching seasonal sales data: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Seasonal Sales",
            "message": "Unable to load seasonal sales"
        })

@router.get('/test/seasonal_sales')
async def test_seasonal_sales(request: Request):
    """Test endpoint for seasonal sales component"""
    try:
        sales_data, current_season = await get_cached_seasonal_sales()
        
        if sales_data:
            formatted_data = {
                "dates": [d.strftime('%Y-%m-%d') for d in sales_data['dates']],
                "amounts": sales_data['amounts'],
                "transactions": sales_data['transactions']
            }
        else:
            formatted_data = None
            
        return templates.TemplateResponse("dashboard/components/annual_sales.html", {
            "request": request,
            "sales_data": formatted_data,
            "current_season": current_season
        })
    except Exception as e:
        logger.error(f"Error in test seasonal sales: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Seasonal Sales",
            "message": "Unable to load seasonal sales"
        }) 