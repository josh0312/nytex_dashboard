from fastapi import Request, Response
from typing import Optional, Dict, Any
import logging
import json
import time
from datetime import datetime
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

class MonitorService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_history = []
        self.error_history = []
        self.template_history = []
        self.htmx_history = []

    def log_request(self, request: Request, response: Response, duration: float):
        """Log details about a request/response cycle"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "headers": dict(request.headers),
            "is_htmx": "HX-Request" in request.headers,
            "client": request.client.host if request.client else None
        }
        self.request_history.append(entry)
        self.logger.info(f"Request: {json.dumps(entry, indent=2)}")
        return entry

    def log_error(self, error: Exception, request: Optional[Request] = None):
        """Log details about an error"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "url": str(request.url) if request else None,
            "method": request.method if request else None,
            "headers": dict(request.headers) if request else None
        }
        self.error_history.append(entry)
        self.logger.error(f"Error: {json.dumps(entry, indent=2)}")
        return entry

    def log_template_render(self, template_name: str, context: Dict[str, Any], duration: float):
        """Log details about template rendering"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "template": template_name,
            "context_keys": list(context.keys()),
            "duration_ms": round(duration * 1000, 2)
        }
        self.template_history.append(entry)
        self.logger.info(f"Template Render: {json.dumps(entry, indent=2)}")
        return entry

    def log_htmx_event(self, event_type: str, details: Dict[str, Any]):
        """Log HTMX-specific events"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        self.htmx_history.append(entry)
        self.logger.info(f"HTMX Event: {json.dumps(entry, indent=2)}")
        return entry

    def get_recent_errors(self, limit: int = 10) -> list:
        """Get most recent errors"""
        return self.error_history[-limit:]

    def get_recent_requests(self, limit: int = 10) -> list:
        """Get most recent requests"""
        return self.request_history[-limit:]

    def get_template_stats(self) -> Dict[str, Any]:
        """Get statistics about template rendering"""
        if not self.template_history:
            return {}

        stats = {}
        for entry in self.template_history:
            template = entry["template"]
            if template not in stats:
                stats[template] = {
                    "count": 0,
                    "total_duration_ms": 0,
                    "avg_duration_ms": 0
                }
            stats[template]["count"] += 1
            stats[template]["total_duration_ms"] += entry["duration_ms"]
            stats[template]["avg_duration_ms"] = (
                stats[template]["total_duration_ms"] / stats[template]["count"]
            )
        return stats

    def get_htmx_stats(self) -> Dict[str, Any]:
        """Get statistics about HTMX events"""
        if not self.htmx_history:
            return {}

        stats = {}
        for entry in self.htmx_history:
            event_type = entry["event_type"]
            if event_type not in stats:
                stats[event_type] = {
                    "count": 0,
                    "details": []
                }
            stats[event_type]["count"] += 1
            stats[event_type]["details"].append(entry["details"])
        return stats

# Create a global instance
monitor = MonitorService()

# Decorator for monitoring routes
def monitor_route(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        request = None
        try:
            # Find the request object in args or kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]

            # Execute the route
            response = await func(*args, **kwargs)
            
            # Log the request/response
            duration = time.time() - start_time
            if request:
                monitor.log_request(request, response, duration)
            
            return response
        except Exception as e:
            # Log any errors
            if request:
                monitor.log_error(e, request)
            raise
    return wrapper 