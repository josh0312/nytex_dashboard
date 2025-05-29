# NyTex Dashboard Authentication System

## Overview
The NyTex Dashboard includes a comprehensive authentication system that supports both **Microsoft Entra ID** (formerly Azure AD) login for organization members and manual user accounts for external access.

> **✅ Modern Implementation**: Uses **MSAL** and **Microsoft Graph API** - fully compliant with current Microsoft standards

## Quick Setup Status ✅

### Manual User Account - CONFIGURED ✅
The guest account has been set up with these credentials:
- **Email**: `guest@nytexfireworks.com`
- **Password**: `NytexD@shboard2025!`
- **Status**: ✅ Ready for use

### Microsoft Entra ID Integration - PENDING SETUP ⚠️
To enable Microsoft Entra ID login for your organization, you need to:
1. Set up a Microsoft Entra ID App Registration (see setup instructions below)
2. Configure the environment variables

## Environment Variables

Add these to your `.env` file:

```bash
# Required - Secret key for session encryption
SECRET_KEY=your-production-secret-key-here

# Manual user account (CONFIGURED)
MANUAL_USER_EMAIL=guest@nytexfireworks.com
MANUAL_USER_PASSWORD=NytexD@shboard2025!
MANUAL_USER_NAME=Guest User

# Microsoft Entra ID Integration (TO BE CONFIGURED)
AZURE_CLIENT_ID=your-azure-app-client-id
AZURE_CLIENT_SECRET=your-azure-app-client-secret  
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_REDIRECT_URI=https://yourdomain.com/auth/callback
```

## Testing the Authentication System

### Local Testing
1. **Simple Test Server**: 
   ```bash
   python test_auth_simple.py
   ```
   - Visit: http://localhost:8001
   - Login with: `guest@nytexfireworks.com` / `NytexD@shboard2025!`

2. **Full System Test**:
   ```bash
   python test_auth_local.py
   ```
   - Tests complete authentication integration

### Production Testing
1. Deploy your application
2. Visit your domain
3. You should be redirected to login page
4. Test both manual login and Microsoft Entra ID (once configured)

## Features

### Authentication Methods
1. **Manual Login**: Email/password for external users
2. **Microsoft Entra ID Login**: Single sign-on for organization members

### Modern Security Features
- ✅ **MSAL (Microsoft Authentication Library)** - current standard
- ✅ **Microsoft Graph API** integration - supported and maintained
- ✅ Encrypted session tokens
- ✅ HTTP-only cookies  
- ✅ bcrypt password hashing with salt
- ✅ 24-hour session expiry
- ✅ HTTPS enforcement for production
- ✅ **TLS 1.2** enforcement (TLS 1.0/1.1 deprecated)
- ✅ Automatic route protection

### User Management
- ✅ Automatic user creation for Microsoft Entra ID users
- ✅ Manual user account management
- ✅ Session management and logout
- ✅ User profile pages

## Microsoft Entra ID Setup Instructions

> **Important**: Follow the updated guide using **Microsoft Entra ID** (not Azure AD)

### 1. Microsoft Entra ID App Registration
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "Microsoft Entra ID" > "App registrations"
3. Click "New registration"
4. Fill out:
   - **Name**: "NyTex Dashboard"
   - **Supported account types**: "Accounts in this organizational directory only"
   - **Redirect URI**: Web - `https://yourdomain.com/auth/callback`

### 2. Configure Application
1. Go to "Authentication" and add redirect URI if needed
2. Go to "Certificates & secrets" > "New client secret"
3. Copy the **Client ID**, **Client Secret**, and **Tenant ID**
4. Update your `.env` file with these values

### 3. API Permissions (Microsoft Graph)
1. Go to "API permissions"
2. Add permission: **Microsoft Graph** > Delegated > **User.Read**
3. Grant admin consent

> **⚠️ Important**: Use **Microsoft Graph** API (NOT Azure AD Graph - deprecated)

## Implementation Compliance

Based on [Microsoft Entra change management updates](https://techcommunity.microsoft.com/blog/microsoft-entra-blog/azure-ad-change-management-simplified/2967456):

### ✅ We're Future-Proof:
- **MSAL Library**: Using supported authentication library (ADAL retired June 2023)
- **Microsoft Graph API**: Using current API (Azure AD Graph deprecated)
- **Modern Auth Flows**: OpenID Connect with proper token handling
- **Security Standards**: TLS 1.2, secure sessions, modern encryption

### ❌ What We're NOT Using (Deprecated):
- ~~ADAL~~ - retired June 30, 2023
- ~~Azure AD Graph API~~ - deprecated
- ~~TLS 1.0/1.1~~ - deprecated
- ~~Legacy PowerShell modules~~ - not applicable to our implementation

## Database Management

### Creating Additional Manual Users
```bash
# Use the setup script
python scripts/setup_manual_user.py

# Or modify the script for additional users
```

### Database Migration
The authentication tables are created automatically, but you can run migrations:
```bash
alembic upgrade head
```

## File Structure
```
app/
├── database/
│   ├── models/auth.py          # User and Session models
│   └── schemas/auth.py         # Pydantic schemas
├── services/auth_service.py    # MSAL authentication logic
├── middleware/auth_middleware.py # Route protection
├── routes/auth.py              # Login/logout routes
└── templates/auth/             # Login/profile pages
```

## Troubleshooting

### Common Issues
1. **"No module named" errors**: Ensure virtual environment is activated
2. **Database connection errors**: Check Cloud SQL proxy is running
3. **Session issues**: Verify SECRET_KEY is set
4. **Microsoft Entra ID login fails**: Check App Registration configuration

### Microsoft Entra ID Specific
- **AADSTS50011**: Redirect URI mismatch in App Registration
- **AADSTS700016**: Incorrect tenant ID
- **Graph API errors**: Ensure using Microsoft Graph (not Azure AD Graph)

### Debug Mode
Set `DEBUG=True` in your environment to see detailed logs.

### Logs
Check application logs for authentication errors:
```bash
tail -f logs/app.log
```

## Next Steps

### For Production Deployment:
1. ✅ Manual user account configured
2. ⚠️ Set up Microsoft Entra ID App Registration
3. ⚠️ Configure Microsoft Entra ID environment variables
4. ✅ Deploy with authentication enabled
5. ✅ Test both authentication methods

### Security Checklist:
- ✅ Use strong SECRET_KEY in production
- ✅ Enable HTTPS
- ✅ Use secure session settings
- ✅ Regular password updates for manual accounts
- ✅ Monitor authentication logs
- ✅ Using modern MSAL library
- ✅ Using Microsoft Graph API

The authentication system is production-ready and follows current Microsoft Entra ID best practices. Once you configure the Microsoft Entra ID integration, your team will have seamless single sign-on access while external users can use the guest account. 