from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.connection import get_db
from ..services.auth_service import AuthService
from ..database.schemas.auth import UserResponse
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = AuthService()
        self.public_paths = {
            "/auth/login",
            "/auth/callback",
            "/auth/logout",
            "/static",
            "/docs",
            "/openapi.json",
            "/redoc"
        }
        
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)
        
        # Check for session token in cookies
        session_token = request.cookies.get("session_token")
        
        if not session_token:
            # Redirect to login page
            return RedirectResponse(url="/auth/login", status_code=302)
        
        # Validate session
        try:
            async with get_db() as db:
                user = await self.auth_service.get_user_from_session(session_token, db)
                
                if not user:
                    # Invalid session, redirect to login
                    response = RedirectResponse(url="/auth/login", status_code=302)
                    response.delete_cookie("session_token")
                    return response
                
                # Add user to request state
                request.state.user = user
                
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            response = RedirectResponse(url="/auth/login", status_code=302)
            response.delete_cookie("session_token")
            return response
        
        return await call_next(request)

def get_current_user(request: Request) -> UserResponse:
    """Get current user from request state"""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user 