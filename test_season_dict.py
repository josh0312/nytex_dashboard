from app.services.current_season import get_current_season

# Fetch the current season
def test_season_dict():
    season = get_current_season()
    print("Season dictionary:", season)

if __name__ == "__main__":
    test_season_dict() 