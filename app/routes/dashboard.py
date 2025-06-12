from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.square_service import SquareService
from app.services.weather_service import WeatherService
from app.services.current_season import get_current_season
from app.services.season_service import SeasonService
from app.database.connection import get_db
from app.logger import logger
from app.templates_config import templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, func

router = APIRouter()

async def get_cached_seasonal_sales():
    """Get cached seasonal sales data"""
    try:
        logger.info("Fetching fresh seasonal sales...")
        
        async with get_db() as session:
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
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Dashboard",
            "message": "Unable to load dashboard"
        })

@router.get("/metrics")
async def get_metrics(request: Request):
    """Get metrics page"""
    try:
        logger.info("Loading metrics page")
        
        # Try to get metrics from Square API, but handle gracefully if not available
        metrics = None
        try:
            logger.info("Fetching fresh metrics from Square API...")
            square_service = SquareService()
            metrics = await square_service.get_todays_sales()
        except ValueError as e:
            logger.warning(f"Square API not configured: {str(e)}")
            # Return demo/mock data when Square API is not available
            metrics = {
                'total_sales': 0,
                'total_orders': 0,
                'inventory_items': 0,
                'low_stock_items': 0,
                'locations': {}
            }
        except Exception as e:
            logger.error(f"Error fetching Square metrics: {str(e)}")
            # Return demo/mock data on any other error
            metrics = {
                'total_sales': 0,
                'total_orders': 0,
                'inventory_items': 0,
                'low_stock_items': 0,
                'locations': {}
            }
        
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
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Metrics",
            "message": "Unable to load metrics"
        })

@router.get("/metrics/locations")
async def get_locations(request: Request):
    """Get location sales table"""
    try:
        # Try to get Square data but handle gracefully if not available
        location_sales = []
        try:
            square_service = SquareService()
            weather_service = WeatherService()
            metrics = await square_service.get_todays_sales()
            
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
        except ValueError as e:
            logger.warning(f"Square API not configured for locations: {str(e)}")
            # Return empty location sales when Square API is not available
            location_sales = []
        except Exception as e:
            logger.error(f"Error fetching Square location data: {str(e)}")
            # Return empty location sales on any other error
            location_sales = []
            
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
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request client: {request.client}")
        
        total_sales = 0
        try:
            logger.info("Creating Square service...")
            square_service = SquareService()
            
            logger.info("Initiating Square API call for today's sales...")
            metrics = await square_service.get_todays_sales()
            logger.info(f"Received metrics from Square: {bool(metrics)}")
            
            if metrics:
                total_sales = metrics.get('total_sales', 0)
                logger.info(f"Raw total sales value: {total_sales}")
        except ValueError as e:
            logger.warning(f"Square API not configured for total sales: {str(e)}")
            total_sales = 0
        except Exception as e:
            logger.error(f"Error fetching Square total sales: {str(e)}")
            total_sales = 0
        
        formatted_sales = "{:,.2f}".format(float(total_sales))
        logger.info(f"Formatted total sales value: ${formatted_sales}")
        
        logger.info("Preparing to render total sales template...")
        response = templates.TemplateResponse("dashboard/components/total_sales.html", {
            "request": request,
            "total_sales": formatted_sales
        })
        logger.info("Total sales template rendered successfully")
        logger.info(f"Response status: {response.status_code}")
        logger.info("=== Completed total sales component fetch ===")
        
        return response
    except Exception as e:
        logger.error(f"Error fetching total sales: {str(e)}", exc_info=True)
        logger.error("=== Failed total sales component fetch ===")
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Total Sales",
            "message": "Unable to load total sales"
        })

@router.get("/metrics/total_orders")
async def get_total_orders(request: Request):
    """Get total orders component"""
    try:
        total_orders = 0
        try:
            square_service = SquareService()
            metrics = await square_service.get_todays_sales()
            
            if metrics:
                total_orders = metrics.get('total_orders', 0)
        except ValueError as e:
            logger.warning(f"Square API not configured for total orders: {str(e)}")
            total_orders = 0
        except Exception as e:
            logger.error(f"Error fetching Square total orders: {str(e)}")
            total_orders = 0
        
        return templates.TemplateResponse("dashboard/components/total_orders.html", {
            "request": request,
            "total_orders": total_orders
        })
    except Exception as e:
        logger.error(f"Error loading total orders: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Total Orders",
            "message": "Unable to load total orders"
        })

@router.get("/metrics/annual_sales_comparison")
async def get_annual_sales_comparison(request: Request):
    """Get annual sales comparison data for the chart"""
    try:
        logger.info("=== ROUTE: Starting annual sales comparison request ===")
        async with get_db() as session:
            logger.info("=== ROUTE: Database session created successfully ===")
            season_service = SeasonService(session)
            logger.info("=== ROUTE: SeasonService instance created ===")
            logger.info("=== ROUTE: About to call get_yearly_season_totals ===")
            totals = await season_service.get_yearly_season_totals()
            logger.info("=== ROUTE: get_yearly_season_totals completed ===")
            logger.info(f"SeasonService returned totals: {totals is not None}, type: {type(totals)}")
            if totals:
                logger.info(f"Number of year entries: {len(totals)}")
                for i, year_data in enumerate(totals):
                    logger.info(f"Year {i}: {year_data.get('year', 'unknown')} with {len(year_data.get('seasons', []))} seasons")
            else:
                logger.warning("SeasonService returned None or empty data")
            
            return templates.TemplateResponse("dashboard/components/annual_sales_comparison.html", {
                "request": request,
                "season_totals": totals
            })
    except Exception as e:
        logger.error(f"Error fetching annual sales comparison: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Annual Sales Comparison",
            "message": "Unable to load annual sales comparison"
        })

