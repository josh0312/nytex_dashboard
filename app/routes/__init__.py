from app.routes.dashboard import router as dashboard_router
from app.routes.metrics import router as metrics_router
from app.routes.tools import router as tools_router
from app.routes.admin import router as admin_router

__all__ = ['dashboard_router', 'metrics_router', 'tools_router', 'admin_router'] 