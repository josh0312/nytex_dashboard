from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class ProxyHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle proxy headers from Cloud Run.
    
    Cloud Run sends requests with X-Forwarded-Proto: https but FastAPI
    doesn't automatically use this for url_for() generation, causing
    mixed content issues.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check for proxy headers
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host")
        
        if forwarded_proto:
            # Update the request URL scheme
            request.scope["scheme"] = forwarded_proto
            logger.debug(f"Updated scheme to: {forwarded_proto}")
        
        if forwarded_host:
            # Update the request host
            request.scope["server"] = (forwarded_host, 443 if forwarded_proto == "https" else 80)
            logger.debug(f"Updated host to: {forwarded_host}")
        
        response = await call_next(request)
        return response 