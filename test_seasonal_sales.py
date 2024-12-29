import asyncio
from app.services.season_service import SeasonService
from app.database import get_session
from app.services.current_season import get_current_season

async def test_get_seasonal_sales():
    # Fetch the current season
    season = get_current_season()
    print(f"Testing with season: {season}")

    # Create a session and call the method
    async with get_session() as session:
        service = SeasonService(session)
        result = await service.get_seasonal_sales(season)
        print("Seasonal Sales Result:", result)

if __name__ == "__main__":
    asyncio.run(test_get_seasonal_sales()) 