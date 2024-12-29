from flask import Blueprint, render_template, jsonify, g
from app.services.square_service import SquareService
from app.services.season_service import SeasonService
from app.services.current_season import get_current_season
from app.database import get_session
from app.logger import logger
import asyncio

dashboard = Blueprint('dashboard', __name__)

async def get_cached_metrics():
    """Get or create cached metrics"""
    if not hasattr(g, 'metrics_cache'):
        logger.info("Fetching fresh metrics from Square API...")
        square = SquareService()
        g.metrics_cache = await square.get_todays_sales()
    return g.metrics_cache

async def get_cached_seasonal_sales():
    """Get or create cached seasonal sales"""
    if not hasattr(g, 'seasonal_sales_cache'):
        logger.info("Fetching fresh seasonal sales...")
        current_season = await get_current_season()
        if current_season:
            try:
                async with get_session() as session:
                    season_service = SeasonService(session)
                    g.seasonal_sales_cache = await season_service.get_seasonal_sales(current_season)
                    g.current_season = current_season
            except Exception as e:
                logger.error(f"Error fetching seasonal sales: {str(e)}", exc_info=True)
                g.seasonal_sales_cache = None
                g.current_season = None
        else:
            g.seasonal_sales_cache = None
            g.current_season = None
    return g.seasonal_sales_cache, g.current_season

@dashboard.route('/')
async def index():
    """Render the dashboard index page"""
    logger.info("Loading dashboard index page")
    seasonal_sales, current_season = await get_cached_seasonal_sales()
    return render_template('dashboard/index.html', sales_data=seasonal_sales, current_season=current_season)

@dashboard.route('/metrics')
async def get_metrics():
    """Get metrics for the dashboard"""
    logger.info("Loading metrics page")
    try:
        # Get metrics with error handling
        metrics = await get_cached_metrics()
        if not metrics:
            metrics = {
                'total_sales': 0,
                'total_orders': 0,
                'low_stock_items': 0,
                'locations': {}
            }
            
        # Get seasonal sales with error handling
        sales_data, current_season = await get_cached_seasonal_sales()
        
        # Format seasonal data if available
        if sales_data and current_season:
            dates = [day.strftime('%d') for day in sales_data['dates']]
            amounts = [float(amount) if amount > 0 else None for amount in sales_data['amounts']]
            transactions = sales_data['transactions']
        else:
            dates, amounts, transactions = [], [], []
            
        # Format location data
        location_sales = []
        for location_id, location in metrics.get('locations', {}).items():
            location_sales.append({
                'name': location['name'],
                'sales': location['sales'],
                'orders': location['orders'],
                'status': 'Open'
            })
        
        # Render all components at once
        return render_template('dashboard/metrics.html',
                             total_sales=metrics['total_sales'],
                             total_orders=metrics['total_orders'],
                             low_stock_items=metrics['low_stock_items'],
                             location_sales=location_sales,
                             current_season=current_season,
                             sales_data=bool(sales_data),
                             dates=dates,
                             amounts=amounts,
                             transactions=transactions)
                             
    except Exception as e:
        logger.error(f"Error loading metrics: {str(e)}", exc_info=True)
        return render_template('dashboard/metrics.html',
                             total_sales=0,
                             total_orders=0,
                             low_stock_items=0,
                             location_sales=[],
                             current_season=None,
                             sales_data=False,
                             dates=[],
                             amounts=[],
                             transactions=[])

@dashboard.route('/metrics/locations')
async def get_locations():
    """Get location sales table"""
    try:
        metrics = await get_cached_metrics()
        location_sales = []
        for location_id, location in metrics.get('locations', {}).items():
            location_sales.append({
                'name': location['name'],
                'sales': location['sales'],
                'orders': location['orders'],
                'status': 'Open'
            })
            
        return render_template('dashboard/components/locations.html',
                             location_sales=location_sales)
    except Exception as e:
        logger.error(f"Error fetching locations: {str(e)}", exc_info=True)
        return render_template('dashboard/components/error.html',
                             title="Location Sales",
                             message="Unable to load location sales") 