from sqlalchemy.future import select
from app.database.connection import get_db
from app.database.models.operating_season import OperatingSeason
from app.logger import logger
from datetime import datetime

async def get_current_season():
    """Get the current operating season based on today's date"""
    async with get_db() as session:
        today = datetime.now().date()
        logger.info(f"Checking for active season on date: {today}")

        stmt = select(OperatingSeason).where(
            OperatingSeason.start_date <= today,
            OperatingSeason.end_date >= today
        ).order_by(OperatingSeason.start_date.desc()).limit(1)

        logger.debug(f"Executing query to find active season for date: {today}")

        result = await session.execute(stmt)
        season = result.scalars().first()

        logger.debug(f"Query result: {season}")

        if season:
            logger.info(f"Found active season: {season.name} ({season.start_date} to {season.end_date})")
            return {
                'id': season.id,
                'name': season.name,
                'start_date': season.start_date,
                'end_date': season.end_date
            }
        else:
            logger.warning("No active season found")
            return None 