# Docker Development Guide - NyTex Dashboard

## Overview

This guide explains how to run your NyTex Dashboard in Docker exactly like production, with integrated Google Secret Manager for secrets management. This ensures **development/production parity** and eliminates "works on my machine" issues.

## Architecture

### 🏗️ **Development Setup**
- **Local Development**: `docker-compose.yml` with hot reload and local secrets
- **Production Testing**: `docker-compose.prod.yml` with Google Secret Manager
- **Secrets Management**: Automated sync between local `.env.local` and Google Secret Manager

### 🔐 **Secrets Management Flow**
```
Local Development (.env.local) ←→ Google Secret Manager ←→ Production (Cloud Run)
```

## Quick Start

### 1. **Initialize Development Environment**
```bash
# Set up authentication and create .env.local template
./scripts/dev-secrets.sh init
```

### 2. **Configure Your Local Secrets**
Edit `.env.local` with your actual values:
```bash
nano .env.local
```

### 3. **Push Secrets to Google Secret Manager**
```bash
# Upload your local secrets to production Secret Manager
./scripts/dev-secrets.sh push
```

### 4. **Start Development Environment**
```bash
# Start with local file-based secrets (hot reload enabled)
docker-compose up

# OR start with Cloud SQL proxy
docker-compose --profile cloud-sql up

# OR start with local PostgreSQL
docker-compose --profile local-db up
```

## Development Modes

### 🔄 **Local Development Mode** (Recommended)
**File**: `docker-compose.yml`
- Uses local `.env.local` file for secrets
- Hot reload enabled for code changes
- Volume mounts for real-time development
- Same port (8080) as production

```bash
docker-compose up
```

**Features**:
- ✅ Hot reload on code changes
- ✅ Local secret file management
- ✅ Volume mounts for development
- ✅ Debug logging enabled
- ✅ Same environment as production

### 🎯 **Production Testing Mode**
**File**: `docker-compose.prod.yml`
- Uses Google Secret Manager (exactly like production)
- No hot reload (exactly like production)
- Same resource constraints as Cloud Run
- Read-only filesystem

```bash
docker-compose -f docker-compose.prod.yml up
```

**Features**:
- ✅ Identical to production Cloud Run
- ✅ Google Secret Manager integration
- ✅ Production security constraints
- ✅ Resource limits matching Cloud Run

## Secrets Management Commands

### 📋 **Available Commands**
```bash
./scripts/dev-secrets.sh init      # Initialize development environment
./scripts/dev-secrets.sh push      # Upload local secrets to Secret Manager
./scripts/dev-secrets.sh pull      # Download secrets from Secret Manager
./scripts/dev-secrets.sh compare   # Compare local vs remote secrets
./scripts/dev-secrets.sh list      # List all secrets in Secret Manager
./scripts/dev-secrets.sh backup    # Backup current .env.local
./scripts/dev-secrets.sh restore   # Restore .env.local from backup
```

### 🔄 **Typical Workflow**
```bash
# 1. Set up development environment
./scripts/dev-secrets.sh init

# 2. Edit your local secrets
nano .env.local

# 3. Compare with production
./scripts/dev-secrets.sh compare

# 4. Push to production Secret Manager
./scripts/dev-secrets.sh push

# 5. Start development
docker-compose up
```

## Database Options

### ☁️ **Cloud SQL (Recommended)**
Connect to production database via Cloud SQL Proxy:

```bash
# Set up authentication
gcloud auth application-default login

# Add to .env.local:
CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1:your-instance
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:pass@localhost:5432/db

# Start with Cloud SQL proxy
docker-compose --profile cloud-sql up
```

### 🐘 **Local PostgreSQL**
Use local PostgreSQL for complete offline development:

```bash
# Add to .env.local:
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://nytex_user:nytex_password@postgres:5432/nytex_dashboard

# Start with local database
docker-compose --profile local-db up
```

## Environment Variables

### 🔑 **Managed by Secret Manager**
These are automatically synced between local and production:

