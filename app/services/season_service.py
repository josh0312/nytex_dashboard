import os
import asyncio
from datetime import datetime, timezone, date
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, select, func, cast, Integer, Date, and_, desc
from contextlib import asynccontextmanager

from app.database.models.order import Order
from app.database.models.location import Location
from app.logger import logger
from app.utils.timezone import convert_utc_to_central, CENTRAL_TZ

class SeasonService:
    def __init__(self, session: AsyncSession = None):
        self.session = session
        if not session:
            # Fallback to creating our own connection if no session provided
            self.database_url = os.getenv('DATABASE_URL')
            if not self.database_url:
                raise ValueError("DATABASE_URL environment variable is required")
            
            # Handle both sync and async database URLs
            if self.database_url.startswith('postgresql://'):
                self.database_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
            elif not self.database_url.startswith('postgresql+asyncpg://'):
                self.database_url = 'postgresql+asyncpg://' + self.database_url
            
            self.engine = create_async_engine(self.database_url, echo=False)
            self.SessionLocal = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def _get_session_context(self):
        """Async context manager for database sessions"""
        if self.session:
            # Use the provided session
            yield self.session
        else:
            # Create our own session
            async with self.SessionLocal() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

    def _get_season_date_ranges(self, year: int) -> Dict[str, Tuple[date, date]]:
        """
        Get date ranges for each season in Central Time.
        These dates represent when seasons occur in Central Time zone.
        """
        return {
            'Spring': (date(year, 3, 20), date(year, 6, 20)),  # Mar 20 - Jun 20
            'Summer': (date(year, 6, 21), date(year, 9, 21)),  # Jun 21 - Sep 21  
            'Fall': (date(year, 9, 22), date(year, 12, 20)),   # Sep 22 - Dec 20
            'Winter': (date(year, 12, 21), date(year + 1, 3, 19)) if year < datetime.now().year else (date(year - 1, 12, 21), date(year, 3, 19))  # Dec 21 - Mar 19
        }

    def _categorize_season(self, order_date: date) -> str:
        """Categorize a date into a season based on Central Time"""
        year = order_date.year
        
        # Handle winter season that spans years
        if order_date.month in [12] or (order_date.month <= 3 and order_date.day <= 19):
            # Winter: Dec 21 - Mar 19
            if order_date.month == 12 and order_date.day >= 21:
                return 'Winter'
            elif order_date.month <= 3 and order_date.day <= 19:
                return 'Winter'
        
        # Get season ranges for this year
        season_ranges = self._get_season_date_ranges(year)
        
        for season, (start_date, end_date) in season_ranges.items():
            if season == 'Winter':
                continue  # Already handled above
                
            if start_date <= order_date <= end_date:
                return season
        
        return 'Unknown'

    async def get_season_totals(self):
        """Get order totals for each season in the current year"""
        try:
            async with self._get_session_context() as session:
                current_year = datetime.now().year
                
                # Get all orders for the current year with location timezone info
                query = """
                    SELECT 
                        o.created_at,
                        COALESCE(CAST(o.total_money->>'amount' AS INTEGER), 0) as amount,
                        l.timezone as location_timezone
                    FROM orders o
                    LEFT JOIN locations l ON o.location_id = l.id
                    WHERE EXTRACT(YEAR FROM o.created_at) = :year
                    AND o.state = 'COMPLETED'
                    ORDER BY o.created_at
                """
                
                result = await session.execute(text(query), {"year": current_year})
                orders = result.fetchall()
                
                # Initialize season totals
                season_totals = {
                    'Spring': 0,
                    'Summer': 0, 
                    'Fall': 0,
                    'Winter': 0
                }
                
                # Process each order
                for order in orders:
                    created_at, amount, location_timezone = order
                    
                    # Convert UTC stored time to Central Time for proper season categorization
                    if created_at:
                        central_dt = convert_utc_to_central(created_at)
                        order_date = central_dt.date()
                        
                        season = self._categorize_season(order_date)
                        if season in season_totals:
                            # Convert amount from cents to dollars
                            season_totals[season] += (amount or 0) / 100
                
                logger.info(f"Season totals calculated for {current_year}: {season_totals}")
                return season_totals
                
        except Exception as e:
            logger.error(f"Error getting season totals: {str(e)}", exc_info=True)
            return {'Spring': 0, 'Summer': 0, 'Fall': 0, 'Winter': 0}

    async def get_yearly_season_totals(self):
        """Get order totals for each season grouped by year, from 2020 to current year."""
        try:
            async with self._get_session_context() as session:
                current_year = datetime.now().year
                
                # Get all orders from 2020 to current year with location timezone info
                query = """
                    SELECT 
                        o.created_at,
                        COALESCE(CAST(o.total_money->>'amount' AS INTEGER), 0) as amount,
                        l.timezone as location_timezone
                    FROM orders o
                    LEFT JOIN locations l ON o.location_id = l.id
                    WHERE EXTRACT(YEAR FROM o.created_at) >= 2020
                    AND EXTRACT(YEAR FROM o.created_at) <= :current_year
                    AND o.state = 'COMPLETED'
                    ORDER BY o.created_at
                """
                
                result = await session.execute(text(query), {"current_year": current_year})
                orders = result.fetchall()
                
                # Initialize yearly season totals
                yearly_totals = {}
                
                # Process each order
                for order in orders:
                    created_at, amount, location_timezone = order
                    
                    if created_at:
                        # Convert UTC stored time to Central Time for proper season categorization
                        central_dt = convert_utc_to_central(created_at)
                        order_date = central_dt.date()
                        order_year = order_date.year
                        
                        # Initialize year if not exists
                        if order_year not in yearly_totals:
                            yearly_totals[order_year] = {
                                'Spring': 0,
                                'Summer': 0,
                                'Fall': 0,
                                'Winter': 0
                            }
                        
                        season = self._categorize_season(order_date)
                        if season in yearly_totals[order_year]:
                            # Convert amount from cents to dollars
                            yearly_totals[order_year][season] += (amount or 0) / 100
                
                logger.info(f"Yearly season totals calculated: {yearly_totals}")
                return yearly_totals
                
        except Exception as e:
            logger.error(f"Error getting yearly season totals: {str(e)}", exc_info=True)
            return {}

    async def get_seasonal_sales(self, current_season):
        """Get daily sales data for the current season"""
        try:
            if not current_season:
                logger.warning("No current season provided")
                return None
                
            async with self._get_session_context() as session:
                logger.info(f"Getting seasonal sales for {current_season['name']} ({current_season['start_date']} to {current_season['end_date']})")
                
                # Query daily sales within the season date range
                query = """
                    SELECT 
                        DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') as order_date,
                        SUM(COALESCE(CAST(o.total_money->>'amount' AS INTEGER), 0)) as daily_amount,
                        COUNT(*) as daily_transactions
                    FROM orders o
                    WHERE o.state = 'COMPLETED'
                    AND DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') >= :start_date
                    AND DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') <= :end_date
                    GROUP BY DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')
                    ORDER BY order_date
                """
                
                result = await session.execute(text(query), {
                    "start_date": current_season['start_date'],
                    "end_date": current_season['end_date']
                })
                daily_sales = result.fetchall()
                
                if not daily_sales:
                    logger.warning(f"No sales data found for season {current_season['name']}")
                    return None
                
                # Process the results
                dates = []
                amounts = []
                transactions = []
                
                for row in daily_sales:
                    order_date, daily_amount, daily_transactions = row
                    dates.append(order_date)
                    # Convert from cents to dollars
                    amounts.append((daily_amount or 0) / 100)
                    transactions.append(daily_transactions or 0)
                
                logger.info(f"Found {len(dates)} days of sales data for season {current_season['name']}")
                
                return {
                    'dates': dates,
                    'amounts': amounts,
                    'transactions': transactions
                }
                
        except Exception as e:
            logger.error(f"Error getting seasonal sales: {str(e)}", exc_info=True)
            return None

    async def close(self):
        """Close database connections"""
        if hasattr(self, 'engine'):
            await self.engine.dispose() 