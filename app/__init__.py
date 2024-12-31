from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import init_models
from app.filters import filters

def create_app():
    app = FastAPI()
    
    # Initialize models
    init_models()
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Set up templates with custom filters
    templates = Jinja2Templates(directory="app/templates")
    for name, func in filters.items():
        templates.env.filters[name] = func
    
    # Register routes
    from app.routes import dashboard_router, metrics_router
    from app.routes.reports import reports_router
    
    app.include_router(dashboard_router)
    app.include_router(metrics_router)
    app.include_router(reports_router)
    
    return app
