#!/usr/bin/env python3
"""
Simple local test script for authentication system.
This runs a basic FastAPI server with authentication for local testing.
"""

import os
import asyncio
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Set minimal environment variables for testing
os.environ['SECRET_KEY'] = 'test-secret-key-for-local-testing'
os.environ['MANUAL_USER_EMAIL'] = 'test@nytex.com'
os.environ['MANUAL_USER_PASSWORD'] = 'testpass123'
os.environ['MANUAL_USER_NAME'] = 'Test User'

# Disable O365 for local testing
os.environ['AZURE_CLIENT_ID'] = ''
os.environ['AZURE_CLIENT_SECRET'] = ''
os.environ['AZURE_TENANT_ID'] = ''

from app.routes.auth import router as auth_router
from app.middleware.auth_middleware import get_current_user

# Create test app
app = FastAPI(title="NyTex Dashboard - Local Test")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include authentication routes
app.include_router(auth_router)

# Test protected route
@app.get("/test")
async def test_page(request: Request, current_user = Depends(get_current_user)):
    """Test protected page"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Test - Success!</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; max-width: 600px; margin: 0 auto; }}
            .success {{ color: #22c55e; font-size: 24px; font-weight: bold; }}
            .user-info {{ background: #f8fafc; padding: 20px; border-radius: 6px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">🎉 Authentication Test Successful!</h1>
            <p>You have successfully logged in to the NyTex Dashboard authentication system.</p>
            
            <div class="user-info">
                <h3>User Information:</h3>
                <p><strong>Email:</strong> {current_user.email}</p>
                <p><strong>Name:</strong> {current_user.full_name or 'Not provided'}</p>
                <p><strong>Account Type:</strong> {'O365' if current_user.is_o365_user else 'Manual'}</p>
                <p><strong>Login Time:</strong> {current_user.last_login or 'First login'}</p>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/auth/profile" style="background: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-right: 10px;">View Profile</a>
                <form method="POST" action="/auth/logout" style="display: inline;">
                    <button type="submit" style="background: #ef4444; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">Logout</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """)

# Root redirect
@app.get("/")
async def root():
    return RedirectResponse(url="/test", status_code=302)

if __name__ == "__main__":
    print("🚀 Starting NyTex Dashboard Authentication Test Server")
    print("📋 Test Credentials:")
    print("   Email: test@nytex.com")
    print("   Password: testpass123")
    print("")
    print("🌐 Open: http://localhost:8000")
    print("📖 You'll be redirected to login, then to test page after authentication")
    print("")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 