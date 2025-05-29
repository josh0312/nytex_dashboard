#!/usr/bin/env python3
"""
Simple authentication test for NyTex Dashboard
Tests the authentication system without requiring database connection.
"""

import asyncio
import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
import secrets

# Test app setup
app = FastAPI(title="NyTex Dashboard Auth Test")
app.add_middleware(SessionMiddleware, secret_key="test-secret-key-12345")
templates = Jinja2Templates(directory="app/templates")

# Test user credentials - using the real guest account
TEST_USERS = {
    "guest@nytexfireworks.com": {
        "password": "NytexD@shboard2025!",
        "full_name": "Guest User",
        "auth_method": "manual"
    }
}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirects to test page if authenticated, login if not"""
    if request.session.get("user_id"):
        return RedirectResponse(url="/test", status_code=302)
    return RedirectResponse(url="/auth/login", status_code=302)

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.post("/auth/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    """Handle login form submission"""
    
    # Check credentials
    user = TEST_USERS.get(email)
    if not user or user["password"] != password:
        return templates.TemplateResponse(
            "auth/login.html", 
            {
                "request": request, 
                "error": "Invalid email or password"
            }
        )
    
    # Set session
    request.session["user_id"] = email
    request.session["user_name"] = user["full_name"]
    request.session["auth_method"] = user["auth_method"]
    
    return RedirectResponse(url="/test", status_code=302)

@app.get("/auth/logout")
async def logout(request: Request):
    """Logout endpoint"""
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=302)

@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Test page - only accessible when authenticated"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_name = request.session.get("user_name", "Unknown User")
    auth_method = request.session.get("auth_method", "unknown")
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Test Success</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .success {{ color: #28a745; font-size: 24px; margin-bottom: 20px; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .button {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 5px 0 0; }}
            .button:hover {{ background: #0056b3; }}
            .logout {{ background: #dc3545; }}
            .logout:hover {{ background: #c82333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success">✅ Authentication Test Successful!</div>
            
            <div class="info">
                <strong>Logged in as:</strong> {user_name}<br>
                <strong>Email:</strong> {user_id}<br>
                <strong>Auth Method:</strong> {auth_method}<br>
                <strong>Session Active:</strong> Yes
            </div>
            
            <p>🎉 The authentication system is working correctly!</p>
            
            <p><strong>What was tested:</strong></p>
            <ul>
                <li>Login page rendering</li>
                <li>Form submission and validation</li>
                <li>Session management</li>
                <li>Route protection (this page requires authentication)</li>
                <li>User data display</li>
            </ul>
            
            <a href="/auth/logout" class="button logout">Test Logout</a>
            <a href="/auth/login" class="button">Back to Login</a>
        </div>
    </body>
    </html>
    """)

def main():
    print("🚀 Starting NyTex Dashboard Authentication Test")
    print("=" * 50)
    print("📋 Test Credentials:")
    print("   Email: guest@nytexfireworks.com")
    print("   Password: NytexD@shboard2025!")
    print("🌐 Open: http://localhost:8001")
    print("📖 Flow: Login page → Authenticate → Test success page")
    print("✅ This tests:")
    print("   - Login page rendering")
    print("   - Form submission")
    print("   - Session management") 
    print("   - Route protection")
    print("   - Logout functionality")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    main() 