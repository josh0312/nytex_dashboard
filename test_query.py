from app.services.season_service import SeasonService
from app.database import get_session
from app.services.current_season import get_current_season
import asyncio

async def test_query():
    current_season = get_current_season()
    print(f"Current season: {current_season}")
    async with get_session() as session:
        service = SeasonService(session)
        result = await service.get_seasonal_sales(current_season)
        print(f"Query result: {result}")

if __name__ == "__main__":
    asyncio.run(test_query()) 