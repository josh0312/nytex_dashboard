from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from fastapi import Request
import time
from ..services.monitor_service import monitor

class TemplateMonitorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Store the original TemplateResponse.init
        from starlette.templating import _TemplateResponse
        original_init = _TemplateResponse.__init__

        # Wrap the init to capture template rendering
        def wrapped_init(self, template, context, *args, **kwargs):
            start_time = time.time()
            original_init(self, template, context, *args, **kwargs)
            duration = time.time() - start_time
            monitor.log_template_render(template.name, context, duration)

        # Replace the init
        _TemplateResponse.__init__ = wrapped_init

        try:
            # Process the request
            response = await call_next(request)
            return response
        finally:
            # Restore the original init
            _TemplateResponse.__init__ = original_init 