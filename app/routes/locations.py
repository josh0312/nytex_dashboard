from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.location_service import LocationService
from app.templates_config import templates
from app.logger import logger

router = APIRouter()

@router.get("/weather_summary")
async def locations_weather_summary(request: Request):
    """Get weather summary across all locations (HTMX endpoint)"""
    try:
        from app.services.weather_service import WeatherService
        
        location_service = LocationService()
        weather_service = WeatherService()
        
        # Get all locations
        locations = await location_service.get_all_locations()
        
        # Calculate weather stats across all locations
        rain_count = 0
        clear_count = 0
        temps = []
        weather_data_count = 0
        
        for location in locations:
            if location.get('address') and location['address'].get('postal_code'):
                try:
                    weather = await weather_service.get_weather_by_zip(location['address']['postal_code'])
                    if weather:
                        weather_data_count += 1
                        
                        # Check for rain/precipitation
                        weather_main = weather.get('main', '').lower()
                        if 'rain' in weather_main or 'drizzle' in weather_main or 'thunderstorm' in weather_main:
                            rain_count += 1
                        elif 'clear' in weather_main or 'sun' in weather_main or 'few clouds' in weather_main:
                            clear_count += 1
                        
                        # Collect temperature
                        if weather.get('temp'):
                            temps.append(weather['temp'])
                            
                except Exception as e:
                    logger.warning(f"Could not get weather for location {location['name']}: {str(e)}")
        
        # Calculate averages
        avg_temp = sum(temps) / len(temps) if temps else None
        data_coverage = round((weather_data_count / len(locations)) * 100) if locations else 0
        
        # Return compact weather display for header
        return templates.TemplateResponse("dashboard/components/weather_summary.html", {
            "request": request,
            "weather_stats": {
                'rain_count': rain_count,
                'clear_count': clear_count,
                'avg_temp': avg_temp,
                'data_coverage': data_coverage,
                'total_locations': len(locations)
            }
        })
    except Exception as e:
        logger.error(f"Error getting weather summary: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load weather summary"
        })

@router.get("/all/current")
async def all_locations_current_metrics(request: Request):
    """Get combined current metrics for all locations (HTMX endpoint)"""
    try:
        location_service = LocationService()
        
        # Get aggregated data for all locations
        all_locations_data = await location_service.get_all_locations_overview()
        
        return templates.TemplateResponse("locations/components/current_metrics.html", {
            "request": request,
            "current": all_locations_data['current'],
            "location": {"name": "All Locations Combined", "id": "all"}
        })
    except Exception as e:
        logger.error(f"Error getting all locations current metrics: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load combined metrics"
        })

@router.get("/all/historical")
async def all_locations_historical_data(request: Request):
    """Get combined historical data for all locations (HTMX endpoint)"""
    try:
        location_service = LocationService()
        
        # Get aggregated historical data for all locations
        all_locations_data = await location_service.get_all_locations_overview()
        
        return templates.TemplateResponse("locations/components/historical_data.html", {
            "request": request,
            "historical": all_locations_data['historical'],
            "location": {"name": "All Locations Combined", "id": "all"}
        })
    except Exception as e:
        logger.error(f"Error getting all locations historical data: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load combined historical data"
        })

@router.get("/all/inventory")
async def all_locations_inventory_summary(request: Request):
    """Get combined inventory summary for all locations (HTMX endpoint)"""
    try:
        location_service = LocationService()
        
        # Get aggregated inventory data for all locations
        all_locations_data = await location_service.get_all_locations_overview()
        
        return templates.TemplateResponse("locations/components/inventory_summary.html", {
            "request": request,
            "inventory": all_locations_data['inventory'],
            "location": {"name": "All Locations Combined", "id": "all"}
        })
    except Exception as e:
        logger.error(f"Error getting all locations inventory: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load combined inventory data"
        })

