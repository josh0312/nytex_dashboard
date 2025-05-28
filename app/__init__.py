from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_models
from app.templates_config import templates

def create_app():
    app = FastAPI()
    
    # Initialize models
    init_models()
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Register routes
    from app.routes import dashboard_router, metrics_router, tools_router
    from app.routes.reports import reports_router
    from app.routes.catalog import router as catalog_router
    
    app.include_router(dashboard_router)
    app.include_router(metrics_router)
    app.include_router(reports_router)
    app.include_router(catalog_router)
    app.include_router(tools_router, prefix="/tools")
    
    return app
