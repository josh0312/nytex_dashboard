# NyTex Dashboard - CI/CD Pipeline Guide

> **📖 For complete deployment instructions, see [Enhanced Deployment Guide](./DEPLOYMENT.md)**

## 🚀 CI/CD Pipeline Overview

This document focuses specifically on the **GitHub Actions CI/CD pipeline**. For the recommended enhanced deployment workflow with automatic IAM setup and monitoring, see the [Enhanced Deployment Guide](./DEPLOYMENT.md).

---

## 🎯 Quick CI/CD Deployment

### **Automated Deployment via GitHub Actions**

```bash
# 1. Make your changes
git add .
git commit -m "feat: Your feature description"

# 2. Push to trigger automated deployment
git push origin master

# 3. Monitor deployment
# Visit: https://github.com/josh0312/nytex_dashboard/actions
```

**The CI/CD pipeline automatically:**
- ✅ Runs comprehensive tests
- ✅ Validates configuration
- ✅ Checks performance
- ✅ Deploys to production
- ✅ Runs health checks
- ✅ Rolls back on failure

---

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

### **Environments**

| Environment | Trigger | URL | Resources |
|-------------|---------|-----|-----------|
| **Staging** | Pull Requests | `nytex-dashboard-staging-*` | 512Mi RAM, 0.5 CPU |
| **Production** | `master` merge | `nytex-dashboard-932676587025.us-central1.run.app` | 1Gi RAM, 1 CPU |

---

## 🧪 CI/CD Testing Strategy

### **Automated Tests (Must Pass)**

1. **Critical Endpoint Tests**:
   - Health check functionality
   - Authentication system
   - Database connectivity
   - Static file serving

2. **Configuration Validation**:
   - Environment variables
   - Secret availability
   - Security settings
   - Database URI format

3. **Performance Tests** (Warning on fail):
   - Response time validation
   - Memory usage monitoring
   - Concurrent request handling

### **Pre-Push Testing**

```bash
# Quick deployment readiness check
python scripts/test_deployment_readiness.py

# Run critical tests only
pytest tests/test_critical_endpoints.py -v

# Run without slow tests
pytest tests/ -v -m "not slow"
```

---

## 🔧 CI/CD Prerequisites

### **GitHub Secrets Configuration**

In your GitHub repository → Settings → Secrets → Actions:

| Secret Name | Description | Status |
|-------------|-------------|---------|
| `GCP_SA_KEY` | Service account JSON key | ✅ Configured |

### **Google Cloud Setup**

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

---

## 📊 CI/CD Monitoring

### **GitHub Actions Monitoring**

1. Visit: https://github.com/josh0312/nytex_dashboard/actions
2. Click on latest workflow run
3. View detailed logs for each step

### **Deployment Verification**

```bash
# Production health check
curl https://nytex-dashboard-932676587025.us-central1.run.app/admin/status

# View deployment history
gcloud run revisions list --service=nytex-dashboard --region=us-central1
```

---

## 🔄 CI/CD Rollback Procedures

### **Automatic Rollback**

CI/CD automatically rolls back on:
- Health check failures
- Database connection issues
- Critical test failures

### **Manual Rollback**

```bash
# List recent revisions
gcloud run revisions list --service=nytex-dashboard --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic nytex-dashboard \
    --region=us-central1 \
    --to-revisions=REVISION_NAME=100
```

---

## 🎯 Development Workflow with CI/CD

### **Feature Development**

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

### **Hotfix Process**

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

---

## 🚨 Emergency Procedures

### **When CI/CD is Unavailable**

**Option 1: Enhanced Deployment (Recommended)**
```bash
# Use the enhanced deployment system
python deploy.py
```

**Option 2: Legacy Deploy Script**
```bash
# WARNING: Bypasses testing and validation
./deploy.sh
```

**Option 3: Manual gcloud Commands**
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

---

## 🔐 Security & Secrets

### **Production Secrets (Google Secret Manager)**

All secrets are managed via Google Secret Manager:

| Secret | Purpose |
|--------|---------|
| `database-uri` | Cloud SQL connection |
| `secret-key` | Application encryption |
| `square-access-token` | Square API access |
| `smtp-*` | Email notifications |
| `azure-*` | O365 authentication |

### **Secrets Management**

```bash
# List all secrets
gcloud secrets list

# Update a secret (if needed)
echo "new-value" | gcloud secrets versions add secret-name --data-file=-

# View secret (masked)
python scripts/secrets_manager.py list
```

---

## 📈 Performance & Scaling

### **Production Configuration**

- **Memory**: 1Gi RAM
- **CPU**: 1 vCPU
- **Concurrency**: 80 requests per instance
- **Max Instances**: 10
- **Min Instances**: 0 (auto-scaling)
- **Timeout**: 300 seconds

### **Monitoring Metrics**

```bash
# Check resource usage
gcloud run services describe nytex-dashboard --region=us-central1 --format="get(status.traffic,spec.template.spec.containerConcurrency)"

# View performance metrics in Google Cloud Console
# Navigate to: Cloud Run → nytex-dashboard → Metrics
```

---

## 📚 Related Documentation

### **Primary Deployment Guide**
- **[Enhanced Deployment Guide](./DEPLOYMENT.md)** - **Main deployment documentation** with enhanced features

### **Specialized Guides**
- **[Production Monitoring Guide](./MONITORING.md)** - Health monitoring and auto-fix capabilities
- **[CI/CD Setup](./CI_CD_SETUP.md)** - Initial CI/CD pipeline configuration
- **[Testing Strategy](./TESTING_STRATEGY.md)** - Comprehensive testing approach
- **[Secrets Management](./SECRETS_GUIDE.md)** - Google Secret Manager integration

---

## 📝 Troubleshooting CI/CD Issues

### **Common CI/CD Problems**

1. **GitHub Actions Failure**:
   - Check workflow logs in GitHub Actions tab
   - Review test failures and error messages
   - Verify secrets are properly configured

2. **IAM Permission Issues**:
   - Use enhanced deployment for automatic IAM setup: `python deploy.py`
   - See [Enhanced Deployment Guide](./DEPLOYMENT.md) for auto-fix solutions

3. **Build Failures**:
   - Check Docker build logs in GitHub Actions
   - Verify Dockerfile syntax and dependencies
   - Test build locally: `docker build .`

### **Support Resources**

- **Enhanced Deployment**: See [Enhanced Deployment Guide](./DEPLOYMENT.md)
- **Monitoring Issues**: See [Production Monitoring Guide](./MONITORING.md)
- **Infrastructure**: Google Cloud Console
- **CI/CD Logs**: GitHub Actions workflow logs

---

**💡 Recommendation**: For most deployment needs, use the **[Enhanced Deployment System](./DEPLOYMENT.md)** which provides automatic IAM setup, comprehensive monitoring, and better error handling than the traditional CI/CD pipeline. 