@router.get("/")
async def locations_index(request: Request):
    """Locations index page showing all locations"""
    try:
        logger.info("Loading locations index page")
        location_service = LocationService()
        locations = await location_service.get_all_locations()
        
        # Get basic stats for each location from today's Square data
        location_stats = []
        try:
            # Try to get current data but don't fail if Square API is not available
            for location in locations:
                # For now, we'll just show the location info
                # Current sales will be added later via HTMX if Square API is available
                location_stats.append({
                    **location,
                    'today_sales': 0,
                    'today_orders': 0,
                    'weather': None
                })
        except Exception as e:
            logger.warning(f"Could not get current location stats: {str(e)}")
            location_stats = locations
        
        return templates.TemplateResponse("locations/index.html", {
            "request": request,
            "locations": location_stats
        })
    except Exception as e:
        logger.error(f"Error loading locations index: {str(e)}", exc_info=True)
        return templates.TemplateResponse("components/shared/error.html", {
            "request": request,
            "title": "Locations",
            "message": "Unable to load locations"
        })

@router.get("/{location_id}")
async def location_detail(request: Request, location_id: str):
    """Individual location detail page"""
    try:
        logger.info(f"Loading location detail page for {location_id}")
        location_service = LocationService()
        location_data = await location_service.get_location_overview(location_id)
        
        if not location_data:
            raise HTTPException(status_code=404, detail="Location not found")
        
        return templates.TemplateResponse("locations/detail.html", {
            "request": request,
            "location_data": location_data
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading location detail for {location_id}: {str(e)}", exc_info=True)
        return templates.TemplateResponse("components/shared/error.html", {
            "request": request,
            "title": "Location Detail",
            "message": f"Unable to load location details"
        })

@router.get("/{location_id}/current")
async def location_current_metrics(request: Request, location_id: str):
    """Get current metrics for a location (HTMX endpoint)"""
    try:
        location_service = LocationService()
        location_data = await location_service.get_location_overview(location_id)
        
        if not location_data:
            return templates.TemplateResponse("locations/components/error.html", {
                "request": request,
                "message": "Location not found"
            })
        
        return templates.TemplateResponse("locations/components/current_metrics.html", {
            "request": request,
            "current": location_data['current'],
            "location": location_data['location']
        })
    except Exception as e:
        logger.error(f"Error getting current metrics for {location_id}: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load current metrics"
        })

@router.get("/{location_id}/historical")
async def location_historical_data(request: Request, location_id: str):
    """Get historical data for a location (HTMX endpoint)"""
    try:
        location_service = LocationService()
        location_data = await location_service.get_location_overview(location_id)
        
        if not location_data:
            return templates.TemplateResponse("locations/components/error.html", {
                "request": request,
                "message": "Location not found"
            })
        
        return templates.TemplateResponse("locations/components/historical_data.html", {
            "request": request,
            "historical": location_data['historical'],
            "location": location_data['location']
        })
    except Exception as e:
        logger.error(f"Error getting historical data for {location_id}: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load historical data"
        })

@router.get("/{location_id}/highlights")
async def location_highlights(request: Request, location_id: str):
    """Get basic highlights for a location (HTMX endpoint for index page)"""
    try:
        location_service = LocationService()
        location_data = await location_service.get_location_overview(location_id)
        
        if not location_data:
            return templates.TemplateResponse("locations/components/error.html", {
                "request": request,
                "message": "Location not found"
            })
        
        return templates.TemplateResponse("locations/components/highlights.html", {
            "request": request,
            "current": location_data['current'],
            "location": location_data['location']
        })
    except Exception as e:
        logger.error(f"Error getting highlights for {location_id}: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load highlights"
        })

@router.get("/{location_id}/inventory")
async def location_inventory_summary(request: Request, location_id: str):
    """Get inventory summary for a location (HTMX endpoint)"""
    try:
        location_service = LocationService()
        location_data = await location_service.get_location_overview(location_id)
        
        if not location_data:
            return templates.TemplateResponse("locations/components/error.html", {
                "request": request,
                "message": "Location not found"
            })
        
        return templates.TemplateResponse("locations/components/inventory_summary.html", {
            "request": request,
            "inventory": location_data['inventory'],
            "location": location_data['location']
        })
    except Exception as e:
        logger.error(f"Error getting inventory summary for {location_id}: {str(e)}")
        return templates.TemplateResponse("locations/components/error.html", {
            "request": request,
            "message": "Unable to load inventory data"
        }) 