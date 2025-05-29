# Microsoft Entra ID (O365) Setup for NyTex Dashboard

> **Note**: Azure Active Directory is now called **Microsoft Entra ID**. This guide uses the current terminology and latest authentication practices.

## Microsoft Entra ID App Registration Setup

### Step 1: Create App Registration

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate**: Microsoft Entra ID → App registrations → New registration

> **Important**: We're using **Microsoft Entra ID** (formerly Azure AD) with modern authentication practices

### Step 2: App Registration Details

**Fill out the form:**
- **Name**: `NyTex Dashboard`
- **Supported account types**: `Accounts in this organizational directory only (nytexfireworks.com only - Single tenant)`
- **Redirect URI**: 
  - Type: `Web`
  - URL: `https://nytex-dashboard-932676587025.us-central1.run.app/auth/callback`

### Step 3: Collect Required Information

After creating the app, go to the **Overview** page and copy:

1. **Application (client) ID** - [Copy from Azure Portal Overview]
2. **Directory (tenant) ID** - [Copy from Azure Portal Overview]

### Step 4: Create Client Secret

1. Go to **"Certificates & secrets"**
2. Click **"New client secret"**
3. Description: `NyTex Dashboard Production Secret`
4. Expires: `24 months` (recommended for production)
5. Click **"Add"**
6. **⚠️ IMPORTANT**: Copy the secret **Value** immediately (not the Secret ID)

### Step 5: Set API Permissions (Microsoft Graph)

> **Note**: We're using **Microsoft Graph API** (not the deprecated Azure AD Graph API)

1. Go to **"API permissions"**
2. Click **"Add a permission"**
3. Select **"Microsoft Graph"** (NOT Azure AD Graph - deprecated)
4. Choose **"Delegated permissions"**
5. Search for and select: **"User.Read"**
6. Click **"Add permissions"**
7. Click **"Grant admin consent for nytexfireworks.com"**
8. Confirm the consent

### Step 6: Authentication Configuration (Modern Auth)

1. Go to **"Authentication"**
2. Verify the redirect URI is listed:
   - `https://nytex-dashboard-932676587025.us-central1.run.app/auth/callback`
3. Under **"Implicit grant and hybrid flows"**:
   - ✅ Check **"Access tokens"** (for modern auth)
   - ✅ Check **"ID tokens"** (for OpenID Connect)
4. Under **"Advanced settings"**:
   - ✅ Enable **"Allow public client flows"**: No (keep secure)
5. Click **"Save"**

## Environment Variables for Google Cloud Run

Use these exact values in your Google Cloud Run environment variables:

```bash
# Generated secure secret key
SECRET_KEY=NwdCDlUofwGFus3gco9wYncf0JiwxBRD_Z0v6eEaSjk

# Manual user account (already configured)
MANUAL_USER_EMAIL=guest@nytexfireworks.com
MANUAL_USER_PASSWORD=NytexD@shboard2025!
MANUAL_USER_NAME=Guest User

# Microsoft Entra ID values (replace with your actual values from Azure Portal)
AZURE_CLIENT_ID=your-application-client-id-from-azure
AZURE_CLIENT_SECRET=your-client-secret-value-from-azure
AZURE_TENANT_ID=your-directory-tenant-id-from-azure
AZURE_REDIRECT_URI=https://nytex-dashboard-932676587025.us-central1.run.app/auth/callback
```

## Important: Microsoft Authentication Library (MSAL)

Our implementation uses **MSAL (Microsoft Authentication Library)**, which is the recommended and supported library. The old ADAL library was retired as of June 30, 2023, according to the [Microsoft Entra change management updates](https://techcommunity.microsoft.com/blog/microsoft-entra-blog/azure-ad-change-management-simplified/2967456).

✅ **We're using MSAL** - modern and supported  
❌ **Not using ADAL** - deprecated and retired  
✅ **Microsoft Graph API** - current and supported  
❌ **Not using Azure AD Graph** - deprecated  

## Deployment Steps

### 1. Update Google Cloud Run Environment Variables

In Google Cloud Console:
1. Go to Cloud Run → nytex-dashboard service
2. Click **"Edit & Deploy New Revision"**
3. Go to **"Variables & Secrets"** tab
4. Add/update the environment variables above

### 2. Deploy the Updated Service

The authentication system is already included in your code with modern MSAL implementation:
1. Set the environment variables
2. Deploy the new revision
3. Test the authentication

### 3. Testing

After deployment:
1. **Visit**: https://nytex-dashboard-932676587025.us-central1.run.app/
2. **You should be redirected to login page**
3. **Test Manual Login**: Use `guest@nytexfireworks.com` / `NytexD@shboard2025!`
4. **Test Microsoft Entra ID Login**: Click "Sign in with Microsoft 365" - should work for @nytexfireworks.com users

## Security Notes & Modern Standards

- ✅ Using **MSAL** (Microsoft Authentication Library) - current standard
- ✅ **Microsoft Graph API** integration - supported and maintained
- ✅ **TLS 1.2** enforcement (TLS 1.0/1.1 deprecated)
- ✅ HTTPS redirect URI (required for production)
- ✅ Single tenant configuration (only nytexfireworks.com users)
- ✅ Minimal permissions (User.Read only)
- ✅ Secure secret key with proper expiration
- ✅ HTTP-only session cookies

## Troubleshooting

### Common Issues:

**Error: "AADSTS50011: The reply URL specified in the request does not match"**
- Solution: Double-check the redirect URI in Microsoft Entra ID matches exactly

**Error: "AADSTS700016: Application not found in directory"**
- Solution: Ensure you're using the correct tenant ID from Microsoft Entra ID

**Manual login works but Entra ID doesn't:**
- Check all Azure environment variables are set correctly
- Verify admin consent was granted in Microsoft Entra ID
- Ensure you're using Microsoft Graph API permissions (not deprecated Azure AD Graph)

**MSAL-related errors:**
- Our implementation uses the modern MSAL library (not deprecated ADAL)
- Verify client secret hasn't expired
- Check that the app registration is configured for web applications

### Testing Locally (Optional)

You can test Microsoft Entra ID integration locally by temporarily setting:
```bash
AZURE_REDIRECT_URI=http://localhost:8000/auth/callback
```
And adding this as a redirect URI in Microsoft Entra ID (for testing only).

## Migration Notes

Based on the [Microsoft Entra change management updates](https://techcommunity.microsoft.com/blog/microsoft-entra-blog/azure-ad-change-management-simplified/2967456):

- ✅ **Our implementation is future-proof** - uses MSAL and Microsoft Graph
- ✅ **No migration needed** - we're already using current standards
- ✅ **Secure and supported** - follows latest Microsoft recommendations

## Next Steps

1. ✅ Complete Microsoft Entra ID App Registration
2. ✅ Set environment variables in Google Cloud Run  
3. ✅ Deploy new revision
4. ✅ Test both authentication methods
5. ✅ Production ready with modern Microsoft Entra ID! 🚀 