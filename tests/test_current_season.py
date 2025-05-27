import asyncio
from app.services.current_season import get_current_season
from app.services.season_service import SeasonService
from app.database import get_session
from app.logger import logger

async def test_current_season():
    logger.info("Testing get_current_season()")
    season = await get_current_season()
    logger.info(f"Current season: {season}")
    
    logger.info("\nTesting seasonal sales...")
    async with get_session() as session:
        season_service = SeasonService(session)
        sales_data = await season_service.get_seasonal_sales(season)
        logger.info(f"Sales data: {sales_data}")
    
    return {
        'season': season,
        'sales_data': sales_data
    }

if __name__ == "__main__":
    result = asyncio.run(test_current_season())
    print("\nResult:", result) 