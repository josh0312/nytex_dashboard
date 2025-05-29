# Authentication Setup Guide

This guide explains how to set up authentication for the NyTex Dashboard with both Microsoft 365 (O365) integration and manual user accounts.

## Environment Variables

Add these environment variables to your `.env` file or Cloud Run environment:

### Microsoft Azure/O365 Authentication
```
AZURE_CLIENT_ID=your_azure_app_client_id
AZURE_CLIENT_SECRET=your_azure_app_client_secret
AZURE_TENANT_ID=your_azure_tenant_id
AZURE_REDIRECT_URI=https://your-domain.com/auth/callback
```

### Manual User Account
```
MANUAL_USER_EMAIL=guest@yourcompany.com
MANUAL_USER_PASSWORD=secure-password-change-this
MANUAL_USER_NAME=Guest User
```

### Security Settings
```
SECRET_KEY=your-secret-key-change-this-in-production
```

## Azure App Registration Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "Azure Active Directory" > "App registrations"
3. Click "New registration"
4. Fill in the details:
   - **Name**: NyTex Dashboard
   - **Supported account types**: Accounts in this organizational directory only
   - **Redirect URI**: Web - `https://your-domain.com/auth/callback`
5. After creation, note down:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `AZURE_TENANT_ID`
6. Go to "Certificates & secrets" and create a new client secret
   - Note down the secret value → `AZURE_CLIENT_SECRET`
7. Go to "API permissions" and add:
   - Microsoft Graph → Delegated permissions → User.Read

## Database Migration

Run the database migration to create authentication tables:

```bash
# Run from project root
PYTHONPATH=. alembic -c migrations/alembic.ini upgrade head
```

## Setup Manual User

After running migrations, create the manual user account:

```bash
# Make sure environment variables are set first
python scripts/setup_manual_user.py
```

## How Authentication Works

### O365 Users
- Users from your organization can sign in with their Microsoft 365 credentials
- They are automatically created in the database on first login
- Their information is kept in sync with Azure AD

### Manual Users
- You can create manual user accounts for people outside your organization
- These users sign in with email and password
- You control when to create these accounts

### Session Management
- Both authentication methods use secure session tokens
- Sessions expire after 24 hours
- Users are automatically redirected to login when sessions expire

## Deployment Considerations

### For Google Cloud Run

1. Set environment variables in Cloud Run service configuration
2. Ensure your domain is properly configured for HTTPS
3. Update `AZURE_REDIRECT_URI` to match your production domain

### Security Best Practices

1. Use strong, unique passwords for manual users
2. Rotate the `SECRET_KEY` regularly
3. Use HTTPS in production
4. Monitor authentication logs
5. Regularly review user access

## Troubleshooting

### Common Issues

1. **O365 login fails**: Check Azure app configuration and redirect URI
2. **Manual user can't login**: Verify environment variables and run setup script
3. **Session expires immediately**: Check `SECRET_KEY` configuration
4. **Database connection issues**: Verify database connection and run migrations

### Logs

Check application logs for authentication-related errors:
```bash
tail -f app.log | grep auth
``` 