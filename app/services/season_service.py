from sqlalchemy import select, func, cast, Integer, text
from sqlalchemy.sql import column
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.logger import logger
from app.models import Order  # Assuming Order is the model for the orders table

class SeasonService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_seasonal_sales(self, season):
        """Get daily sales totals and transaction counts for the given season."""
        if not season:
            logger.warning("No season provided")
            return None

        logger.info(f"Fetching sales for season: {season['name']} ({season['start_date']} to {season['end_date']})")

        # Use SQLAlchemy ORM query builders
        date_series = select(
            func.generate_series(
                season['start_date'],
                season['end_date'],
                text("'1 day'")
            ).label('order_date')
        ).alias('date_series')

        stmt = (
            select(
                date_series.c.order_date,
                func.coalesce(func.count(func.distinct(Order.id)), 0).label('transaction_count'),
                func.coalesce(func.sum(Order.total_amount), 0).label('total')
            )
            .select_from(date_series.outerjoin(
                Order,
                func.date(Order.order_date.op('AT TIME ZONE')('America/Chicago')) == date_series.c.order_date
            ))
            .group_by(date_series.c.order_date)
            .order_by(date_series.c.order_date)
        )

        try:
            result = await self.session.execute(stmt)
            rows = result.all()  # Use .all() to fetch all rows

            logger.info(f"Raw query returned {len(rows)} rows")

            if not rows:
                return None

            dates = []
            amounts = []
            transactions = []

            for row in rows:
                dates.append(row.order_date)
                amounts.append(float(row.total) / 100)
                transactions.append(row.transaction_count)

            return {
                'dates': dates,
                'amounts': amounts,
                'transactions': transactions
            }

        except Exception as e:
            logger.error(f"Error fetching seasonal sales: {str(e)}", exc_info=True)
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