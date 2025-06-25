from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, and_, or_
from app.database.connection import get_db
from app.database.models.location import Location
from app.database.models.order import Order
from app.database.models.square_sale import SquareSale
from app.database.models.catalog import CatalogInventory, CatalogItem, CatalogVariation
from app.database.models.weather import DailyWeather
from app.services.weather_service import WeatherService
from app.services.square_service import SquareService
from app.utils.timezone import convert_utc_to_central
from app.logger import logger


class LocationService:
    """Service for handling location-specific data and metrics"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.square_service = SquareService()

    async def get_location_overview(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive overview data for a specific location"""
        try:
            async with get_db() as session:
                # Get location basic info
                location_info = await self._get_location_info(session, location_id)
                if not location_info:
                    return None
                
                # Get current metrics
                current_metrics = await self._get_current_metrics(session, location_id)
                
                # Get today's sales and orders
                today_data = await self._get_today_data(location_id, location_info.get('name'))
                
                # Add today's data to yearly totals (since it might not be in the database yet)
                current_metrics['total_sales_year'] += today_data.get('today_sales', 0)
                current_metrics['total_orders_year'] += today_data.get('today_orders', 0)
                
                # Get current season performance
                season_performance = await self._get_current_season_performance(session, location_id, location_info.get('name'), today_data)
                
                # Get historical data
                historical_data = await self._get_historical_data(session, location_id)
                
                # Get inventory summary
                inventory_summary = await self._get_inventory_summary(session, location_id)
                
                # Get weather data
                weather_data = await self._get_weather_data(location_info)
                
                return {
                    'location': location_info,
                    'current': {
                        **current_metrics,
                        **today_data,
                        'weather': weather_data,
                        'season_performance': season_performance
                    },
                    'historical': historical_data,
                    'inventory': inventory_summary
                }
                
        except Exception as e:
            logger.error(f"Error getting location overview for {location_id}: {str(e)}", exc_info=True)
            return None

    async def _get_location_info(self, session: AsyncSession, location_id: str) -> Optional[Dict[str, Any]]:
        """Get basic location information by ID or name"""
        try:
            # First try by ID
            query = """
                SELECT 
                    id, name, address, timezone, status, description,
                    business_hours, business_email, phone_number, website_url
                FROM locations 
                WHERE id = :location_id AND status = 'ACTIVE'
            """
            result = await session.execute(text(query), {"location_id": location_id})
            row = result.fetchone()
            
            # If not found by ID, try by name (case-insensitive)
            if not row:
                query = """
                    SELECT 
                        id, name, address, timezone, status, description,
                        business_hours, business_email, phone_number, website_url
                    FROM locations 
                    WHERE LOWER(name) = LOWER(:location_name) AND status = 'ACTIVE'
                """
                result = await session.execute(text(query), {"location_name": location_id})
                row = result.fetchone()
            
            if not row:
                logger.warning(f"Location not found: {location_id}")
                return None
                
            return {
                'id': row[0],
                'name': row[1],
                'address': row[2],
                'timezone': row[3],
                'status': row[4],
                'description': row[5],
                'business_hours': row[6],
                'business_email': row[7],
                'phone_number': row[8],
                'website_url': row[9]
            }
        except Exception as e:
            logger.error(f"Error getting location info: {str(e)}")
            return None

    async def _get_current_metrics(self, session: AsyncSession, location_id: str) -> Dict[str, Any]:
        """Get current year metrics for the location"""
        try:
            current_year = datetime.now().year
            
            # Orders and sales for current year (excluding New Years Eve orders which belong to previous year)
            # Also exclude $0 orders (no sale transactions to open cash drawer)
            query = """
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(CASE WHEN state = 'COMPLETED' THEN 1 END) as completed_orders,
                    COALESCE(SUM(CASE 
                        WHEN state = 'COMPLETED' AND total_money IS NOT NULL 
                        THEN CAST(total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as total_sales_cents,
                    COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as orders_last_30_days,
                    COALESCE(SUM(CASE 
                        WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' 
                        AND state = 'COMPLETED' 
                        AND total_money IS NOT NULL 
                        THEN CAST(total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as sales_last_30_days_cents
                FROM orders 
                WHERE location_id = :location_id 
                AND EXTRACT(YEAR FROM created_at) = :current_year
                AND NOT (EXTRACT(MONTH FROM created_at) = 1 AND EXTRACT(DAY FROM created_at) = 1)
                AND (total_money IS NULL OR CAST(total_money->>'amount' AS INTEGER) > 0)
            """
            
            result = await session.execute(text(query), {
                "location_id": location_id,
                "current_year": current_year
            })
            row = result.fetchone()
            
            return {
                'total_orders_year': row[0] or 0,
                'completed_orders_year': row[1] or 0,
                'total_sales_year': (row[2] or 0) / 100,  # Convert cents to dollars
                'orders_last_30_days': row[3] or 0,
                'sales_last_30_days': (row[4] or 0) / 100,  # Convert cents to dollars
            }
        except Exception as e:
            logger.error(f"Error getting current metrics: {str(e)}")
            return {}

    async def _get_today_data(self, location_id: str, location_name: str) -> Dict[str, Any]:
        """Get today's sales and orders from Square API"""
        try:
            # Try to get today's data from Square API
            metrics = await self.square_service.get_todays_sales()
            if metrics and 'locations' in metrics:
                for loc_id, loc_data in metrics['locations'].items():
                    if loc_id == location_id or loc_data.get('name') == location_name:
                        return {
                            'today_sales': loc_data.get('sales', 0),
                            'today_orders': loc_data.get('orders', 0)
                        }
            
            # Fallback to empty data if Square API fails
            return {
                'today_sales': 0,
                'today_orders': 0
            }
        except Exception as e:
            logger.warning(f"Could not get today's data from Square API: {str(e)}")
            return {
                'today_sales': 0,
                'today_orders': 0
            }

    async def _get_historical_data(self, session: AsyncSession, location_id: str) -> Dict[str, Any]:
        """Get historical data for the location (by year and season)"""
        try:
            # Get yearly totals for all available years (excluding New Years Eve from current year)
            # Also exclude $0 orders (no sale transactions to open cash drawer)
            query = """
                SELECT 
                    EXTRACT(YEAR FROM created_at) as year,
                    COUNT(*) as total_orders,
                    COUNT(CASE WHEN state = 'COMPLETED' THEN 1 END) as completed_orders,
                    COALESCE(SUM(CASE 
                        WHEN state = 'COMPLETED' AND total_money IS NOT NULL 
                        THEN CAST(total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as total_sales_cents
                FROM orders 
                WHERE location_id = :location_id 
                AND NOT (EXTRACT(YEAR FROM created_at) = :current_year AND EXTRACT(MONTH FROM created_at) = 1 AND EXTRACT(DAY FROM created_at) = 1)
                AND (total_money IS NULL OR CAST(total_money->>'amount' AS INTEGER) > 0)
                GROUP BY EXTRACT(YEAR FROM created_at)
                ORDER BY year DESC
            """
            
            result = await session.execute(text(query), {
                "location_id": location_id,
                "current_year": datetime.now().year
            })
            
            yearly_data = []
            for row in result.fetchall():
                yearly_data.append({
                    'year': int(row[0]),
                    'total_orders': row[1],
                    'completed_orders': row[2],
                    'total_sales': (row[3] or 0) / 100  # Convert cents to dollars
                })
            
            # Get seasonal breakdown for current year
            seasonal_data = await self._get_seasonal_breakdown(session, location_id)
            
            # Get yearly performance chart data
            yearly_performance = await self._get_yearly_performance_chart(session, location_id)
            
            # Get annual sales comparison data
            annual_comparison = await self._get_annual_sales_comparison(session, location_id)
            
            # Get operating seasons info for current year
            operating_seasons = await self._get_operating_seasons(session, datetime.now().year)
            
            # Calculate season rankings based on historical performance
            season_rankings = await self._get_season_rankings(session, location_id)
            
            return {
                'yearly_totals': yearly_data,
                'seasonal_breakdown': seasonal_data,
                'yearly_performance': yearly_performance,
                'annual_comparison': annual_comparison,
                'operating_seasons': operating_seasons,
                'season_rankings': season_rankings
            }
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return {}

    async def _get_seasonal_breakdown(self, session: AsyncSession, location_id: str) -> Dict[str, Any]:
        """Get seasonal breakdown for current year"""
        try:
            current_year = datetime.now().year
            current_date = datetime.now().date()
            
            # Get orders from current year only (no January from next year for New Years Eve)
            # Also exclude $0 orders (no sale transactions to open cash drawer)
            query = """
                SELECT 
                    created_at,
                    CASE WHEN state = 'COMPLETED' AND total_money IS NOT NULL 
                         THEN CAST(total_money->>'amount' AS INTEGER) 
                         ELSE 0 END as amount_cents
                FROM orders 
                WHERE location_id = :location_id 
                AND EXTRACT(YEAR FROM created_at) = :current_year
                AND state = 'COMPLETED'
                AND (total_money IS NULL OR CAST(total_money->>'amount' AS INTEGER) > 0)
                ORDER BY created_at
            """
            
            result = await session.execute(text(query), {
                "location_id": location_id,
                "current_year": current_year
            })
            
            # Initialize seasonal totals based on firework business seasons
            # Note: New Years Eve is excluded from current year data since it belongs to the previous year
            seasons = {
                'Texas Independence': {'sales': 0, 'orders': 0},
                'San Jacinto': {'sales': 0, 'orders': 0},
                'Memorial Day': {'sales': 0, 'orders': 0},
                'July 4th': {'sales': 0, 'orders': 0},
                'Diwali': {'sales': 0, 'orders': 0},
                'Off Season': {'sales': 0, 'orders': 0}
            }
            
            # Process each order
            for row in result.fetchall():
                created_at, amount_cents = row
                if created_at:
                    # Convert to central time and categorize by season
                    central_dt = convert_utc_to_central(created_at)
                    order_date = central_dt.date()
                    season = self._categorize_season(order_date)
                    
                    # Add to seasonal totals if it's a valid season for current year
                    # Exclude New Years Eve from current year since it belongs to previous year
                    if season in seasons and season != 'New Years Eve':
                        seasons[season]['sales'] += (amount_cents or 0) / 100
                        seasons[season]['orders'] += 1
            
            # Remove seasons that haven't started yet this year
            seasons_to_remove = []
            for season_name in seasons.keys():
                if season_name == 'Diwali':
                    # Diwali typically starts around Oct 12
                    diwali_start = date(current_year, 10, 12)
                    if current_date < diwali_start:
                        seasons_to_remove.append(season_name)
                # Other seasons are earlier in the year, so they've either happened or are past
                # Note: New Years Eve is never included in current year data
            
            # Remove future seasons from the display
            for season_name in seasons_to_remove:
                if seasons[season_name]['sales'] == 0 and seasons[season_name]['orders'] == 0:
                    del seasons[season_name]
            
            return seasons
        except Exception as e:
            logger.error(f"Error getting seasonal breakdown: {str(e)}")
            return {}

    async def _get_yearly_performance_chart(self, session: AsyncSession, location_id: str) -> Dict[str, Any]:
        """Get yearly performance data for chart (one bar per year) with enhanced metrics"""
        try:
            # Get total sales, order count, and average order value per year
            # Note: Only exclude Jan 1st from current year for New Years Eve attribution
            query = """
                SELECT 
                    EXTRACT(YEAR FROM created_at) as year,
                    COUNT(*) as total_orders,
                    COALESCE(SUM(CASE 
                        WHEN state = 'COMPLETED' AND total_money IS NOT NULL 
                        THEN CAST(total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as total_sales_cents
                FROM orders 
                WHERE location_id = :location_id 
                AND state = 'COMPLETED'
                AND NOT (EXTRACT(YEAR FROM created_at) = :current_year AND EXTRACT(MONTH FROM created_at) = 1 AND EXTRACT(DAY FROM created_at) = 1)
                GROUP BY EXTRACT(YEAR FROM created_at)
                ORDER BY year
            """
            
            result = await session.execute(text(query), {
                "location_id": location_id,
                "current_year": datetime.now().year
            })
            
            yearly_data = []
            total_sales_sum = 0
            total_years = 0
            current_year = datetime.now().year
            
            for row in result.fetchall():
                year, total_orders, total_sales_cents = row
                total_sales = float(total_sales_cents) / 100 if total_sales_cents else 0
                avg_order_value = total_sales / total_orders if total_orders > 0 else 0
                
                yearly_data.append({
                    'year': int(year) if year is not None else 0,
                    'total_sales': total_sales,
                    'total_orders': int(total_orders) if total_orders else 0,
                    'avg_order_value': round(avg_order_value, 2)
                })
                
                # Only include complete years in average calculation (exclude current year)
                if year and int(year) != current_year:
                    total_sales_sum += total_sales
                    total_years += 1
            
            # Calculate overall average (excluding current year)
            overall_average = total_sales_sum / total_years if total_years > 0 else 0
            
            return {
                'yearly_data': yearly_data,
                'overall_average': round(overall_average, 2)
            }
        except Exception as e:
            logger.error(f"Error getting yearly performance chart data: {str(e)}")
            return {'yearly_data': [], 'overall_average': 0}

    async def _get_annual_sales_comparison(self, session: AsyncSession, location_id: str) -> List[Dict[str, Any]]:
        """Get annual sales comparison by season for this location with enhanced metrics"""
        try:
            # Get seasonal data for all available years
            # Note: Only exclude Jan 1st from current year for New Years Eve attribution
            query = """
                SELECT 
                    EXTRACT(YEAR FROM created_at) as year,
                    created_at,
                    CASE WHEN state = 'COMPLETED' AND total_money IS NOT NULL 
                         THEN CAST(total_money->>'amount' AS INTEGER) 
                         ELSE 0 END as amount_cents
                FROM orders 
                WHERE location_id = :location_id 
                AND state = 'COMPLETED'
                AND NOT (EXTRACT(YEAR FROM created_at) = :current_year AND EXTRACT(MONTH FROM created_at) = 1 AND EXTRACT(DAY FROM created_at) = 1)
                ORDER BY year, created_at
            """
            
            result = await session.execute(text(query), {
                "location_id": location_id,
                "current_year": datetime.now().year
            })
            
            # Group orders by year and season with detailed metrics
            yearly_seasonal_data = {}
            
            for row in result.fetchall():
                year, created_at, amount_cents = row
                # Convert year to int to avoid Decimal JSON serialization issues
                year = int(year) if year is not None else None
                if created_at and year:
                    # Convert to central time and categorize by season
                    central_dt = convert_utc_to_central(created_at)
                    order_date = central_dt.date()
                    season = self._categorize_season(order_date)
                    
                    # Skip New Years Eve for current year (belongs to previous year)
                    if season == 'New Years Eve' and year == datetime.now().year:
                        continue
                    
                    # Skip off-season orders for cleaner chart
                    if season == 'Off Season':
                        continue
                    
                    if year not in yearly_seasonal_data:
                        yearly_seasonal_data[year] = {}
                    
                    if season not in yearly_seasonal_data[year]:
                        yearly_seasonal_data[year][season] = {
                            'total_sales': 0,
                            'order_count': 0,
                            'orders': []
                        }
                    
                    # Convert amount_cents to float to avoid Decimal JSON serialization issues
                    amount_value = float(amount_cents) if amount_cents is not None else 0
                    yearly_seasonal_data[year][season]['total_sales'] += amount_value / 100
                    yearly_seasonal_data[year][season]['order_count'] += 1
                    yearly_seasonal_data[year][season]['orders'].append(amount_value / 100)
            
            # Format data for the chart with enhanced metrics
            annual_data = []
            for year in sorted(yearly_seasonal_data.keys()):
                seasons_data = []
                for season_name, data in yearly_seasonal_data[year].items():
                    total_sales = data['total_sales']
                    order_count = data['order_count']
                    avg_order_value = total_sales / order_count if order_count > 0 else 0
                    
                    seasons_data.append({
                        'name': season_name,
                        'total_amount': float(total_sales),  # For chart compatibility
                        'total_sales': float(total_sales),
                        'order_count': int(order_count),
                        'avg_order_value': round(avg_order_value, 2)
                    })
                
                annual_data.append({
                    'year': int(year),  # Ensure it's an int for JSON serialization
                    'seasons': seasons_data
                })
            
            return annual_data
        except Exception as e:
            logger.error(f"Error getting annual sales comparison: {str(e)}")
            return []

    async def _get_inventory_summary(self, session: AsyncSession, location_id: str) -> Dict[str, Any]:
        """Get inventory summary for the location"""
        try:
            # Get total items and low stock items
            query = """
                SELECT 
                    COUNT(DISTINCT ci.variation_id) as total_items,
                    COUNT(CASE WHEN ci.quantity < 10 THEN 1 END) as low_stock_items,
                    COUNT(CASE WHEN ci.quantity = 0 THEN 1 END) as out_of_stock_items,
                    AVG(ci.quantity) as avg_quantity
                FROM catalog_inventory ci
                WHERE ci.location_id = :location_id
            """
            
            result = await session.execute(text(query), {"location_id": location_id})
            row = result.fetchone()
            
            return {
                'total_items': row[0] or 0,
                'low_stock_items': row[1] or 0,
                'out_of_stock_items': row[2] or 0,
                'avg_quantity': round(row[3] or 0, 1)
            }
        except Exception as e:
            logger.error(f"Error getting inventory summary: {str(e)}")
            return {}

    async def _get_weather_data(self, location_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current weather for the location"""
        try:
            if not location_info or not location_info.get('address'):
                return None
                
            address = location_info['address']
            postal_code = None
            
            if isinstance(address, dict):
                postal_code = address.get('postal_code', '').split('-')[0]
            elif isinstance(address, str):
                # Try to parse postal code from address string
                import re
                postal_match = re.search(r'\b(\d{5})\b', address)
                if postal_match:
                    postal_code = postal_match.group(1)
            
            if postal_code and len(postal_code) == 5:
                weather = await self.weather_service.get_weather_by_zip(postal_code)
                return weather
                
            return None
        except Exception as e:
            logger.warning(f"Could not get weather data: {str(e)}")
            return None

    async def _get_operating_seasons(self, session: AsyncSession, year: int) -> List[Dict[str, Any]]:
        """Get operating seasons from database for a specific year"""
        try:
            query = """
                SELECT name, start_date, end_date, rule_description
                FROM operating_seasons 
                WHERE EXTRACT(YEAR FROM start_date) = :year
                ORDER BY start_date
            """
            result = await session.execute(text(query), {"year": year})
            
            seasons = []
            for row in result.fetchall():
                seasons.append({
                    'name': row[0],
                    'start_date': row[1],
                    'end_date': row[2],
                    'rule_description': row[3]
                })
            return seasons
        except Exception as e:
            logger.warning(f"Could not get operating seasons from database: {str(e)}")
            return []

    async def _get_season_rankings(self, session: AsyncSession, location_id: str) -> List[Dict[str, Any]]:
        """Get firework season performance rankings for this location"""
        try:
            # This query properly handles New Years Eve by using the season start year
            # Orders from Jan 1st will be matched to the previous year's New Years Eve season
            query = """
                SELECT 
                    os.name,
                    COUNT(o.id) as total_orders,
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as total_sales_cents,
                    AVG(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END) as avg_order_value_cents
                FROM operating_seasons os
                LEFT JOIN orders o ON 
                    o.location_id = :location_id
                    AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date 
                    AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                    AND o.state = 'COMPLETED'
                WHERE EXTRACT(YEAR FROM os.start_date) >= 2018  -- All available historical data
                GROUP BY os.name
                HAVING COUNT(o.id) > 0  -- Only include seasons with orders
                ORDER BY total_sales_cents DESC, total_orders DESC
            """
            
            result = await session.execute(text(query), {"location_id": location_id})
            
            rankings = []
            rank = 1
            for row in result.fetchall():
                rankings.append({
                    'rank': rank,
                    'season_name': row[0],
                    'total_orders': row[1],
                    'total_sales': (row[2] or 0) / 100,
                    'avg_order_value': (row[3] or 0) / 100,
                    'performance_level': 'High' if rank <= 2 else 'Medium' if rank <= 4 else 'Low'
                })
                rank += 1
            
            return rankings
        except Exception as e:
            logger.warning(f"Could not get season rankings: {str(e)}")
            return []

    def _categorize_season(self, order_date: date) -> str:
        """Categorize a date into a firework business season"""
        month = order_date.month
        day = order_date.day
        
        # Texas Independence Day: Feb 25 - Mar 2
        if (month == 2 and day >= 25) or (month == 3 and day <= 2):
            return 'Texas Independence'
        
        # San Jacinto Day: Apr 16 - Apr 21
        elif month == 4 and 16 <= day <= 21:
            return 'San Jacinto'
        
        # Memorial Day: May 21 - May 27 (approximate range)
        elif month == 5 and 21 <= day <= 27:
            return 'Memorial Day'
        
        # July 4th: June 24 - July 4 (biggest firework season)
        elif (month == 6 and day >= 24) or (month == 7 and day <= 4):
            return 'July 4th'
        
        # Diwali: Oct 12 - Oct 23 (approximate range)
        elif month == 10 and 12 <= day <= 23:
            return 'Diwali'
        
        # New Years Eve: Dec 20 - Jan 1 (crosses year boundary)
        elif (month == 12 and day >= 20) or (month == 1 and day <= 1):
            return 'New Years Eve'
        
        # Everything else is off season for fireworks business
        else:
            return 'Off Season'

    async def get_all_locations(self) -> List[Dict[str, Any]]:
        """Get all active locations with basic info"""
        try:
            async with get_db() as session:
                query = """
                    SELECT id, name, address, status 
                    FROM locations 
                    WHERE status = 'ACTIVE' 
                    ORDER BY name
                """
                result = await session.execute(text(query))
                
                locations = []
                for row in result.fetchall():
                    locations.append({
                        'id': row[0],
                        'name': row[1],
                        'address': row[2],
                        'status': row[3]
                    })
                
                return locations
        except Exception as e:
            logger.error(f"Error getting all locations: {str(e)}")
            return []

    async def get_all_locations_overview(self) -> Dict[str, Any]:
        """Get combined overview data for all locations"""
        try:
            async with get_db() as session:
                locations = await self.get_all_locations()
                
                if not locations:
                    return {
                        'location': {'name': 'All Locations Combined', 'id': 'all'},
                        'current': self._get_empty_current_data(),
                        'historical': self._get_empty_historical_data(),
                        'inventory': self._get_empty_inventory_data()
                    }
                
                # Get aggregated current metrics
                combined_current = await self._get_combined_current_metrics(session, locations)
                
                # Get today's Square API data to pass to historical charts
                today_square_data = {
                    'today_sales': combined_current.get('today_sales', 0),
                    'today_orders': combined_current.get('today_orders', 0)
                }
                
                # Get aggregated historical data (pass today's Square API data for accurate 2025 totals)
                combined_historical = await self._get_combined_historical_data(session, locations, today_square_data)
                
                # Get aggregated inventory data
                combined_inventory = await self._get_combined_inventory_data(session, locations)
                
                return {
                    'location': {'name': 'All Locations Combined', 'id': 'all'},
                    'current': combined_current,
                    'historical': combined_historical,
                    'inventory': combined_inventory
                }
                
        except Exception as e:
            logger.error(f"Error getting all locations overview: {str(e)}", exc_info=True)
            return {
                'location': {'name': 'All Locations Combined', 'id': 'all'},
                'current': self._get_empty_current_data(),
                'historical': self._get_empty_historical_data(),
                'inventory': self._get_empty_inventory_data()
            }

    async def _get_combined_current_metrics(self, session: AsyncSession, locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get combined current metrics for all locations"""
        try:
            # Get current year for year-to-date calculations
            from app.utils.timezone import get_central_now
            current_central_time = get_central_now()
            current_year = current_central_time.year
            
            # Get today's data from Square API (same as individual locations)
            today_sales = 0
            today_orders = 0
            try:
                square_metrics = await self.square_service.get_todays_sales()
                if square_metrics:
                    today_sales = square_metrics.get('total_sales', 0)
                    today_orders = square_metrics.get('total_orders', 0)
                    logger.info(f"Got today's data from Square API: ${today_sales}, {today_orders} orders")
                else:
                    logger.warning("No Square API data available for today")
            except Exception as e:
                logger.warning(f"Could not get today's data from Square API: {str(e)}")
            
            # Aggregate year-to-date sales across all locations from database
            year_query = """
                SELECT 
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as total_sales,
                    COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as total_orders
                FROM orders o
                WHERE EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')) = :current_year
                AND o.state = 'COMPLETED'
            """
            
            result = await session.execute(text(year_query), {"current_year": current_year})
            year_row = result.fetchone()
            year_sales = 0
            year_orders = 0
            if year_row:
                year_sales = float(year_row[0]) / 100.0  # Convert from cents to dollars and ensure float
                year_orders = int(year_row[1])
            
            # Add today's Square API data to year totals (since it might not be in database yet)
            year_sales += today_sales
            year_orders += today_orders
            
            # Get combined season performance (pass today's Square API data)
            today_square_data = {
                'today_sales': today_sales,
                'today_orders': today_orders
            }
            season_performance = await self._get_combined_current_season_performance(session, locations, today_square_data)
            
            return {
                'today_sales': today_sales,
                'today_orders': today_orders,
                'total_sales_year': year_sales,
                'total_orders_year': year_orders,
                'weather': None,  # Will be handled separately
                'season_performance': season_performance
            }
            
        except Exception as e:
            logger.error(f"Error getting combined current metrics: {str(e)}")
            return self._get_empty_current_data()

    async def _get_combined_current_season_performance(self, session: AsyncSession, locations: List[Dict[str, Any]], today_square_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get combined current season performance across all locations"""
        try:
            # Determine current season using Central Time
            from app.utils.timezone import get_central_now
            current_central_time = get_central_now()
            current_date = current_central_time.date()
            
            current_season = self._categorize_season(current_date)
            
            # If we're in off season, return empty data
            if current_season == 'Off Season':
                return {
                    'season_name': 'Off Season',
                    'current_day': 0,
                    'daily_data': [],
                    'cumulative_progress': []
                }
            
            # Get current season dates for this year
            current_year = current_central_time.year
            season_dates = await self._get_season_date_range(session, current_season, current_year)
            
            if not season_dates:
                return {
                    'season_name': current_season,
                    'current_day': 0,
                    'daily_data': [],
                    'cumulative_progress': []
                }
            
            season_start = season_dates['start_date']
            season_end = season_dates['end_date']
            
            # Calculate which day we are in the season
            if current_date < season_start:
                current_day = 0
            elif current_date > season_end:
                current_day = (season_end - season_start).days + 1
            else:
                current_day = (current_date - season_start).days + 1
            
            # Get combined daily performance data for all locations
            daily_data = await self._get_combined_daily_season_comparison(session, current_season, current_day)
            
            # Get combined cumulative progress data
            cumulative_progress = await self._get_combined_cumulative_season_progress(session, current_season, current_day)
            
            # Add today's Square API data to current year if we're in season and it's a current day
            if current_day > 0 and current_date <= season_end and today_square_data:
                logger.info(f"Adding Square API data to season charts: ${today_square_data.get('today_sales', 0)}, {today_square_data.get('today_orders', 0)} orders")
                daily_data = self._add_today_data_to_combined_season(daily_data, current_day, current_year, today_square_data)
                cumulative_progress = self._add_today_data_to_combined_cumulative(cumulative_progress, current_year, today_square_data)
            
            # Get precipitation counts across all locations for each day
            weather_data = await self._get_combined_season_weather_data(session, season_start, season_end, current_day)
            
            return {
                'season_name': current_season,
                'current_day': current_day,
                'season_start': season_start.strftime('%b %d'),
                'season_end': season_end.strftime('%b %d'),
                'daily_data': daily_data,
                'cumulative_progress': cumulative_progress,
                'weather_data': weather_data
            }
            
        except Exception as e:
            logger.error(f"Error getting combined current season performance: {str(e)}")
            return {
                'season_name': 'Unknown',
                'current_day': 0,
                'daily_data': [],
                'cumulative_progress': []
            }

    async def _get_combined_daily_season_comparison(self, session: AsyncSession, season_name: str, current_day: int) -> List[Dict[str, Any]]:
        """Get combined daily sales comparison for current season across all locations and years"""
        try:
            # Get aggregated daily season data across ALL locations for comparison (2018-2025)
            query = """
                WITH season_totals AS (
                    -- Get total sales per year for this season across ALL locations
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as total_season_sales
                    FROM operating_seasons os
                    LEFT JOIN orders o ON 
                        CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                        AND o.state = 'COMPLETED'
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) BETWEEN 2018 AND 2025
                    GROUP BY EXTRACT(YEAR FROM os.start_date)
                ),
                daily_season_data AS (
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        (CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) - os.start_date + 1) as day_in_season,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as daily_sales,
                        COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as daily_orders
                    FROM operating_seasons os
                    LEFT JOIN orders o ON 
                        CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                        AND o.state = 'COMPLETED'
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) BETWEEN 2018 AND 2025
                    GROUP BY 
                        EXTRACT(YEAR FROM os.start_date),
                        CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE),
                        os.start_date
                    HAVING (CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) - os.start_date + 1) <= :current_day
                )
                SELECT 
                    dsd.day_in_season,
                    dsd.season_year,
                    dsd.daily_sales / 100.0 as daily_sales,
                    dsd.daily_orders,
                    CASE 
                        WHEN dsd.daily_orders > 0 
                        THEN ROUND((dsd.daily_sales / 100.0) / dsd.daily_orders, 2)
                        ELSE 0 
                    END as avg_per_order
                FROM daily_season_data dsd
                INNER JOIN season_totals st ON dsd.season_year = st.season_year
                WHERE st.total_season_sales > 0  -- Only include years with sales
                ORDER BY dsd.day_in_season, dsd.season_year
            """
            
            result = await session.execute(text(query), {
                "season_name": season_name,
                "current_day": current_day
            })
            
            # Group data by day
            daily_data = {}
            for row in result.fetchall():
                day = int(row[0])
                year = int(row[1])
                sales = float(row[2])
                orders = int(row[3])
                avg_per_order = float(row[4])
                
                if day not in daily_data:
                    daily_data[day] = {
                        'day': day,
                        'years': []
                    }
                
                daily_data[day]['years'].append({
                    'year': year,
                    'sales': sales,
                    'orders': orders,
                    'avg_per_order': avg_per_order
                })
            
            # Convert to list and sort
            return sorted(daily_data.values(), key=lambda x: x['day'])
            
        except Exception as e:
            logger.error(f"Error getting combined daily season comparison: {str(e)}")
            return []

    async def _get_combined_cumulative_season_progress(self, session: AsyncSession, season_name: str, current_day: int) -> List[Dict[str, Any]]:
        """Get combined cumulative season progress across all locations"""
        try:
            # Get cumulative progress for each year across ALL locations
            query = """
                WITH season_cumulative AS (
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            AND (CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) - os.start_date + 1) <= :current_day
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as cumulative_sales,
                        COUNT(CASE 
                            WHEN o.state = 'COMPLETED' 
                            AND (CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) - os.start_date + 1) <= :current_day
                            THEN 1 
                        END) as cumulative_orders
                    FROM operating_seasons os
                    LEFT JOIN orders o ON 
                        CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                        AND o.state = 'COMPLETED'
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) BETWEEN 2018 AND 2025
                    GROUP BY EXTRACT(YEAR FROM os.start_date)
                    HAVING COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) > 0  -- Only include years with sales
                )
                SELECT 
                    season_year,
                    cumulative_sales / 100.0 as total_sales,
                    cumulative_orders as total_orders,
                    CASE 
                        WHEN cumulative_orders > 0 
                        THEN ROUND((cumulative_sales / 100.0) / cumulative_orders, 2)
                        ELSE 0 
                    END as avg_per_order
                FROM season_cumulative
                ORDER BY season_year
            """
            
            result = await session.execute(text(query), {
                "season_name": season_name,
                "current_day": current_day
            })
            
            cumulative_data = []
            for row in result.fetchall():
                cumulative_data.append({
                    'year': int(row[0]),
                    'total_sales': float(row[1]),
                    'total_orders': int(row[2]),
                    'avg_per_order': float(row[3])
                })
            
            return cumulative_data
            
        except Exception as e:
            logger.error(f"Error getting combined cumulative season progress: {str(e)}")
            return []

    async def _get_combined_historical_data(self, session: AsyncSession, locations: List[Dict[str, Any]], today_square_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get combined historical data for all locations"""
        try:
            # Get combined seasonal breakdown across all locations (pass today's Square API data)
            seasonal_breakdown = await self._get_combined_seasonal_breakdown(session, today_square_data)
            
            # Get combined yearly performance across all locations
            yearly_performance = await self._get_combined_yearly_performance(session)
            
            # Get combined annual sales comparison across all locations (pass today's Square API data)
            annual_comparison = await self._get_combined_annual_sales_comparison(session, today_square_data)
            
            # Get combined season rankings across all locations
            season_rankings = await self._get_combined_season_rankings(session)
            
            # Get operating seasons info for current year (same as individual locations)
            operating_seasons = await self._get_operating_seasons(session, datetime.now().year)
            
            return {
                'seasonal_breakdown': seasonal_breakdown,
                'yearly_performance': yearly_performance,
                'annual_comparison': annual_comparison,
                'season_rankings': season_rankings,
                'operating_seasons': operating_seasons
            }
            
        except Exception as e:
            logger.error(f"Error getting combined historical data: {str(e)}")
            return self._get_empty_historical_data()

    async def _get_combined_seasonal_breakdown(self, session: AsyncSession, today_square_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get seasonal breakdown across all locations"""
        try:
            # Get seasonal performance across all locations for 2025
            query = """
                SELECT 
                    os.name as season_name,
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) / 100.0 as total_sales,
                    COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as total_orders,
                    os.start_date,
                    os.end_date
                FROM operating_seasons os
                LEFT JOIN orders o ON 
                    CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                    AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                    AND o.state = 'COMPLETED'
                WHERE EXTRACT(YEAR FROM os.start_date) = 2025
                GROUP BY os.name, os.start_date, os.end_date
                ORDER BY os.start_date
            """
            
            result = await session.execute(text(query))
            seasonal_data = {}
            
            for row in result.fetchall():
                season_name = row[0]
                total_sales = float(row[1])
                total_orders = int(row[2])
                start_date = row[3]
                end_date = row[4]
                
                # Add today's Square API data to current season if we're in that season
                if today_square_data:
                    from app.utils.timezone import get_central_now
                    current_date = get_central_now().date()
                    if start_date <= current_date <= end_date:
                        total_sales += today_square_data.get('today_sales', 0)
                        total_orders += today_square_data.get('today_orders', 0)
                        logger.info(f"Added Square API data to {season_name} seasonal breakdown: +${today_square_data.get('today_sales', 0)}, +{today_square_data.get('today_orders', 0)} orders")
                
                seasonal_data[season_name] = {
                    'total_sales': total_sales,
                    'total_orders': total_orders,
                    'avg_per_order': round(total_sales / total_orders, 2) if total_orders > 0 else 0,
                    'start_date': start_date.strftime('%b %d'),
                    'end_date': end_date.strftime('%b %d')
                }
            
            return seasonal_data
        except Exception as e:
            logger.error(f"Error getting combined seasonal breakdown: {str(e)}")
            return {}

    async def _get_combined_yearly_performance(self, session: AsyncSession) -> Dict[str, Any]:
        """Get yearly performance across all locations (same format as individual locations)"""
        try:
            # Get yearly totals across ALL locations
            query = """
                SELECT 
                    EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')) as year,
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) / 100.0 as total_sales,
                    COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as total_orders
                FROM orders o
                WHERE o.state = 'COMPLETED'
                AND EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')) BETWEEN 2018 AND 2025
                GROUP BY EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago'))
                HAVING COALESCE(SUM(CASE 
                    WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                    THEN CAST(o.total_money->>'amount' AS INTEGER) 
                    ELSE 0 
                END), 0) > 0
                ORDER BY year
            """
            
            result = await session.execute(text(query))
            
            yearly_data = []
            total_sales_sum = 0
            total_years = 0
            current_year = datetime.now().year
            
            for row in result.fetchall():
                year = int(row[0])
                total_sales = float(row[1])
                total_orders = int(row[2])
                avg_order_value = total_sales / total_orders if total_orders > 0 else 0
                
                yearly_data.append({
                    'year': year,
                    'total_sales': total_sales,
                    'total_orders': total_orders,
                    'avg_order_value': round(avg_order_value, 2)
                })
                
                # Only include complete years in average calculation (exclude current year)
                if year != current_year:
                    total_sales_sum += total_sales
                    total_years += 1
            
            # Calculate overall average (excluding current year)
            overall_average = total_sales_sum / total_years if total_years > 0 else 0
            
            return {
                'yearly_data': yearly_data,
                'overall_average': round(overall_average, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting combined yearly performance: {str(e)}")
            return {'yearly_data': [], 'overall_average': 0}

    async def _get_combined_annual_sales_comparison(self, session: AsyncSession, today_square_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get annual sales comparison by season across all locations (same format as dashboard)"""
        try:
            # Get seasonal sales data across ALL locations for all years
            query = """
                SELECT 
                    os.name as season_name,
                    EXTRACT(YEAR FROM os.start_date) as season_year,
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) / 100.0 as total_sales,
                    COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as total_orders,
                    os.start_date,
                    os.end_date
                FROM operating_seasons os
                LEFT JOIN orders o ON 
                    CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                    AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                    AND o.state = 'COMPLETED'
                WHERE EXTRACT(YEAR FROM os.start_date) BETWEEN 2018 AND 2025
                GROUP BY os.name, os.start_date, os.end_date
                HAVING COALESCE(SUM(CASE 
                    WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                    THEN CAST(o.total_money->>'amount' AS INTEGER) 
                    ELSE 0 
                END), 0) > 0
                ORDER BY os.start_date
            """
            
            result = await session.execute(text(query))
            
            # Group by year and season
            yearly_seasons = {}
            for row in result.fetchall():
                season_name = row[0]
                season_year = int(row[1])
                total_sales = float(row[2])
                total_orders = int(row[3])
                start_date = row[4]
                end_date = row[5]
                
                # Add today's Square API data to current season if we're in that season
                if today_square_data and season_year == 2025:
                    from app.utils.timezone import get_central_now
                    current_date = get_central_now().date()
                    if start_date <= current_date <= end_date:
                        total_sales += today_square_data.get('today_sales', 0)
                        total_orders += today_square_data.get('today_orders', 0)
                        logger.info(f"Added Square API data to {season_name} {season_year} annual comparison: +${today_square_data.get('today_sales', 0)}, +{today_square_data.get('today_orders', 0)} orders")
                
                if season_year not in yearly_seasons:
                    yearly_seasons[season_year] = []
                
                yearly_seasons[season_year].append({
                    'name': season_name,
                    'total_amount': total_sales,
                    'total_sales': total_sales,
                    'order_count': total_orders,
                    'avg_order_value': round(total_sales / total_orders, 2) if total_orders > 0 else 0
                })
            
            # Convert to the format expected by the template (same as dashboard)
            annual_data = []
            for year in sorted(yearly_seasons.keys()):
                annual_data.append({
                    'year': year,
                    'seasons': yearly_seasons[year]
                })
            
            return annual_data
            
        except Exception as e:
            logger.error(f"Error getting combined annual sales comparison: {str(e)}")
            return []

    async def _get_combined_season_rankings(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get season rankings across all locations"""
        try:
            # This would aggregate season rankings across all locations
            # For now, return empty list - can be implemented later
            return []
        except Exception as e:
            logger.error(f"Error getting combined season rankings: {str(e)}")
            return []

    async def _get_combined_inventory_data(self, session: AsyncSession, locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get combined inventory data for all locations"""
        try:
            # Get basic inventory stats from items view (which aggregates across locations)
            inventory_query = """
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(CASE WHEN category IS NULL OR category = '' THEN 1 END) as missing_category,
                    COUNT(CASE WHEN description IS NULL OR description = '' THEN 1 END) as missing_description,
                    COUNT(CASE WHEN sku IS NULL OR sku = '' THEN 1 END) as missing_sku
                FROM items_view
                WHERE archived != 'Y'
            """
            
            result = await session.execute(text(inventory_query))
            row = result.fetchone()
            
            if row:
                total_items = int(row[0])
                missing_category = int(row[1])
                missing_description = int(row[2])
                missing_sku = int(row[3])
                
                # Get category breakdown
                category_query = """
                    SELECT 
                        COALESCE(category, 'Uncategorized') as category,
                        COUNT(*) as item_count
                    FROM items_view
                    WHERE archived != 'Y'
                    GROUP BY category
                    ORDER BY item_count DESC
                    LIMIT 10
                """
                
                result = await session.execute(text(category_query))
                categories = []
                for cat_row in result.fetchall():
                    categories.append({
                        'name': cat_row[0],
                        'count': int(cat_row[1])
                    })
                
                # Get average quantity across all items
                avg_qty_query = """
                    SELECT AVG(total_qty) as avg_quantity
                    FROM items_view
                    WHERE archived != 'Y' AND total_qty > 0
                """
                
                avg_result = await session.execute(text(avg_qty_query))
                avg_row = avg_result.fetchone()
                avg_quantity = round(float(avg_row[0])) if avg_row and avg_row[0] else 0
                
                return {
                    'total_items': total_items,
                    'low_stock_items': 0,  # Would need inventory counts to determine this
                    'out_of_stock_items': 0,  # Would need inventory counts to determine this
                    'avg_quantity': avg_quantity,
                    'missing_category': missing_category,
                    'missing_description': missing_description,
                    'missing_sku': missing_sku,
                    'categories': categories
                }
            else:
                return self._get_empty_inventory_data()
                
        except Exception as e:
            logger.error(f"Error getting combined inventory data: {str(e)}")
            return self._get_empty_inventory_data()

    async def _get_today_combined_data(self, session: AsyncSession) -> Dict[str, Any]:
        """Get current season's combined sales and orders across all locations (not just today)"""
        try:
            # Get current season dates
            from app.utils.timezone import get_central_now
            current_date = get_central_now().date()
            current_year = current_date.year
            
            # Get current season info
            season_query = """
                SELECT start_date, end_date, name
                FROM operating_seasons 
                WHERE start_date <= :current_date AND end_date >= :current_date AND EXTRACT(YEAR FROM start_date) = :current_year
                ORDER BY start_date DESC
                LIMIT 1
            """
            
            season_result = await session.execute(text(season_query), {
                'current_date': current_date, 
                'current_year': current_year
            })
            season_row = season_result.fetchone()
            
            if not season_row:
                logger.info("No current season found, using year-to-date data")
                # Fall back to year-to-date data if no current season
                ytd_query = """
                    SELECT 
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as total_sales,
                        COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as total_orders
                    FROM orders o
                    WHERE EXTRACT(YEAR FROM (o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')) = :current_year
                    AND o.state = 'COMPLETED'
                """
                
                result = await session.execute(text(ytd_query), {'current_year': current_year})
                row = result.fetchone()
                
                if row:
                    return {
                        'today_sales': float(row[0]) / 100.0,
                        'today_orders': int(row[1])
                    }
                return {'today_sales': 0, 'today_orders': 0}
            
            season_start = season_row[0]
            season_end = season_row[1]
            season_name = season_row[2]
            
            # Get sales from current season so far (same logic for all years including 2025)
            season_data_query = """
                SELECT 
                    COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) as total_sales,
                    COUNT(CASE WHEN o.state = 'COMPLETED' THEN 1 END) as total_orders
                FROM orders o
                WHERE CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= :season_start
                AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= :season_end
                AND o.state = 'COMPLETED'
            """
            
            result = await session.execute(text(season_data_query), {
                'season_start': season_start, 
                'season_end': min(current_date, season_end)
            })
            
            row = result.fetchone()
            
            if row:
                season_sales = float(row[0]) / 100.0
                season_orders = int(row[1])
                logger.info(f"Current season ({season_name}) data: ${season_sales}, {season_orders} orders")
                return {
                    'today_sales': season_sales,  # Actually season-to-date sales
                    'today_orders': season_orders  # Actually season-to-date orders
                }
            return {'today_sales': 0, 'today_orders': 0}
            
        except Exception as e:
            logger.error(f"Error getting current season combined data: {str(e)}")
            return {'today_sales': 0, 'today_orders': 0}

    def _add_today_data_to_combined_season(self, daily_data: List[Dict[str, Any]], current_day: int, current_year: int, today_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add today's combined sales and orders to the current year's daily season data"""
        try:
            # Find the current day's data in daily_data
            for day_entry in daily_data:
                if day_entry['day'] == current_day:
                    # Find the current year in the years data for this day
                    found_year = False
                    for year_data in day_entry['years']:
                        if year_data['year'] == current_year:
                            # Add today's data to the existing database data
                            year_data['sales'] += today_data.get('today_sales', 0)
                            year_data['orders'] += today_data.get('today_orders', 0)
                            # Recalculate average per order
                            if year_data['orders'] > 0:
                                year_data['avg_per_order'] = round(year_data['sales'] / year_data['orders'], 2)
                            else:
                                year_data['avg_per_order'] = 0
                            found_year = True
                            break
                    
                    # If current year not found, add it
                    if not found_year:
                        day_entry['years'].append({
                            'year': current_year,
                            'sales': today_data.get('today_sales', 0),
                            'orders': today_data.get('today_orders', 0),
                            'avg_per_order': round(today_data.get('today_sales', 0) / today_data.get('today_orders', 1), 2) if today_data.get('today_orders', 0) > 0 else 0
                        })
                    break
            else:
                # If current day not found, add it with current year data
                daily_data.append({
                    'day': current_day,
                    'years': [{
                        'year': current_year,
                        'sales': today_data.get('today_sales', 0),
                        'orders': today_data.get('today_orders', 0),
                        'avg_per_order': round(today_data.get('today_sales', 0) / today_data.get('today_orders', 1), 2) if today_data.get('today_orders', 0) > 0 else 0
                    }]
                })
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Error adding today's data to combined season charts: {str(e)}")
            return daily_data

    def _add_today_data_to_combined_cumulative(self, cumulative_progress: List[Dict[str, Any]], current_year: int, today_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add today's combined sales and orders to the current year's cumulative progress data"""
        try:
            # Find the current year in cumulative progress data
            found_year = False
            for year_data in cumulative_progress:
                if year_data['year'] == current_year:
                    # Add today's data to the existing database data
                    year_data['total_sales'] += today_data.get('today_sales', 0)
                    year_data['total_orders'] += today_data.get('today_orders', 0)
                    # Recalculate average per order
                    if year_data['total_orders'] > 0:
                        year_data['avg_per_order'] = round(year_data['total_sales'] / year_data['total_orders'], 2)
                    else:
                        year_data['avg_per_order'] = 0
                    found_year = True
                    break
            
            # If current year not found, add it
            if not found_year:
                cumulative_progress.append({
                    'year': current_year,
                    'total_sales': today_data.get('today_sales', 0),
                    'total_orders': today_data.get('today_orders', 0),
                    'avg_per_order': round(today_data.get('today_sales', 0) / today_data.get('today_orders', 1), 2) if today_data.get('today_orders', 0) > 0 else 0
                })
            
            return cumulative_progress
            
        except Exception as e:
            logger.error(f"Error adding today's data to combined cumulative progress: {str(e)}")
            return cumulative_progress

    def _get_empty_current_data(self) -> Dict[str, Any]:
        """Return empty current data structure"""
        return {
            'today_sales': 0,
            'today_orders': 0,
            'total_sales_year': 0,
            'total_orders_year': 0,
            'weather': None,
            'season_performance': None
        }

    def _get_empty_historical_data(self) -> Dict[str, Any]:
        """Return empty historical data structure"""
        return {
            'seasonal_breakdown': {},
            'yearly_performance': [],
            'annual_comparison': [],
            'season_rankings': [],
            'operating_seasons': []
        }

    def _get_empty_inventory_data(self) -> Dict[str, Any]:
        """Return empty inventory data structure"""
        return {
            'total_items': 0,
            'low_stock_items': 0,
            'out_of_stock_items': 0,
            'avg_quantity': 0,
            'missing_category': 0,
            'missing_description': 0,
            'missing_sku': 0,
            'categories': []
        }

    async def _get_current_season_performance(self, session: AsyncSession, location_id: str, location_name: str = None, today_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get current season daily performance data with year-over-year comparison"""
        try:
            # Determine current season using Central Time (not UTC!)
            from app.utils.timezone import get_central_now
            current_central_time = get_central_now()
            current_date = current_central_time.date()
            
            current_season = self._categorize_season(current_date)
            
            # If we're in off season, return empty data
            if current_season == 'Off Season':
                return {
                    'season_name': 'Off Season',
                    'current_day': 0,
                    'daily_data': [],
                    'cumulative_progress': []
                }
            
            # Get current season dates for 2025 (use Central Time year)
            current_year = current_central_time.year
            season_dates = await self._get_season_date_range(session, current_season, current_year)
            
            if not season_dates:
                return {
                    'season_name': current_season,
                    'current_day': 0,
                    'daily_data': [],
                    'cumulative_progress': []
                }
            
            season_start = season_dates['start_date']
            season_end = season_dates['end_date']
            
            # Calculate which day we are in the season
            if current_date < season_start:
                current_day = 0
            elif current_date > season_end:
                current_day = (season_end - season_start).days + 1
            else:
                current_day = (current_date - season_start).days + 1
            
            # Get today's data if not provided
            if today_data is None:
                today_data = await self._get_today_data(location_id, location_name)
            
            # Get daily performance data for all years
            daily_data = await self._get_daily_season_comparison(session, location_id, current_season, current_day)
            
            # Get cumulative progress data
            cumulative_progress = await self._get_cumulative_season_progress(session, location_id, current_season, current_day)
            
            # Add today's data to the current year's data if we're in season and it's a current day
            if current_day > 0 and current_date <= season_end and today_data:
                daily_data = self._add_today_data_to_season(daily_data, current_day, current_year, today_data)
                cumulative_progress = self._add_today_data_to_cumulative(cumulative_progress, current_year, today_data)
            
            # Get weather data for season days
            weather_data = await self._get_season_weather_data(session, location_id, season_start, season_end, current_day)
            
            return {
                'season_name': current_season,
                'current_day': current_day,
                'season_start': season_start.strftime('%b %d'),
                'season_end': season_end.strftime('%b %d'),
                'daily_data': daily_data,
                'cumulative_progress': cumulative_progress,
                'weather_data': weather_data
            }
            
        except Exception as e:
            logger.error(f"Error getting current season performance: {str(e)}")
            return {
                'season_name': 'Unknown',
                'current_day': 0,
                'daily_data': [],
                'cumulative_progress': []
            }

    async def _get_season_date_range(self, session: AsyncSession, season_name: str, year: int) -> Optional[Dict[str, Any]]:
        """Get start and end dates for a specific season and year"""
        try:
            query = """
                SELECT start_date, end_date
                FROM operating_seasons 
                WHERE name = :season_name 
                AND EXTRACT(YEAR FROM start_date) = :year
            """
            result = await session.execute(text(query), {
                "season_name": season_name,
                "year": year
            })
            row = result.fetchone()
            
            if row:
                return {
                    'start_date': row[0],
                    'end_date': row[1]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting season date range: {str(e)}")
            return None
    
    def _add_today_data_to_season(self, daily_data: List[Dict[str, Any]], current_day: int, current_year: int, today_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add today's sales and orders to the current year's daily season data"""
        try:
            # Find the current day's data in daily_data
            for day_entry in daily_data:
                if day_entry['day'] == current_day:
                    # Find the current year in the years data for this day
                    for year_data in day_entry['years']:
                        if year_data['year'] == current_year:
                            # Add today's data to the existing database data
                            year_data['sales'] += today_data.get('today_sales', 0)
                            year_data['orders'] += today_data.get('today_orders', 0)
                            # Recalculate average per order
                            if year_data['orders'] > 0:
                                year_data['avg_per_order'] = round(year_data['sales'] / year_data['orders'], 2)
                            else:
                                year_data['avg_per_order'] = 0
                            break
                    break
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Error adding today's data to season charts: {str(e)}")
            return daily_data
    
    def _add_today_data_to_cumulative(self, cumulative_progress: List[Dict[str, Any]], current_year: int, today_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add today's sales and orders to the current year's cumulative progress data"""
        try:
            # Find the current year in cumulative progress data
            for year_data in cumulative_progress:
                if year_data['year'] == current_year:
                    # Add today's data to the existing database data
                    year_data['total_sales'] += today_data.get('today_sales', 0)
                    year_data['total_orders'] += today_data.get('today_orders', 0)
                    # Recalculate average per order
                    if year_data['total_orders'] > 0:
                        year_data['avg_per_order'] = round(year_data['total_sales'] / year_data['total_orders'], 2)
                    else:
                        year_data['avg_per_order'] = 0
                    break
            
            return cumulative_progress
            
        except Exception as e:
            logger.error(f"Error adding today's data to cumulative progress: {str(e)}")
            return cumulative_progress

    async def _get_daily_season_comparison(self, session: AsyncSession, location_id: str, season_name: str, current_day: int) -> List[Dict[str, Any]]:
        """Get daily sales comparison for current season across years"""
        try:
            # Get historical season data for comparison (2018-2025)
            # Only include years where the location had sales during that season
            query = """
                WITH season_totals AS (
                    -- First, get total sales per year for this season to filter out years with no sales
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as total_season_sales
                    FROM operating_seasons os
                    LEFT JOIN orders o ON 
                        o.location_id = :location_id
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                        AND o.state = 'COMPLETED'
                        AND (o.total_money IS NULL OR CAST(o.total_money->>'amount' AS INTEGER) > 0)
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) >= 2018
                    GROUP BY EXTRACT(YEAR FROM os.start_date)
                    HAVING COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) > 0 
                    OR EXTRACT(YEAR FROM os.start_date) = EXTRACT(YEAR FROM CURRENT_DATE)  -- Always include current year
                ),
                season_days AS (
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        os.start_date,
                        os.end_date,
                        generate_series(
                            os.start_date, 
                            os.end_date, 
                            '1 day'::interval
                        )::date as day_date,
                        ROW_NUMBER() OVER (
                            PARTITION BY EXTRACT(YEAR FROM os.start_date) 
                            ORDER BY generate_series(os.start_date, os.end_date, '1 day'::interval)
                        ) as day_number
                    FROM operating_seasons os
                    INNER JOIN season_totals st ON st.season_year = EXTRACT(YEAR FROM os.start_date)
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) >= 2018
                ),
                daily_sales AS (
                    SELECT 
                        sd.season_year,
                        sd.day_number,
                        sd.day_date,
                        COUNT(o.id) as orders,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as sales_cents
                    FROM season_days sd
                    LEFT JOIN orders o ON 
                        o.location_id = :location_id
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) = sd.day_date
                        AND o.state = 'COMPLETED'
                        AND (o.total_money IS NULL OR CAST(o.total_money->>'amount' AS INTEGER) > 0)
                    WHERE sd.day_number <= :current_day
                    GROUP BY sd.season_year, sd.day_number, sd.day_date
                    ORDER BY sd.day_number, sd.season_year DESC
                )
                SELECT 
                    day_number,
                    MIN(day_date) as sample_date,
                    JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'year', season_year,
                            'sales', ROUND(sales_cents / 100.0, 2),
                            'orders', orders,
                            'avg_per_order', CASE 
                                WHEN orders > 0 
                                THEN ROUND(sales_cents / 100.0 / orders, 2) 
                                ELSE 0 
                            END
                        ) ORDER BY season_year ASC  -- Change to ASC so current year (2025) appears last/rightmost
                    ) as year_data
                FROM daily_sales
                GROUP BY day_number
                ORDER BY day_number
            """
            
            result = await session.execute(text(query), {
                "season_name": season_name,
                "location_id": location_id,
                "current_day": current_day
            })
            
            daily_data = []
            for row in result.fetchall():
                # Log for debugging
                logger.info(f"Daily data for day {row[0]} ({row[1]}): {len(row[2])} years of data")
                daily_data.append({
                    'day': int(row[0]),
                    'date': row[1].strftime('%m/%d'),
                    'years': row[2]
                })
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Error getting daily season comparison: {str(e)}")
            return []

    async def _get_cumulative_season_progress(self, session: AsyncSession, location_id: str, season_name: str, current_day: int) -> List[Dict[str, Any]]:
        """Get cumulative season progress for year-over-year comparison"""
        try:
            # Fix the date range calculation - for current_day = 1, we want just the start_date
            # For current_day = 2, we want start_date + 1 day, etc.
            query = """
                WITH season_totals AS (
                    -- First, get total sales per year for this season to filter out years with no sales
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as total_season_sales
                    FROM operating_seasons os
                    LEFT JOIN orders o ON 
                        o.location_id = :location_id
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.end_date
                        AND o.state = 'COMPLETED'
                        AND (o.total_money IS NULL OR CAST(o.total_money->>'amount' AS INTEGER) > 0)
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) >= 2018
                    GROUP BY EXTRACT(YEAR FROM os.start_date)
                    HAVING COALESCE(SUM(CASE 
                        WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                        THEN CAST(o.total_money->>'amount' AS INTEGER) 
                        ELSE 0 
                    END), 0) > 0 
                    OR EXTRACT(YEAR FROM os.start_date) = EXTRACT(YEAR FROM CURRENT_DATE)  -- Always include current year
                ),
                season_cumulative AS (
                    SELECT 
                        EXTRACT(YEAR FROM os.start_date) as season_year,
                        os.start_date,
                        os.start_date + INTERVAL '1 day' * (:current_day - 1) as end_date_for_comparison,
                        COUNT(o.id) as total_orders,
                        COALESCE(SUM(CASE 
                            WHEN o.state = 'COMPLETED' AND o.total_money IS NOT NULL 
                            THEN CAST(o.total_money->>'amount' AS INTEGER) 
                            ELSE 0 
                        END), 0) as total_sales_cents
                    FROM operating_seasons os
                    INNER JOIN season_totals st ON st.season_year = EXTRACT(YEAR FROM os.start_date)
                    LEFT JOIN orders o ON 
                        o.location_id = :location_id
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) >= os.start_date
                        AND CAST((o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') AS DATE) <= os.start_date + INTERVAL '1 day' * (:current_day - 1)
                        AND o.state = 'COMPLETED'
                        AND (o.total_money IS NULL OR CAST(o.total_money->>'amount' AS INTEGER) > 0)
                    WHERE os.name = :season_name
                    AND EXTRACT(YEAR FROM os.start_date) >= 2018
                    GROUP BY EXTRACT(YEAR FROM os.start_date), os.start_date
                    ORDER BY season_year ASC  -- Change to ASC so 2025 appears rightmost
                )
                SELECT 
                    season_year,
                    total_orders,
                    ROUND(total_sales_cents / 100.0, 2) as total_sales,
                    CASE 
                        WHEN total_orders > 0 
                        THEN ROUND(total_sales_cents / 100.0 / total_orders, 2) 
                        ELSE 0 
                    END as avg_per_order,
                    start_date,
                    end_date_for_comparison
                FROM season_cumulative
            """
            
            result = await session.execute(text(query), {
                "season_name": season_name,
                "location_id": location_id,
                "current_day": current_day
            })
            
            progress_data = []
            for row in result.fetchall():
                # Log the date ranges for debugging
                logger.info(f"Season progress for {row[0]}: {row[1]} orders, ${row[2]}, dates {row[4]} to {row[5]}")
                progress_data.append({
                    'year': int(row[0]),
                    'total_orders': row[1],
                    'total_sales': float(row[2]),
                    'avg_per_order': float(row[3])
                })
            
            return progress_data
            
        except Exception as e:
            logger.error(f"Error getting cumulative season progress: {str(e)}")
            return []

    async def _get_season_weather_data(self, session: AsyncSession, location_id: str, season_start: date, season_end: date, current_day: int) -> List[Dict[str, Any]]:
        """Get weather data for each day of the current season"""
        try:
            # Get historical weather data from database
            query = """
                SELECT 
                    date,
                    temp_high,
                    temp_low,
                    temp_avg,
                    weather_main,
                    weather_description,
                    weather_icon,
                    humidity,
                    precipitation,
                    wind_speed
                FROM daily_weather
                WHERE location_id = :location_id
                AND date >= :season_start
                AND date <= :season_end
                ORDER BY date
            """
            
            result = await session.execute(text(query), {
                "location_id": location_id,
                "season_start": season_start,
                "season_end": season_end
            })
            
            weather_records = result.fetchall()
            weather_dict = {}
            
            # Convert to dictionary keyed by date
            for record in weather_records:
                weather_dict[record[0]] = {
                    'date': record[0].strftime('%m/%d'),
                    'temp_high': record[1],
                    'temp_low': record[2],
                    'temp_avg': record[3],
                    'weather_main': record[4],
                    'weather_description': record[5],
                    'weather_icon': record[6],
                    'humidity': record[7],
                    'precipitation': record[8],
                    'wind_speed': record[9]
                }
            
            # Build complete weather data for each day of season
            weather_data = []
            current_date = season_start
            day_num = 1
            
            while current_date <= season_end:
                if current_date in weather_dict:
                    # Use historical data from database
                    weather_info = weather_dict[current_date]
                    weather_info['day'] = day_num
                    weather_info['is_current'] = day_num == current_day
                    weather_data.append(weather_info)
                elif day_num == current_day:
                    # For today, get current weather from API
                    try:
                        # Get location info for weather API
                        location_query = """
                            SELECT address->>'postal_code' as zip_code, name
                            FROM locations
                            WHERE id = :location_id
                        """
                        loc_result = await session.execute(text(location_query), {"location_id": location_id})
                        loc_row = loc_result.fetchone()
                        
                        if loc_row and loc_row[0]:
                            current_weather = await self.weather_service.get_weather_by_zip(loc_row[0])
                            if current_weather:
                                weather_data.append({
                                    'day': day_num,
                                    'date': current_date.strftime('%m/%d'),
                                    'temp_high': current_weather.get('temp_max'),
                                    'temp_low': current_weather.get('temp_min'),
                                    'temp_avg': current_weather.get('temp'),
                                    'weather_main': current_weather.get('main'),
                                    'weather_description': current_weather.get('description'),
                                    'weather_icon': current_weather.get('icon'),
                                    'humidity': current_weather.get('humidity'),
                                    'precipitation': None,  # Not available in current weather
                                    'wind_speed': None,     # Not available in basic plan
                                    'is_current': True
                                })
                                
                                # Store today's weather for future reference
                                await self.weather_service.store_daily_weather(location_id, current_weather, current_date)
                    except Exception as e:
                        logger.warning(f"Could not get current weather for day {day_num}: {str(e)}")
                        # Add placeholder for today without weather data
                        weather_data.append({
                            'day': day_num,
                            'date': current_date.strftime('%m/%d'),
                            'temp_high': None,
                            'temp_low': None,
                            'temp_avg': None,
                            'weather_main': None,
                            'weather_description': 'Weather data unavailable',
                            'weather_icon': None,
                            'humidity': None,
                            'precipitation': None,
                            'wind_speed': None,
                            'is_current': True
                        })
                else:
                    # Future day or past day without data - add placeholder
                    weather_data.append({
                        'day': day_num,
                        'date': current_date.strftime('%m/%d'),
                        'temp_high': None,
                        'temp_low': None,
                        'temp_avg': None,
                        'weather_main': None,
                        'weather_description': 'No data available',
                        'weather_icon': None,
                        'humidity': None,
                        'precipitation': None,
                        'wind_speed': None,
                        'is_current': False
                    })
                
                current_date += timedelta(days=1)
                day_num += 1
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Error getting season weather data: {str(e)}", exc_info=True)
            return []

    async def _get_combined_season_weather_data(self, session: AsyncSession, season_start: date, season_end: date, current_day: int) -> List[Dict[str, Any]]:
        """Get precipitation counts across all locations for each day of the season"""
        try:
            from app.utils.timezone import get_central_now
            from datetime import timedelta
            current_date = get_central_now().date()
            
            # Get all active locations
            locations = await self.get_all_locations()
            
            # Build weather data for each day of season
            weather_data = []
            day_date = season_start
            day_num = 1
            
            while day_date <= season_end and day_num <= current_day:
                precipitation_count = 0
                
                if day_date == current_date:
                    # For today, check current weather via API
                    for location in locations:
                        if location.get('address') and location['address'].get('postal_code'):
                            try:
                                weather = await self.weather_service.get_weather_by_zip(location['address']['postal_code'])
                                if weather:
                                    # Check for precipitation
                                    weather_main = weather.get('main', '').lower()
                                    if any(precip in weather_main for precip in ['rain', 'drizzle', 'thunderstorm', 'snow']):
                                        precipitation_count += 1
                            except Exception as e:
                                logger.warning(f"Could not get current weather for location {location['name']}: {str(e)}")
                else:
                    # For past days, check database
                    precip_query = """
                        SELECT COUNT(DISTINCT location_id) as precip_locations
                        FROM daily_weather 
                        WHERE date = :day_date 
                        AND (
                            precipitation > 0 
                            OR weather_main ILIKE '%rain%' 
                            OR weather_main ILIKE '%drizzle%' 
                            OR weather_main ILIKE '%thunderstorm%'
                            OR weather_main ILIKE '%snow%'
                        )
                    """
                    
                    result = await session.execute(text(precip_query), {"day_date": day_date})
                    row = result.fetchone()
                    precipitation_count = int(row[0]) if row and row[0] else 0
                
                weather_data.append({
                    'day': day_num,
                    'date': day_date.strftime('%m/%d'),
                    'precipitation_count': precipitation_count,
                    'is_current': day_date == current_date
                })
                
                day_date += timedelta(days=1)
                day_num += 1
            
            weather_summary = [f"Day {w['day']}: {w['precipitation_count']} locations" for w in weather_data[:3]]
            logger.info(f"Combined weather data for {len(weather_data)} days: {weather_summary}")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error getting combined season weather data: {str(e)}")
            return [] 