import asyncio
from app.database import get_session
from app.database.models.operating_season import OperatingSeason
from sqlalchemy import select, update
from datetime import datetime
from sqlalchemy.sql import text

async def update_july_4th_seasons():
    """Update all July 4th seasons to run from June 24th to July 4th"""
    async with get_session() as session:
        # First, get all July 4th seasons
        stmt = select(OperatingSeason).where(OperatingSeason.name == 'July 4th')
        result = await session.execute(stmt)
        seasons = result.scalars().all()
        
        for season in seasons:
            # Get the year from the existing start_date
            year = season.start_date.year
            
            # Update the dates
            season.start_date = datetime(year, 6, 24).date()
            season.end_date = datetime(year, 7, 4).date()
            season.rule_description = 'Season runs from June 24th to July 4th'
            
        await session.commit()
        
        # Log the updated seasons
        result = await session.execute(stmt)
        updated_seasons = result.scalars().all()
        for season in updated_seasons:
            print(f"Updated {season.name} {season.start_date.year}: {season.start_date} to {season.end_date}")

if __name__ == "__main__":
    asyncio.run(update_july_4th_seasons()) 