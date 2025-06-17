# NyTex Dashboard - Production Deployment Guide

## 🚀 Modern CI/CD Production Deployment

### Overview

NyTex Dashboard now uses a **fully automated CI/CD pipeline** with GitHub Actions. This guide covers both the automated process and emergency manual procedures.

## 🎯 Quick Start (Recommended)

### Automated Deployment via CI/CD

```bash
# 1. Make your changes
git add .
git commit -m "feat: Your feature description"

# 2. Push to trigger automated deployment
git push origin master

# 3. Monitor deployment
# Visit: https://github.com/josh0312/nytex_dashboard/actions
```

**That's it!** The CI/CD pipeline will:
- ✅ Run comprehensive tests
- ✅ Validate configuration
- ✅ Check performance
- ✅ Deploy to production
- ✅ Run health checks
- ✅ Rollback on failure

## 🏗️ CI/CD Pipeline Architecture

```
Feature Branch → Pull Request → Staging → Merge → Production
     ↓              ↓             ↓         ↓
   Tests        Staging Tests   Review   Production Tests
                     ↓                      ↓
               Staging Deploy           Production Deploy
                     ↓                      ↓
                Comment URL            Health Checks
```

### Environments

| Environment | Trigger | URL | Resources |
|-------------|---------|-----|-----------|
| **Staging** | Pull Requests | `nytex-dashboard-staging-*` | 512Mi RAM, 0.5 CPU |
| **Production** | `master` merge | `nytex-dashboard-932676587025.us-central1.run.app` | 1Gi RAM, 1 CPU |

## 🧪 Testing Strategy

### Automated Tests Run Before Deployment

1. **Critical Endpoint Tests** (MUST PASS):
   - Health check functionality
   - Authentication system
   - Database connectivity
   - Static file serving

2. **Configuration Validation** (MUST PASS):
   - Environment variables
   - Secret availability
   - Security settings
   - Database URI format

3. **Performance Tests** (WARNING ON FAIL):
   - Response time validation
   - Memory usage monitoring
   - Concurrent request handling

### Test Locally Before Pushing

```bash
# Quick deployment readiness check
python scripts/test_deployment_readiness.py

# Run critical tests only
pytest tests/test_critical_endpoints.py -v

# Run without slow tests
pytest tests/ -v -m "not slow"
```

## 🔧 Prerequisites (One-Time Setup)

### 1. GitHub Secrets Configuration

In your GitHub repository → Settings → Secrets → Actions:

| Secret Name | Description | Source |
|-------------|-------------|---------|
| `GCP_SA_KEY` | Service account JSON key | See setup below |

### 2. Google Cloud Setup

**Service Account** (Already configured):
```bash
# Verify service account exists
gcloud iam service-accounts list | grep github-actions
```

**Artifact Registry** (Already configured):
```bash
# Verify repository exists
gcloud artifacts repositories list --location=us-central1
```

## 📊 Monitoring & Verification

### Health Check Endpoints

```bash
# Production health check
curl https://nytex-dashboard-932676587025.us-central1.run.app/admin/status

# Expected response:
{
  "database": "connected",
  "square_config": "configured",
  "locations": [...],
  "tables_exist": true
}
```

### Deployment Logs

```bash
# View Cloud Run logs
gcloud run services logs read nytex-dashboard --region us-central1 --limit 50

# View deployment history
gcloud run revisions list --service=nytex-dashboard --region=us-central1
```

### GitHub Actions Monitoring

1. Visit: https://github.com/josh0312/nytex_dashboard/actions
2. Click on latest workflow run
3. View detailed logs for each step

## 🚨 Emergency Manual Deployment

**⚠️ Use only when CI/CD is unavailable**

### Option 1: Legacy Deploy Script (Emergency)

```bash
# WARNING: This bypasses testing and validation
./deploy.sh

# Script will prompt for confirmation
# Enter 'y' only for emergencies
```

### Option 2: Manual gcloud Commands

