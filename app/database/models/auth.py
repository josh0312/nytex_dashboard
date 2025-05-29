from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from passlib.context import CryptContext
import secrets
from .. import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)  # Only for manual users
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_o365_user = Column(Boolean, default=False)
    o365_user_id = Column(String, unique=True, nullable=True)  # Microsoft user ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def verify_password(self, password: str) -> bool:
        """Verify password for manual users"""
        if not self.hashed_password:
            return False
        return pwd_context.verify(password, self.hashed_password)
    
    def set_password(self, password: str):
        """Set password for manual users"""
        self.hashed_password = pwd_context.hash(password)
    
    @classmethod
    def create_manual_user(cls, email: str, password: str, full_name: str = None, username: str = None):
        """Create a manual user with password"""
        user = cls(
            email=email,
            username=username or email,
            full_name=full_name,
            is_o365_user=False
        )
        user.set_password(password)
        return user
    
    @classmethod
    def create_o365_user(cls, email: str, o365_user_id: str, full_name: str = None):
        """Create an O365 user"""
        return cls(
            email=email,
            username=email,
            full_name=full_name,
            is_o365_user=True,
            o365_user_id=o365_user_id
        )

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    user_agent = Column(Text, nullable=True)
    
    @classmethod
    def generate_token(cls):
        """Generate a secure session token"""
        return secrets.token_urlsafe(32) 