@router.get("/metrics/annual_sales_comparison_simple")
async def get_annual_sales_comparison_simple(request: Request):
    """Get annual sales comparison using raw SQL that we know works"""
    try:
        logger.info("=== SIMPLE: Starting annual sales comparison request ===")
        async with get_db() as session:
            logger.info("=== SIMPLE: Database session created successfully ===")
            
            # Use the exact SQL query that worked in production
            raw_sql = """
                SELECT 
                    EXTRACT(year FROM operating_seasons.start_date) AS year, 
                    operating_seasons.name, 
                    operating_seasons.start_date, 
                    operating_seasons.end_date, 
                    count(orders.id) AS order_count, 
                    coalesce(sum(CAST(json_extract_path_text(orders.total_money, 'amount') AS INTEGER)), 0) AS total_amount
                FROM operating_seasons 
                LEFT OUTER JOIN orders ON 
                    CAST((orders.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= operating_seasons.start_date 
                    AND CAST((orders.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= operating_seasons.end_date 
                    AND orders.state != 'CANCELED'
                WHERE EXTRACT(year FROM operating_seasons.start_date) >= 2020 
                    AND EXTRACT(year FROM operating_seasons.start_date) <= 2025 
                GROUP BY EXTRACT(year FROM operating_seasons.start_date), operating_seasons.name, operating_seasons.start_date, operating_seasons.end_date 
                ORDER BY EXTRACT(year FROM operating_seasons.start_date) DESC, operating_seasons.start_date
            """
            
            logger.info("=== SIMPLE: Executing raw SQL query ===")
            result = await session.execute(text(raw_sql))
            seasons = result.all()
            logger.info(f"=== SIMPLE: Got {len(seasons)} seasons ===")
            
            # Group results by year (same logic as SeasonService but simpler)
            years_dict = {}
            for season in seasons:
                year = int(season.year)
                if year not in years_dict:
                    years_dict[year] = []
                
                years_dict[year].append({
                    'name': season.name,
                    'start_date': season.start_date.strftime('%Y-%m-%d'),
                    'end_date': season.end_date.strftime('%Y-%m-%d'),
                    'order_count': season.order_count,
                    'total_amount': float(season.total_amount) / 100  # Convert cents to dollars
                })
            
            # Convert to list and sort by year descending
            totals = [
                {
                    'year': year,
                    'seasons': seasons_list
                }
                for year, seasons_list in sorted(years_dict.items(), reverse=True)
            ]
            
            logger.info(f"=== SIMPLE: Returning {len(totals)} years of data ===")
            
            return templates.TemplateResponse("dashboard/components/annual_sales_comparison.html", {
                "request": request,
                "season_totals": totals
            })
    except Exception as e:
        logger.error(f"=== SIMPLE: Error in simple annual sales comparison: {str(e)} ===", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Annual Sales Comparison",
            "message": "Unable to load annual sales comparison"
        })

@router.get("/debug/find_correct_db")
async def find_correct_database(request: Request):
    """Debug endpoint to find which database has the proper tables"""
    databases_to_test = [
        "nytex_dashboard", 
        "square_data_sync"
    ]
    
    results = {}
    
    for db_name in databases_to_test:
        try:
            # Create connection string for this database
            db_uri = f"postgresql+asyncpg://nytex_user:@34.67.201.62:5432/{db_name}"
            engine = create_async_engine(db_uri, echo=False)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            
            async with async_session() as session:
                # Check tables
                tables_result = await session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """))
                tables = [row[0] for row in tables_result.fetchall()]
                
                # Check operating_seasons count if table exists
                operating_seasons_count = 0
                orders_count = 0
                
                if 'operating_seasons' in tables:
                    os_result = await session.execute(text("SELECT COUNT(*) FROM operating_seasons"))
                    operating_seasons_count = os_result.fetchone()[0]
                
                if 'orders' in tables:
                    orders_result = await session.execute(text("SELECT COUNT(*) FROM orders"))
                    orders_count = orders_result.fetchone()[0]
                
                results[db_name] = {
                    "status": "success",
                    "table_count": len(tables),
                    "tables": tables,
                    "operating_seasons_count": operating_seasons_count,
                    "orders_count": orders_count
                }
                
            await engine.dispose()
            
        except Exception as e:
            results[db_name] = {
                "status": "error",
                "error": str(e)
            }
    
    return results 

@router.get("/debug/test_models")
async def test_models(request: Request):
    """Test basic model querying in production"""
    try:
        async with get_db() as session:
            # Test OperatingSeason
            from app.database.models.operating_season import OperatingSeason
            seasons_query = await session.execute(select(func.count(OperatingSeason.id)))
            seasons_count = seasons_query.scalar()
            
            # Test Order 
            from app.database.models.order import Order
            orders_query = await session.execute(select(func.count(Order.id)))
            orders_count = orders_query.scalar()
            
            return {
                "status": "success",
                "operating_seasons_count": seasons_count,
                "orders_count": orders_count,
                "database_connected": True
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_connected": False
        }

@router.get("/debug/simple_count")
async def simple_count(request: Request):
    """Super simple test - just count operating seasons"""
    try:
        async with get_db() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM operating_seasons"))
            count = result.scalar()
            return {"status": "success", "operating_seasons_count": count}
    except Exception as e:
        return {"status": "error", "error": str(e)} 