```bash
# Build and deploy manually
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE="us-central1-docker.pkg.dev/nytex-business-systems/nytex-dashboard/nytex-dashboard:emergency-$TIMESTAMP"

docker build --platform linux/amd64 -t $IMAGE .
docker push $IMAGE

gcloud run deploy nytex-dashboard \
    --image $IMAGE \
    --region us-central1 \
    --platform managed
```

## 🔄 Rollback Procedures

### Automatic Rollback

CI/CD automatically rolls back on:
- Health check failures
- Database connection issues
- Critical test failures

### Manual Rollback

```bash
# List recent revisions
gcloud run revisions list --service=nytex-dashboard --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic nytex-dashboard \
    --region=us-central1 \
    --to-revisions=REVISION_NAME=100
```

## 🔐 Security & Secrets

### Production Secrets (Google Secret Manager)

All secrets are managed via Google Secret Manager:

| Secret | Purpose |
|--------|---------|
| `database-uri` | Cloud SQL connection |
| `secret-key` | Application encryption |
| `square-access-token` | Square API access |
| `smtp-*` | Email notifications |
| `azure-*` | O365 authentication |

### Secrets Management

```bash
# List all secrets
gcloud secrets list

# Update a secret (if needed)
echo "new-value" | gcloud secrets versions add secret-name --data-file=-

# View secret (masked)
python scripts/secrets_manager.py list
```

## 📈 Performance & Scaling

### Production Configuration

- **Memory**: 1Gi RAM
- **CPU**: 1 vCPU
- **Concurrency**: 80 requests per instance
- **Max Instances**: 10
- **Min Instances**: 0 (auto-scaling)
- **Timeout**: 300 seconds

### Monitoring Metrics

```bash
# Check resource usage
gcloud run services describe nytex-dashboard --region=us-central1 --format="get(status.traffic,spec.template.spec.containerConcurrency)"

# View performance metrics in Google Cloud Console
# Navigate to: Cloud Run → nytex-dashboard → Metrics
```

## 🎯 Development Workflow

### Feature Development

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Develop and test locally**:
   ```bash
   python scripts/test_deployment_readiness.py
   ```

3. **Push and create PR**:
   ```bash
   git push origin feature/your-feature
   # Create PR on GitHub
   ```

4. **Review staging deployment**:
   - Staging URL provided in PR comment
   - Test your changes thoroughly

5. **Merge to deploy**:
   - Merge PR → Automatic production deployment

### Hotfix Process

For urgent production fixes:

```bash
# Create hotfix branch
git checkout -b hotfix/critical-fix

# Make minimal necessary changes
git commit -m "hotfix: Critical issue description"

# Push directly to master (bypasses PR for emergencies)
git checkout master
git cherry-pick hotfix/critical-fix
git push origin master
```

## 📝 Troubleshooting

### Common Issues

1. **Deployment Failure**:
   - Check GitHub Actions logs
   - Review test failures
   - Verify secrets are configured

2. **Database Connection Issues**:
   - Verify Cloud SQL instance is running
   - Check `database-uri` secret format
   - Review Cloud SQL proxy logs

3. **Performance Issues**:
   - Monitor response times in Cloud Console
   - Check memory and CPU usage
   - Review concurrent request handling

### Support Contacts

- **CI/CD Issues**: Check GitHub Actions logs
- **Infrastructure**: Google Cloud Console
- **Database**: Cloud SQL logs and monitoring
- **Application**: `/admin/status` endpoint

## 📚 Additional Documentation

- **CI/CD Setup**: `docs/CI_CD_SETUP.md`
- **Testing Strategy**: `docs/TESTING_STRATEGY.md`
- **Local Development**: `docs/DOCKER_GUIDE.md`
- **Secrets Management**: `docs/SECRETS_GUIDE.md`

---

**🎉 Congratulations!** You now have a production-grade CI/CD pipeline that ensures only tested, validated, and secure code reaches production. 