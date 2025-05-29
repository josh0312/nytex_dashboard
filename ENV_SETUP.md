# Environment Variables for Authentication

Add these lines to your `.env` file to complete the authentication setup:

## Manual User Account (CONFIGURED ✅)
```bash
# Guest account credentials - ready to use
MANUAL_USER_EMAIL=guest@nytexfireworks.com
MANUAL_USER_PASSWORD=NytexD@shboard2025!
MANUAL_USER_NAME=Guest User
```

## O365 Integration (TO BE CONFIGURED)
```bash
# Azure App Registration details (set these up in Azure Portal)
AZURE_CLIENT_ID=your-azure-app-client-id
AZURE_CLIENT_SECRET=your-azure-app-client-secret
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_REDIRECT_URI=https://yourdomain.com/auth/callback
```

## Required Secret Key
```bash
# Generate a strong secret key for production
SECRET_KEY=your-production-secret-key-here
```

## Quick Test
After updating your `.env` file, you can test the authentication system:

```bash
# Test locally
python test_auth_simple.py

# Then visit http://localhost:8001
# Login with: guest@nytexfireworks.com / NytexD@shboard2025!
```

## Status
- ✅ Manual user account created in database
- ✅ Authentication system ready
- ⚠️ O365 setup pending (requires Azure App Registration)
- ⚠️ Environment variables need to be set in production 