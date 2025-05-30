from sqlalchemy import select, func, cast, Integer, text, Date, JSON, and_, extract
from sqlalchemy.sql import column
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from app.logger import logger
from app.database.models.order import Order
from app.utils.timezone import CENTRAL_TZ
from contextlib import asynccontextmanager
from app.database.models.operating_season import OperatingSeason

class SeasonService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @asynccontextmanager
    async def _get_session_context(self):
        """Context manager to ensure proper session handling"""
        try:
            yield self.session
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise
        # Don't close the session - it's managed by the caller

    async def get_seasonal_sales(self, season):
        """Get daily sales totals and transaction counts for the given season."""
        if not season:
            logger.warning("No season provided")
            return None

        logger.info(f"Fetching sales for season: {season['name']} ({season['start_date']} to {season['end_date']})")
        logger.debug(f"Season start date type: {type(season['start_date'])}")
        logger.debug(f"Season end date type: {type(season['end_date'])}")

        try:
            async with self._get_session_context() as session:
                # Use SQLAlchemy ORM query builders
                today = date.today()
                yesterday = today - timedelta(days=1)
                date_series = select(
                    func.generate_series(
                        cast(season['start_date'], Date),
                        func.least(cast(season['end_date'], Date), cast(yesterday, Date)),
                        text("interval '1 day'")
                    ).label('order_date')
                ).alias('date_series')

                # Extract amount from total_money JSON using the correct JSON operator
                # The column is JSON type, not JSONB, so we use json_extract_path_text
                amount_expr = cast(
                    func.json_extract_path_text(
                        Order.total_money,
                        'amount'
                    ),
                    Integer
                )

                # Convert timestamps to Central timezone for comparison
                order_date_expr = func.timezone(
                    'America/Chicago',
                    Order.created_at
                )

                # Build the query using only the columns we need
                stmt = (
                    select(
                        date_series.c.order_date,
                        func.coalesce(func.count(func.distinct(Order.id)), 0).label('transaction_count'),
                        func.coalesce(func.sum(amount_expr), 0).label('total')
                    )
                    .select_from(
                        date_series.outerjoin(
                            Order.__table__,  # Use __table__ to avoid relationship loading
                            and_(
                                # Use date_trunc to compare just the date portion
                                cast(func.date_trunc('day', order_date_expr), Date) == date_series.c.order_date,
                                # Move the state condition into the join
                                Order.state != 'CANCELED'
                            )
                        )
                    )
                    .group_by(date_series.c.order_date)
                    .order_by(date_series.c.order_date)
                )

                logger.debug(f"Generated SQL: {stmt.compile(compile_kwargs={'literal_binds': True})}")
                result = await session.execute(stmt)
                rows = result.all()

                logger.info(f"Raw query returned {len(rows)} rows")
                if rows:
                    logger.debug(f"First row sample: {rows[0]}")
                    logger.debug(f"Last row sample: {rows[-1]}")

                if not rows:
                    return None

                dates = []
                amounts = []
                transactions = []

                for row in rows:
                    dates.append(row.order_date)
                    amount = float(row.total) / 100
                    amounts.append(amount)
                    transactions.append(row.transaction_count)
                    logger.debug(f"Processed row - Date: {row.order_date}, Amount: ${amount:.2f}, Transactions: {row.transaction_count}")

                return {
                    'dates': dates,
                    'amounts': amounts,
                    'transactions': transactions
                }

        except Exception as e:
            logger.error(f"Error fetching seasonal sales: {str(e)}", exc_info=True)
            logger.error(f"Season data: {season}")
            return None

    def generate_sparkline_path(self, daily_sales: list[dict]) -> str:
        """Generate SVG path data for the sparkline chart."""
        if not daily_sales:
            logger.warning("No daily sales data provided for sparkline")
            return ""

        # Get the dimensions
        totals = [day['total'] for day in daily_sales]
        max_total = max(totals) if totals else 0
        min_total = min(totals) if totals else 0
        range_total = max_total - min_total or 1  # Avoid division by zero

        logger.info(f"Generating sparkline with {len(daily_sales)} points. Min: {min_total}, Max: {max_total}")

        # Calculate points
        width = 100  # SVG viewBox width
        height = 24  # SVG viewBox height to match the container
        points = []
        
        for i, day in enumerate(daily_sales):
            x = (i / (len(daily_sales) - 1 or 1)) * width
            y = height - ((day['total'] - min_total) / range_total * height)
            points.append(f"{x},{y}")

        # Generate path
        path = f"M{points[0]} " + " ".join(f"L{point}" for point in points[1:])
        logger.info(f"Generated sparkline path: {path}")
        return path 

    async def get_yearly_season_totals(self):
        """Get order totals for each season grouped by year, from 2020 to current year."""
        try:
            logger.info("=== SERVICE: Starting get_yearly_season_totals method ===")
            
            try:
                async with self._get_session_context() as session:
                    logger.info("=== SERVICE: Session context manager entered successfully ===")
                    
                    try:
                        current_year = datetime.now().year
                        logger.info(f"=== SERVICE: Current year: {current_year} ===")
                        
                        # Extract amount from total_money JSON
                        try:
                            amount_expr = cast(
                                func.json_extract_path_text(
                                    Order.total_money,
                                    'amount'
                                ),
                                Integer
                            )
                            logger.info("=== SERVICE: Amount expression created successfully ===")
                        except Exception as e:
                            logger.error(f"=== SERVICE: Failed to create amount expression: {e} ===")
                            raise
                        
                        try:
                            # SQL query with year filtering
                            query = (
                                select([
                                    func.extract('year', Order.created_at).label('year'),
                                    func.extract('month', Order.created_at).label('month'),
                                    func.extract('day', Order.created_at).label('day'),
                                    func.count(Order.id).label('order_count'),
                                    func.sum(amount_expr).label('total_amount')
                                ])
                                .where(
                                    and_(
                                        func.extract('year', Order.created_at) >= 2020,
                                        func.extract('year', Order.created_at) <= current_year,
                                        Order.state == 'COMPLETED'
                                    )
                                )
                                .group_by(
                                    func.extract('year', Order.created_at),
                                    func.extract('month', Order.created_at),
                                    func.extract('day', Order.created_at)
                                )
                                .order_by(
                                    func.extract('year', Order.created_at),
                                    func.extract('month', Order.created_at),
                                    func.extract('day', Order.created_at)
                                )
                            )
                            logger.info("=== SERVICE: SQL query built successfully ===")
                        except Exception as e:
                            logger.error(f"=== SERVICE: Failed to build SQL query: {e} ===")
                            raise
                        
                        try:
                            logger.info("=== SERVICE: About to execute SQL query ===")
                            result = await session.execute(query)
                            logger.info("=== SERVICE: SQL query executed successfully ===")
                        except Exception as e:
                            logger.error(f"=== SERVICE: Failed to execute SQL query: {e} ===")
                            raise
                        
                        try:
                            rows = result.fetchall()
                            logger.info(f"=== SERVICE: SQL query returned {len(rows)} rows ===")
                        except Exception as e:
                            logger.error(f"=== SERVICE: Failed to fetch SQL results: {e} ===")
                            raise
                        
                        try:
                            # Group by year and season
                            logger.info("=== SERVICE: Starting to group results by year and season ===")
                            year_seasons = {}
                            
                            for row in rows:
                                year = int(row.year)
                                month = int(row.month)
                                day = int(row.day)
                                order_count = int(row.order_count)
                                amount = int(row.total_amount) if row.total_amount else 0
                                
                                if year not in year_seasons:
                                    year_seasons[year] = {}
                                
                                season_name = self._get_season_name_for_date(month, day)
                                
                                if season_name not in year_seasons[year]:
                                    year_seasons[year][season_name] = {
                                        'orders': 0,
                                        'amount': 0
                                    }
                                
                                year_seasons[year][season_name]['orders'] += order_count
                                year_seasons[year][season_name]['amount'] += amount
                            
                            logger.info(f"=== SERVICE: Grouped into {len(year_seasons)} years ===")
                        except Exception as e:
                            logger.error(f"=== SERVICE: Failed to group results: {e} ===")
                            raise
                        
                        try:
                            # Convert to final format
                            result_data = []
                            for year in sorted(year_seasons.keys()):
                                year_data = {'year': year, 'seasons': []}
                                
                                for season_name in ['New Year', 'Valentine\'s Day', 'Texas Independence Day', 'Easter', 'Memorial Day', 'July 4th', 'Labor Day', 'Halloween', 'Thanksgiving', 'Christmas']:
                                    if season_name in year_seasons[year]:
                                        season_data = year_seasons[year][season_name]
                                        year_data['seasons'].append({
                                            'name': season_name,
                                            'orders': season_data['orders'],
                                            'amount': season_data['amount'] / 100.0  # Convert from cents
                                        })
                                
                                result_data.append(year_data)
                            
                            logger.info(f"=== SERVICE: Final result has {len(result_data)} years ===")
                            return result_data
                        except Exception as e:
                            logger.error(f"=== SERVICE: Failed to convert to final format: {e} ===")
                            raise
                            
                    except Exception as e:
                        logger.error(f"=== SERVICE: Exception in main logic: {e} ===")
                        raise
                        
            except Exception as e:
                logger.error(f"=== SERVICE: Exception in session context: {e} ===")
                raise
                
        except Exception as e:
            logger.error(f"=== SERVICE: Top-level exception in get_yearly_season_totals: {type(e).__name__}: {e} ===")
            import traceback
            logger.error(f"=== SERVICE: Traceback: {traceback.format_exc()} ===")
            return None