from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from .routes.dashboard import router as dashboard_router
from .routes.metrics import router as metrics_router
from .routes.reports import reports_router
from .routes.catalog import router as catalog_router
from .routes.auth import router as auth_router
from .middleware.template_monitor import TemplateMonitorMiddleware
from .middleware.auth_middleware import AuthMiddleware
from .services.monitor_service import monitor
from .database import init_models
import logging

# Import additional routes from original app
from .routes import tools_router, admin_router, locations_router
from .routes.items_routes import router as items_router
from .routes.inventory import router as inventory_router

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

app = FastAPI(title="NyTex Dashboard", version="1.0.0")

# Initialize models
init_models()

# Add authentication middleware first
app.add_middleware(AuthMiddleware)
app.add_middleware(TemplateMonitorMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers (auth first, then all others)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(reports_router, prefix="/reports", tags=["reports"])
app.include_router(catalog_router, prefix="/catalog", tags=["catalog"])
app.include_router(tools_router, prefix="/tools")
app.include_router(items_router, prefix="/items")
app.include_router(inventory_router, prefix="/inventory")
app.include_router(locations_router, prefix="/locations")
app.include_router(admin_router)  # Admin routes with /admin prefix

# Root redirect to dashboard
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard", status_code=302) 