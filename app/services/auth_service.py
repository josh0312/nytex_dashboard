from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
import msal
import httpx
import requests
from jose import JWTError, jwt
from ..database.models.auth import User, Session
from ..database.schemas.auth import UserCreate, UserResponse
from ..config import Config
import secrets
import logging
import urllib.parse

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
            validate_authority=False  # Disable strict authority validation
        )
    
    def get_o365_auth_url(self, state: str = None) -> Optional[str]:
        """Get O365 authorization URL"""
        if not self.o365_enabled:
            logger.warning("O365 authentication not configured")
            return None
            
        try:
            app = self.get_msal_app()
            auth_url = app.get_authorization_request_url(
                scopes=["User.Read"],  # Use simple scope format for MSAL
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
            logger.info(f"Starting O365 callback with code length: {len(code)}")
            logger.info(f"Code starts with: {code[:50]}..." if len(code) > 50 else f"Full code: {code}")
            
            # Use v2.0 endpoint explicitly to match requestedAccessTokenVersion: 2
            token_url = f"https://login.microsoftonline.com/{self.o365_tenant_id}/oauth2/v2.0/token"
            
            # Token exchange parameters - scope should not be included in token exchange
            token_data = {
                'client_id': self.o365_client_id,
                'client_secret': self.o365_client_secret,
                'code': code,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
                # Note: scope is NOT included in token exchange - it was specified in auth request
            }
            
            logger.info(f"Token exchange URL: {token_url}")
            logger.info(f"Redirect URI: {self.redirect_uri}")
            logger.info(f"Client ID: {self.o365_client_id}")
            
            # Use requests with proper form encoding
            response = requests.post(
                token_url,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            logger.info(f"Token exchange response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code}")
                logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                
                # If original code failed, try with URL decoded code
                if response.status_code == 400:
                    logger.info("Trying with URL decoded authorization code...")
                    try:
                        decoded_code = urllib.parse.unquote(code)
                        if decoded_code != code:
                            token_data['code'] = decoded_code
                            response = requests.post(
                                token_url,
                                data=token_data,
                                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                timeout=30
                            )
                            logger.info(f"Retry response status: {response.status_code}")
                            if response.status_code != 200:
                                logger.error(f"Retry also failed: {response.text[:500]}")
                                return None
                        else:
                            logger.info("Code was not URL encoded, no retry needed")
                            return None
                    except Exception as retry_error:
                        logger.error(f"Retry attempt failed: {retry_error}")
                        return None
                else:
                    return None
            
            # Try to parse JSON response
            try:
                token_result = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                logger.error(f"Raw response: {response.text}")
                return None
            
            if 'error' in token_result:
                logger.error(f"O365 token error: {token_result.get('error_description', token_result.get('error'))}")
                logger.error(f"Full token error response: {token_result}")
                return None
            
            access_token = token_result.get('access_token')
            if not access_token:
                logger.error("No access token received from O365")
                logger.error(f"Full token response: {token_result}")
                return None
            
            logger.info("Successfully acquired access token from O365 via v2.0 endpoint")
            
            # Get user info from Microsoft Graph
            headers = {"Authorization": f"Bearer {access_token}"}
            graph_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=30)
            
            if graph_response.status_code != 200:
                logger.error(f"Failed to get user info from Microsoft Graph: {graph_response.status_code} - {graph_response.text}")
                return None
            
            user_info = graph_response.json()
            logger.info(f"Successfully retrieved user info from Microsoft Graph")
            
            # Find or create user
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            o365_user_id = user_info.get("id")
            full_name = user_info.get("displayName")
            
            if not email or not o365_user_id:
                logger.error("Missing required user information from O365")
                return None
            
            logger.info(f"Processing O365 user: {email}")
            
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
                logger.info(f"Updated existing user: {email}")
            else:
                # Create new O365 user
                user = User.create_o365_user(email, o365_user_id, full_name)
                user.last_login = func.now()
                db.add(user)
                logger.info(f"Created new O365 user: {email}")
            
            await db.commit()
            await db.refresh(user)
            
            return UserResponse.from_orm(user)
            
        except Exception as e:
            logger.error(f"Error in O365 authentication: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
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