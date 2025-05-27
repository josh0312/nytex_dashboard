from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .routes.dashboard import router as dashboard_router
from .routes.metrics import router as metrics_router
from .routes.reports import router as reports_router
from .middleware.template_monitor import TemplateMonitorMiddleware
from .services.monitor_service import monitor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(title="NyTex Dashboard")

# Add middleware
app.add_middleware(TemplateMonitorMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(dashboard_router)
app.include_router(metrics_router)
app.include_router(reports_router)

# Root redirect
@app.get("/")
async def root():
    return {"message": "Welcome to NyTex Dashboard"} 