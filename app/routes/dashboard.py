from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.services.square_service import SquareService
from app.services.weather_service import WeatherService
from app.services.current_season import get_current_season
from app.services.season_service import SeasonService
from app.database import get_session
from app.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

async def get_cached_seasonal_sales():
    """Get cached seasonal sales data"""
    try:
        logger.info("Fetching fresh seasonal sales...")
        
        async with get_session() as session:
            logger.debug("Got database session")
            # Get current season
            current_season = await get_current_season()
            logger.debug(f"Got current season: {current_season}")
            
            if not current_season:
                logger.warning("No active season found")
                return None, None

            # Get seasonal sales
            season_service = SeasonService(session)
            logger.debug("Created season service")
            sales_data = await season_service.get_seasonal_sales(current_season)
            logger.debug(f"Got sales data: {bool(sales_data)}")
            return sales_data, current_season

    except Exception as e:
        logger.error(f"Error fetching seasonal sales: {str(e)}", exc_info=True)
        return None, None

@router.get("/")
async def index(request: Request):
    """Dashboard index page"""
    try:
        logger.info("Loading dashboard index page")
        sales_data, current_season = await get_cached_seasonal_sales()
        
        # Unpack sales data for template
        dates = []
        amounts = []
        transactions = []
        if sales_data:
            dates = [d.strftime('%b %d') for d in sales_data['dates']]
            amounts = sales_data['amounts']
            transactions = sales_data['transactions']
        
        return templates.TemplateResponse("dashboard/index.html", {
            "request": request,
            "sales_data": sales_data,
            "current_season": current_season,
            "dates": dates,
            "amounts": amounts,
            "transactions": transactions
        })
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/error.html", {
            "request": request,
            "title": "Dashboard",
            "message": "Unable to load dashboard"
        })

@router.get("/metrics")
async def get_metrics(request: Request):
    """Get metrics page"""
    try:
        logger.info("Loading metrics page")
        
        # Get fresh metrics from Square API
        logger.info("Fetching fresh metrics from Square API...")
        square_service = SquareService()
        metrics = await square_service.get_todays_sales()
        
        # Get seasonal sales
        sales_data, current_season = await get_cached_seasonal_sales()
        
        # Extract total sales from metrics
        total_sales = metrics.get('total_sales', 0) if metrics else 0
        total_orders = metrics.get('total_orders', 0) if metrics else 0
        
        # Get location sales
        location_sales = []
        for location_id, location in metrics.get('locations', {}).items():
            location_sales.append({
                'name': location['name'],
                'sales': location['sales'],
                'orders': location['orders']
            })
        
        # Unpack sales data for template
        dates = []
        amounts = []
        transactions = []
        if sales_data:
            dates = [d.strftime('%b %d') for d in sales_data['dates']]
            amounts = sales_data['amounts']
            transactions = sales_data['transactions']
        
        return templates.TemplateResponse("dashboard/metrics.html", {
            "request": request,
            "metrics": metrics,
            "sales_data": sales_data,
            "current_season": current_season,
            "total_sales": total_sales,
            "total_orders": total_orders,
            "dates": dates,
            "amounts": amounts,
            "transactions": transactions,
            "location_sales": location_sales
        })
    except Exception as e:
        logger.error(f"Error loading metrics: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/error.html", {
            "request": request,
            "title": "Metrics",
            "message": "Unable to load metrics"
        })

@router.get("/metrics/locations")
async def get_locations(request: Request):
    """Get location sales table"""
    try:
        square_service = SquareService()
        weather_service = WeatherService()
        metrics = await square_service.get_todays_sales()
        location_sales = []
        
        for location_id, location in metrics.get('locations', {}).items():
            # Get weather if postal code is available
            weather = None
            postal_code = location.get('postal_code')
            logger.info(f"Location {location['name']} has postal code: {postal_code}")
            
            if postal_code:
                weather = await weather_service.get_weather_by_zip(postal_code)
                logger.info(f"Got weather for {location['name']}: {weather}")
            else:
                logger.warning(f"No postal code for location: {location['name']}")
            
            location_sales.append({
                'name': location['name'],
                'sales': location['sales'],
                'orders': location['orders'],
                'weather': weather
            })
            
        return templates.TemplateResponse("dashboard/components/locations.html", {
            "request": request,
            "location_sales": location_sales
        })
    except Exception as e:
        logger.error(f"Error fetching locations: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Location Sales",
            "message": "Unable to load location sales"
        })

@router.get("/metrics/total_sales")
async def get_total_sales(request: Request):
    """Get total sales component"""
    try:
        logger.info("=== Starting total sales component fetch ===")
        logger.info("Creating Square service...")
        square_service = SquareService()
        logger.info("Getting today's sales...")
        metrics = await square_service.get_todays_sales()
        total_sales = metrics.get('total_sales', 0) if metrics else 0
        logger.info(f"Total sales: ${total_sales}")
        logger.info("Rendering total sales template...")
        
        return templates.TemplateResponse("dashboard/components/total_sales.html", {
            "request": request,
            "total_sales": total_sales
        })
    except Exception as e:
        logger.error(f"Error fetching total sales: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Total Sales",
            "message": "Unable to load total sales"
        }) 