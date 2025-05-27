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
        finally:
            await self.session.close()

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
            async with self._get_session_context() as session:
                current_year = datetime.now().year
                
                # Extract amount from total_money JSON
                amount_expr = cast(
                    func.json_extract_path_text(
                        Order.total_money,
                        'amount'
                    ),
                    Integer
                )
                
                # Convert timestamps to Central timezone for comparison
                order_date_expr = cast(
                    text("(orders.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')"),
                    Date
                )
                
                # Query to get seasons and their order totals
                stmt = (
                    select(
                        extract('year', OperatingSeason.start_date).label('year'),
                        OperatingSeason.name,
                        OperatingSeason.start_date,
                        OperatingSeason.end_date,
                        func.count(Order.id).label('order_count'),
                        func.coalesce(func.sum(amount_expr), 0).label('total_amount')
                    )
                    .select_from(OperatingSeason)
                    .outerjoin(
                        Order,
                        and_(
                            order_date_expr >= OperatingSeason.start_date,
                            order_date_expr <= OperatingSeason.end_date,
                            Order.state != 'CANCELED'
                        )
                    )
                    .where(
                        and_(
                            extract('year', OperatingSeason.start_date) >= 2020,
                            extract('year', OperatingSeason.start_date) <= current_year
                        )
                    )
                    .group_by(
                        extract('year', OperatingSeason.start_date),
                        OperatingSeason.name,
                        OperatingSeason.start_date,
                        OperatingSeason.end_date
                    )
                    .order_by(
                        extract('year', OperatingSeason.start_date).desc(),
                        OperatingSeason.start_date
                    )
                )

                # Log the SQL query with actual values
                compiled_query = stmt.compile(compile_kwargs={"literal_binds": True})
                logger.info(f"Generated SQL Query:\n{str(compiled_query)}")

                result = await session.execute(stmt)
                seasons = result.all()
                
                # Log raw results before processing
                logger.info("Raw results from database:")
                for season in seasons:
                    logger.info(
                        f"Year: {season.year}, Name: {season.name}, "
                        f"Date Range: {season.start_date} to {season.end_date}, "
                        f"Orders: {season.order_count}, "
                        f"Amount: ${float(season.total_amount)/100:.2f}"
                    )
                
                # Group results by year
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
                return [
                    {
                        'year': year,
                        'seasons': seasons_list
                    }
                    for year, seasons_list in sorted(years_dict.items(), reverse=True)
                ]

        except Exception as e:
            logger.error(f"Error fetching yearly season totals: {str(e)}", exc_info=True)
            return None 