| Environment Variable | Secret Manager ID | Description |
|---------------------|-------------------|-------------|
| `SECRET_KEY` | `secret-key` | Application secret key |
| `SQUARE_ACCESS_TOKEN` | `square-access-token` | Square API access token |
| `AZURE_CLIENT_SECRET` | `azure-client-secret` | Azure AD client secret |
| `SQLALCHEMY_DATABASE_URI` | `database-uri` | Database connection string |

### ⚙️ **Environment-Specific**
These vary between development and production:

| Variable | Development | Production |
|----------|-------------|------------|
| `ENVIRONMENT` | `development` | `production` |
| `DEBUG` | `True` | `False` |
| `SQUARE_ENVIRONMENT` | `sandbox` | `production` |
| `AZURE_REDIRECT_URI` | `http://localhost:8080/auth/callback` | `https://your-domain.com/auth/callback` |

## Troubleshooting

### 🔐 **Authentication Issues**
```bash
# Check authentication
gcloud auth list
gcloud auth application-default login

# Verify project
gcloud config get-value project
gcloud config set project nytex-business-systems
```

### 🔄 **Secret Sync Issues**
```bash
# Compare local vs remote
./scripts/dev-secrets.sh compare

# Backup before pulling
./scripts/dev-secrets.sh backup
./scripts/dev-secrets.sh pull

# Restore if needed
./scripts/dev-secrets.sh restore
```

### 🐳 **Docker Issues**
```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up

# Check logs
docker-compose logs nytex-dashboard

# Clean up
docker system prune
```

### 🔍 **Development Debugging**
```bash
# View application logs
docker-compose logs -f nytex-dashboard

# Access container shell
docker-compose exec nytex-dashboard bash

# Check environment variables
docker-compose exec nytex-dashboard env | grep -E "(SECRET|AZURE|SQUARE)"
```

## File Structure

```
nytex_dashboard/
├── docker-compose.yml          # Local development
├── docker-compose.prod.yml     # Production testing
├── Dockerfile                  # Regular development image
├── Dockerfile.secrets          # Production image with Secret Manager
├── .env.local                  # Local secrets (gitignored)
├── scripts/
│   ├── secrets_manager.py      # Python secrets management
│   ├── dev-secrets.sh          # Bash helper script
│   ├── load_secrets.py         # Production secret loader
│   └── start_with_secrets.sh   # Production startup script
└── DOCKER_DEVELOPMENT_GUIDE.md # This guide
```

## Production Deployment

### 🚀 **Deploy with Secret Manager**
```bash
# Build and deploy with secrets-enabled Dockerfile
gcloud run deploy nytex-dashboard \
  --source . \
  --dockerfile Dockerfile.secrets \
  --region=us-central1 \
  --allow-unauthenticated
```

### ✅ **Verify Production**
```bash
# Test production deployment
curl https://your-production-url.com/

# Check logs
gcloud run services logs read nytex-dashboard --region=us-central1
```

## Best Practices

### 🔒 **Security**
- Never commit `.env.local` to git
- Use least-privilege service accounts
- Regularly rotate secrets
- Use different secrets for dev/staging/prod

### 🔄 **Development Workflow**
1. **Pull latest secrets**: `./scripts/dev-secrets.sh pull`
2. **Make changes locally**: Edit `.env.local` as needed
3. **Test locally**: `docker-compose up`
4. **Test production-like**: `docker-compose -f docker-compose.prod.yml up`
5. **Push to production**: `./scripts/dev-secrets.sh push`
6. **Deploy**: `gcloud run deploy...`

### 📊 **Monitoring**
- Use `./scripts/dev-secrets.sh compare` regularly
- Check Secret Manager versions in Google Cloud Console
- Monitor application logs for secret loading issues

---

## Quick Reference

### 🚀 **Start Development**
```bash
./scripts/dev-secrets.sh init && docker-compose up
```

### 🔄 **Sync Secrets**
```bash
./scripts/dev-secrets.sh pull    # Download from production
./scripts/dev-secrets.sh push    # Upload to production
```

### 🎯 **Test Production Mode**
```bash
docker-compose -f docker-compose.prod.yml up
```

### 🔍 **Debug**
```bash
docker-compose logs -f nytex-dashboard
```

This setup ensures your local development environment exactly matches production, eliminating deployment surprises and making debugging much easier! 🎉 