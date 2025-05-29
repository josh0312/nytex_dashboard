#!/usr/bin/env python3
"""
Setup script for manual user account.
Run this script to create/update the manual user in the database.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import get_db, engine
from app.database.models.auth import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def setup_manual_user():
    """Create or update the manual user account."""
    
    # Manual user credentials
    email = "guest@nytexfireworks.com"
    password = "NytexD@shboard2025!"
    full_name = "Guest User"
    
    print(f"🔧 Setting up manual user account...")
    print(f"📧 Email: {email}")
    print(f"👤 Name: {full_name}")
    
    try:
        # Create database tables if they don't exist
        from app.database.models.auth import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create user
        async with get_db() as session:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"👤 User {email} already exists. Updating password...")
                existing_user.set_password(password)
                existing_user.full_name = full_name
                await session.commit()
                print(f"✅ Updated user {email}")
            else:
                print(f"👤 Creating new user {email}...")
                user = User.create_manual_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    username=email
                )
                session.add(user)
                await session.commit()
                print(f"✅ Created user {email}")
                
        print(f"\n🎉 Manual user setup complete!")
        print(f"🌐 You can now login with:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
    except Exception as e:
        print(f"❌ Error setting up manual user: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(setup_manual_user()) 