from fastapi import APIRouter, Request, Form, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.connection import get_db_session
from ..services.auth_service import AuthService
from ..database.schemas.auth import LoginRequest, UserCreate
from ..middleware.auth_middleware import get_current_user
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
templates = Jinja2Templates(directory="app/templates")
auth_service = AuthService()

# Determine if we're in production
IS_PRODUCTION = os.getenv("ENVIRONMENT") == "production"

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """Display login page"""
    # Get O365 login URL (may be None if not configured)
    o365_auth_url = auth_service.get_o365_auth_url()
    
    # Only show O365 option if properly configured
    o365_enabled = o365_auth_url is not None
    
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "o365_auth_url": o365_auth_url,
        "o365_enabled": o365_enabled,
        "error": error
    })

@router.post("/login")
async def manual_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Handle manual user login"""
    try:
        # Authenticate user
        user = await auth_service.authenticate_manual_user(email, password, db)
        
        if not user:
            return RedirectResponse(
                url="/auth/login?error=Invalid credentials",
                status_code=302
            )
        
        # Create session
        user_agent = request.headers.get("user-agent", "")
        session_token = await auth_service.create_session(user.id, db, user_agent)
        
        # Redirect to dashboard
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=IS_PRODUCTION,  # Only secure in production
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in manual login: {str(e)}")
        return RedirectResponse(
            url="/auth/login?error=Login failed",
            status_code=302
        )

@router.get("/callback")
async def o365_callback(
    request: Request,
    code: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle O365 authentication callback"""
    if error:
        logger.error(f"O365 authentication error: {error}")
        return RedirectResponse(
            url="/auth/login?error=O365 authentication failed",
            status_code=302
        )
    
    if not code:
        return RedirectResponse(
            url="/auth/login?error=Missing authorization code",
            status_code=302
        )
    
    try:
        # Authenticate with O365
        user = await auth_service.authenticate_o365_callback(code, db)
        
        if not user:
            return RedirectResponse(
                url="/auth/login?error=O365 authentication failed",
                status_code=302
            )
        
        # Create session
        user_agent = request.headers.get("user-agent", "")
        session_token = await auth_service.create_session(user.id, db, user_agent)
        
        # Redirect to dashboard
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=IS_PRODUCTION,  # Only secure in production
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in O365 callback: {str(e)}")
        return RedirectResponse(
            url="/auth/login?error=Authentication failed",
            status_code=302
        )

@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Logout user and invalidate session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await auth_service.invalidate_session(session_token, db)
    
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("session_token")
    
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Display user profile page"""
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "user": current_user
    })

# Admin routes for user management (you can protect these with additional checks)
@router.post("/create-manual-user")
async def create_manual_user_endpoint(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None),
    username: str = Form(None),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Create a new manual user (admin only)"""
    # You can add admin check here if needed
    
    user_data = UserCreate(
        email=email,
        password=password,
        full_name=full_name,
        username=username
    )
    
    user = await auth_service.create_manual_user(user_data, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed"
        )
    
    return {"message": "User created successfully", "user": user} 