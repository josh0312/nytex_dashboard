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
from datetime import datetime, timedelta
from app.utils.timezone import get_central_now

router = APIRouter()

async def get_cached_seasonal_sales():
    """Get cached seasonal sales data"""
    try:
        logger.info("Fetching fresh seasonal sales...")
        
        # Get current season first
        current_season_data = await get_current_season()
        logger.debug(f"Got current season data: {current_season_data}")
        
        if not current_season_data:
            logger.warning("No active season found")
            return None, None

        season_name = current_season_data.get('name') if current_season_data else None
        if not season_name:
            logger.warning("No season name found in season data")
            return None, None

        # Get seasonal sales with a fresh session
        async with get_db() as session:
            logger.debug("Got database session")
            season_service = SeasonService(session)
            logger.debug("Created season service")
            sales_data = await season_service.get_seasonal_sales(current_season_data)
            logger.debug(f"Got sales data: {bool(sales_data)}")
            # Return sales data and the full season object (not just the name)
            return sales_data, current_season_data

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

@router.get("/metrics/seasonal_sales")
async def get_seasonal_sales_component(request: Request):
    """Get seasonal sales component"""
    try:
        logger.info("Loading seasonal sales component")
        
        # Get seasonal sales data
        sales_data, current_season = await get_cached_seasonal_sales()
        
        # Unpack sales data for template
        dates = []
        amounts = []
        transactions = []
        if sales_data:
            dates = [d.strftime('%b %d') for d in sales_data['dates']]
            amounts = sales_data['amounts']
            transactions = sales_data['transactions']
        
        return templates.TemplateResponse("dashboard/components/seasonal_sales.html", {
            "request": request,
            "sales_data": sales_data,
            "current_season": current_season,
            "dates": dates,
            "amounts": amounts,
            "transactions": transactions
        })
    except Exception as e:
        logger.error(f"Error loading seasonal sales component: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Seasonal Sales",
            "message": "Unable to load seasonal sales"
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

@router.get("/metrics/weather_summary")
async def get_weather_summary(request: Request):
    """Get weather summary for dashboard"""
    try:
        from app.services.weather_service import WeatherService
        from app.services.location_service import LocationService
        
        location_service = LocationService()
        weather_service = WeatherService()
        
        # Get all locations
        locations = await location_service.get_all_locations()
        
        # Get weather stats
        weather_stats = {
            'rain_count': 0,
            'clear_count': 0,
            'avg_temp': 0,
            'data_coverage': 0,
            'total_locations': len(locations)
        }
        
        temps = []
        weather_data_count = 0
        
        for location in locations:
            if location.get('address') and location['address'].get('postal_code'):
                try:
                    weather = await weather_service.get_weather_by_zip(location['address']['postal_code'])
                    if weather:
                        weather_data_count += 1
                        
                        # Check for rain/precipitation
                        weather_main = weather.get('weather', {}).get('main', '').lower()
                        if 'rain' in weather_main or 'drizzle' in weather_main or 'thunderstorm' in weather_main:
                            weather_stats['rain_count'] += 1
                        elif 'clear' in weather_main or 'sun' in weather_main:
                            weather_stats['clear_count'] += 1
                        
                        # Collect temperature
                        if weather.get('main') and weather['main'].get('temp'):
                            temps.append(weather['main']['temp'])
                            
                except Exception as e:
                    logger.warning(f"Could not get weather for location {location['name']}: {str(e)}")
        
        # Calculate averages
        if temps:
            weather_stats['avg_temp'] = sum(temps) / len(temps)
        
        if locations:
            weather_stats['data_coverage'] = round((weather_data_count / len(locations)) * 100)
        
        return templates.TemplateResponse("dashboard/components/weather_summary.html", {
            "request": request,
            "weather_stats": weather_stats
        })
    except Exception as e:
        logger.error(f"Error fetching weather summary: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Weather Summary",
            "message": "Unable to load weather summary"
        })

