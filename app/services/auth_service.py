from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
import msal
import httpx
from jose import JWTError, jwt
from ..database.models.auth import User, Session
from ..database.schemas.auth import UserCreate, UserResponse
from ..config import Config
import secrets
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.o365_client_id = Config.AZURE_CLIENT_ID
        self.o365_client_secret = Config.AZURE_CLIENT_SECRET
        self.o365_tenant_id = Config.AZURE_TENANT_ID
        self.redirect_uri = Config.AZURE_REDIRECT_URI
        self.secret_key = Config.SECRET_KEY
        self.algorithm = "HS256"
        self.session_expire_hours = 24
        
        # Check if O365 is properly configured
        self.o365_enabled = all([
            self.o365_client_id,
            self.o365_client_secret,
            self.o365_tenant_id,
            self.redirect_uri
        ])
        
    def get_msal_app(self):
        """Create MSAL confidential client application"""
        if not self.o365_enabled:
            raise ValueError("O365 authentication not configured - missing required environment variables")
            
        return msal.ConfidentialClientApplication(
            self.o365_client_id,
            authority=f"https://login.microsoftonline.com/{self.o365_tenant_id}",
            client_credential=self.o365_client_secret,
        )
    
    def get_o365_auth_url(self, state: str = None) -> Optional[str]:
        """Get O365 authorization URL"""
        if not self.o365_enabled:
            logger.warning("O365 authentication not configured")
            return None
            
        try:
            app = self.get_msal_app()
            auth_url = app.get_authorization_request_url(
                scopes=["User.Read"],
                redirect_uri=self.redirect_uri,
                state=state or secrets.token_urlsafe(16)
            )
            return auth_url
        except Exception as e:
            logger.error(f"Error generating O365 auth URL: {e}")
            return None
    
    async def authenticate_o365_callback(self, code: str, db: AsyncSession) -> Optional[UserResponse]:
        """Handle O365 callback and authenticate user"""
        try:
            app = self.get_msal_app()
            result = app.acquire_token_by_authorization_code(
                code,
                scopes=["User.Read"],
                redirect_uri=self.redirect_uri
            )
            
            if "error" in result:
                logger.error(f"O365 authentication error: {result.get('error_description')}")
                return None
            
            access_token = result.get("access_token")
            if not access_token:
                logger.error("No access token received from O365")
                return None
            
            # Get user info from Microsoft Graph
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to get user info from Microsoft Graph: {response.status_code}")
                    return None
                
                user_info = response.json()
            
            # Find or create user
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            o365_user_id = user_info.get("id")
            full_name = user_info.get("displayName")
            
            if not email or not o365_user_id:
                logger.error("Missing required user information from O365")
                return None
            
            # Check if user exists
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user
                if not user.is_o365_user:
                    user.is_o365_user = True
                    user.o365_user_id = o365_user_id
                user.full_name = full_name or user.full_name
                user.last_login = func.now()
            else:
                # Create new O365 user
                user = User.create_o365_user(email, o365_user_id, full_name)
                user.last_login = func.now()
                db.add(user)
            
            await db.commit()
            await db.refresh(user)
            
            return UserResponse.from_orm(user)
            
        except Exception as e:
            logger.error(f"Error in O365 authentication: {str(e)}")
            return None
    
    async def authenticate_manual_user(self, email: str, password: str, db: AsyncSession) -> Optional[UserResponse]:
        """Authenticate manual user with email and password"""
        try:
            logger.info(f"Starting manual authentication for email: {email}")
            
            stmt = select(User).where(User.email == email, User.is_active == True)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"No user found for email: {email}")
                return None
                
            if user.is_o365_user:
                logger.warning(f"User {email} is an O365 user, cannot use manual login")
                return None
            
            logger.info(f"User found for {email}, verifying password")
            
            if not user.verify_password(password):
                logger.warning(f"Password verification failed for user: {email}")
                return None
            
            logger.info(f"Password verification successful for user: {email}")
            
            # Update last login
            user.last_login = func.now()
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Manual authentication completed successfully for user: {email}")
            return UserResponse.from_orm(user)
            
        except Exception as e:
            logger.error(f"Error in manual authentication for {email}: {str(e)}")
            return None
    
    async def create_session(self, user_id: int, db: AsyncSession, user_agent: str = None) -> str:
        """Create a new session for the user"""
        session_token = Session.generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=self.session_expire_hours)
        
        session = Session(
            session_token=session_token,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent
        )
        
        db.add(session)
        await db.commit()
        
        return session_token
    
    async def get_user_from_session(self, session_token: str, db: AsyncSession) -> Optional[UserResponse]:
        """Get user from session token"""
        try:
            stmt = select(User).join(Session, User.id == Session.user_id).where(
                Session.session_token == session_token,
                Session.is_active == True,
                Session.expires_at > datetime.utcnow(),
                User.is_active == True
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return UserResponse.from_orm(user)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user from session: {str(e)}")
            return None
    
    async def invalidate_session(self, session_token: str, db: AsyncSession):
        """Invalidate a session"""
        stmt = update(Session).where(Session.session_token == session_token).values(is_active=False)
        await db.execute(stmt)
        await db.commit()
    
    async def create_manual_user(self, user_data: UserCreate, db: AsyncSession) -> Optional[UserResponse]:
        """Create a new manual user"""
        try:
            # Check if user already exists
            stmt = select(User).where(User.email == user_data.email)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.warning(f"User with email {user_data.email} already exists")
                return None
            
            # Create new user
            user = User.create_manual_user(
                email=user_data.email,
                password=user_data.password,
                full_name=user_data.full_name,
                username=user_data.username
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            return UserResponse.from_orm(user)
            
        except Exception as e:
            logger.error(f"Error creating manual user: {str(e)}")
            return None 