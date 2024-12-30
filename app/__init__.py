from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import init_models

def create_app():
    app = FastAPI()
    
    # Initialize models
    init_models()
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Set up templates
    templates = Jinja2Templates(directory="app/templates")
    
    # Register routes
    from app.routes import dashboard_router
    app.include_router(dashboard_router)
    
    return app