@router.get("/metrics/locations_overview")
async def get_locations_overview(request: Request):
    """Get locations overview for dashboard"""
    try:
        from app.services.location_service import LocationService
        
        location_service = LocationService()
        locations = await location_service.get_all_locations()
        
        return templates.TemplateResponse("dashboard/components/dashboard_locations.html", {
            "request": request,
            "locations": locations
        })
    except Exception as e:
        logger.error(f"Error fetching locations overview: {str(e)}", exc_info=True)
        return templates.TemplateResponse("dashboard/components/error.html", {
            "request": request,
            "title": "Locations Overview",
            "message": "Unable to load locations overview"
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

async def get_location_comprehensive_comparison(location_id: str, current_data: dict) -> dict:
    """Get comprehensive year-over-year comparison for location's metrics"""
    try:
        from app.utils.timezone import get_central_now
        from app.services.current_season import get_current_season
        
        # Get current date and season info
        current_central = get_central_now()
        current_date = current_central.date()
        last_year_date = current_date.replace(year=current_date.year - 1)
        current_season_data = await get_current_season()
        current_season = current_season_data.get('name') if current_season_data else None
        
        async with get_db() as session:
            comparisons = {}
            
            # 1. TODAY vs SAME DATE LAST YEAR
            today_query = """
                SELECT 
                    COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as last_year_orders,
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as last_year_sales_cents
                FROM orders o
                WHERE o.location_id = :location_id
                AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) = :last_year_date
                AND o.state = 'COMPLETED'
            """
            
            result = await session.execute(text(today_query), {
                "location_id": location_id,
                "last_year_date": last_year_date
            })
            
            row = result.fetchone()
            if row:
                last_year_today_orders = int(row[0] or 0)
                last_year_today_sales = float(row[1] or 0) / 100.0
                
                # Calculate today's comparisons
                comparisons['today_sales'] = _calculate_comparison(
                    current_data.get('today_sales', 0), 
                    last_year_today_sales
                )
                comparisons['today_orders'] = _calculate_comparison(
                    current_data.get('today_orders', 0), 
                    last_year_today_orders
                )
            
            # 2. CURRENT SEASON (up to current day) vs LAST YEAR SAME SEASON (up to same day)
            if current_season:
                # Get current season info
                season_query = """
                    SELECT start_date, end_date, name
                    FROM operating_seasons 
                    WHERE name = :season_name 
                    AND EXTRACT(YEAR FROM start_date) = :current_year
                """
                
                season_result = await session.execute(text(season_query), {
                    "season_name": current_season,
                    "current_year": current_date.year
                })
                
                season_row = season_result.fetchone()
                if season_row:
                    season_start = season_row[0]
                    current_day = (current_date - season_start).days + 1
                    
                    # Get last year's season data up to the same day count
                    last_year_season_query = """
                        WITH season_comparison AS (
                            SELECT 
                                os.start_date,
                                EXTRACT(YEAR FROM os.start_date) as season_year,
                                COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as season_orders,
                                COALESCE(SUM(CASE 
                                    WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                                    THEN CAST(o.total_money->>'amount' AS INTEGER) 
                                    ELSE 0 
                                END), 0) as season_sales_cents
                            FROM operating_seasons os
                            LEFT JOIN orders o ON 
                                o.location_id = :location_id
                                AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                                AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.start_date + INTERVAL '1 day' * (:current_day - 1)
                                AND o.state = 'COMPLETED'
                            WHERE os.name = :season_name
                            AND EXTRACT(YEAR FROM os.start_date) IN (:current_year, :last_year)
                            GROUP BY os.start_date, EXTRACT(YEAR FROM os.start_date)
                        )
                        SELECT 
                            season_year,
                            season_orders,
                            season_sales_cents / 100.0 as season_sales
                        FROM season_comparison
                        ORDER BY season_year
                    """
                    
                    season_comp_result = await session.execute(text(last_year_season_query), {
                        "location_id": location_id,
                        "season_name": current_season,
                        "current_day": current_day,
                        "current_year": current_date.year,
                        "last_year": current_date.year - 1
                    })
                    
                    season_data = {}
                    for row in season_comp_result.fetchall():
                        year = int(row[0])
                        orders = int(row[1] or 0)
                        sales = float(row[2] or 0)
                        season_data[year] = {"orders": orders, "sales": sales}
                    
                    # Calculate season comparisons (current year up to current day vs last year up to same day)
                    if (current_date.year - 1) in season_data:
                        last_year_season = season_data[current_date.year - 1]
                        
                        comparisons['season_sales'] = _calculate_comparison(
                            current_data.get('total_sales_year', 0),
                            last_year_season['sales']
                        )
                        comparisons['season_orders'] = _calculate_comparison(
                            current_data.get('total_orders_year', 0),
                            last_year_season['orders']
                        )
            
            return comparisons
            
    except Exception as e:
        logger.error(f"Error getting comprehensive comparison for location {location_id}: {str(e)}")
        return {}

def _calculate_comparison(current_value: float, last_year_value: float) -> dict:
    """Helper function to calculate comparison direction and percentage"""
    if last_year_value > 0:
        change = ((current_value - last_year_value) / last_year_value) * 100
        if abs(change) < 0.1:  # Less than 0.1% difference
            return {"direction": "flat", "percentage": 0}
        elif change > 0:
            return {"direction": "up", "percentage": change}
        else:
            return {"direction": "down", "percentage": abs(change)}
    elif current_value > 0:
        # Had value this year but not last year
        return {"direction": "up", "percentage": 100}
    else:
        # No data for either year
        return None 