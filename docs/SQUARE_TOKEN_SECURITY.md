# Square Access Token Security Guide

This guide explains how to securely store and manage your Square access token in Google Cloud production environments.

## 🔐 Security Overview

**Never store sensitive tokens in:**
- ❌ Source code
- ❌ Environment variables in deployment files
- ❌ Container images
- ❌ Configuration files committed to git

**Always use:**
- ✅ Google Secret Manager for production
- ✅ Local `.env` files for development (not committed)
- ✅ IAM-controlled access
- ✅ Audit logging

## 🚀 Quick Setup

Run the automated setup script:

```bash
./scripts/setup-secret-manager.sh
```

This script will:
1. Create the secret in Google Secret Manager
2. Configure IAM permissions
3. Verify the setup

## 📋 Manual Setup Steps

If you prefer manual setup:

### 1. Create the Secret

```bash
# Store your Square access token securely
echo "your_actual_square_token" | gcloud secrets create square-access-token --data-file=-
```

### 2. Grant Cloud Run Access

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding square-access-token \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Deploy with Secret Manager

The `cloudbuild.yaml` is already configured to use Secret Manager:

```yaml
- '--set-secrets'
- 'SQUARE_ACCESS_TOKEN=square-access-token:latest'
```

## 🔄 Token Rotation

To update your Square access token:

```bash
# Add a new version of the secret
echo "new_square_token" | gcloud secrets versions add square-access-token --data-file=-

# The latest version will be used automatically
# No need to redeploy your application
```

## 🏠 Local Development

For local development, continue using `.env` files:

```bash
# .env (not committed to git)
SQUARE_ACCESS_TOKEN=your_sandbox_token_here
SQUARE_ENVIRONMENT=sandbox
```

## 🔍 Verification

### Check Secret Exists
```bash
gcloud secrets list --filter="name:square-access-token"
```

### Test Access
```bash
gcloud secrets versions access latest --secret="square-access-token"
```

### View IAM Policies
```bash
gcloud secrets get-iam-policy square-access-token
```

## 🛡️ Security Best Practices

### 1. Use Different Tokens for Different Environments
- **Production**: Live Square access token
- **Staging**: Sandbox Square access token  
- **Development**: Sandbox Square access token

### 2. Regular Token Rotation
- Rotate tokens every 90 days
- Use Secret Manager versioning
- Monitor access logs

### 3. Principle of Least Privilege
- Only grant `secretmanager.secretAccessor` role
- Use service-specific service accounts when possible
- Regularly audit IAM permissions

### 4. Monitoring and Alerting
```bash
# Set up monitoring for secret access
gcloud logging sinks create square-token-access \
    bigquery.googleapis.com/projects/YOUR_PROJECT/datasets/security_logs \
    --log-filter='resource.type="gce_instance" AND protoPayload.serviceName="secretmanager.googleapis.com"'
```

## 🚨 Incident Response

If your token is compromised:

1. **Immediately revoke the token in Square Dashboard**
2. **Generate a new token**
3. **Update Secret Manager**:
   ```bash
   echo "new_secure_token" | gcloud secrets versions add square-access-token --data-file=-
   ```
4. **Destroy the old secret version**:
   ```bash
   gcloud secrets versions destroy VERSION_NUMBER --secret="square-access-token"
   ```

## 📊 Cost Considerations

Secret Manager pricing (as of 2024):
- **Secret versions**: $0.06 per 10,000 versions per month
- **Access operations**: $0.03 per 10,000 operations
- **Typical monthly cost**: < $1 for most applications

## 🔗 Related Documentation

- [Google Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Square API Authentication](https://developer.squareup.com/docs/build-basics/access-tokens)
- [Cloud Run Secrets](https://cloud.google.com/run/docs/configuring/secrets)

## ❓ Troubleshooting

### "Permission denied" errors
```bash
# Check service account has correct permissions
gcloud secrets get-iam-policy square-access-token
```

### "Secret not found" errors
```bash
# Verify secret exists in correct project
gcloud secrets list --filter="name:square-access-token"
```

### Application can't access token
```bash
# Check Cloud Run service configuration
gcloud run services describe nytex-dashboard --region=us-central1 --format="export"
``` 