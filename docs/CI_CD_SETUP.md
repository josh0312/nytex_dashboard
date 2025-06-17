# CI/CD Pipeline Setup Guide

This document explains the new automated CI/CD pipeline for the NyTex Dashboard application using GitHub Actions and Google Cloud Run.

## 🎯 Overview

The CI/CD pipeline provides:
- **Automated testing** on every pull request
- **Staging deployments** for testing changes
- **Production deployments** from the main branch
- **Rollback capabilities** if deployments fail
- **Health checks** and verification

## 🏗️ Pipeline Architecture

```
Feature Branch → PR → Staging Environment → Merge → Production Environment
     ↓              ↓              ↓              ↓
   Tests        Staging Tests   Final Tests   Health Checks
```

### Environments

1. **Staging**: `nytex-dashboard-staging`
   - Deployed on PR creation and `develop/staging` branches
   - Lower resource allocation (512Mi RAM, 0.5 CPU)
   - Debug mode enabled for easier troubleshooting

2. **Production**: `nytex-dashboard`
   - Deployed on `main/master` branch merges
   - Full resource allocation (1Gi RAM, 1 CPU)
   - Production optimized settings

## 🔧 Setup Instructions

### 1. Create Google Cloud Service Account

```bash
# Create service account
gcloud iam service-accounts create github-actions \
    --description="Service account for GitHub Actions" \
    --display-name="GitHub Actions"

# Grant necessary permissions
gcloud projects add-iam-policy-binding nytex-business-systems \
    --member="serviceAccount:github-actions@nytex-business-systems.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding nytex-business-systems \
    --member="serviceAccount:github-actions@nytex-business-systems.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding nytex-business-systems \
    --member="serviceAccount:github-actions@nytex-business-systems.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding nytex-business-systems \
    --member="serviceAccount:github-actions@nytex-business-systems.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Create and download service account key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions@nytex-business-systems.iam.gserviceaccount.com
```

### 2. Configure GitHub Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secret:

- **GCP_SA_KEY**: Contents of the `github-actions-key.json` file

### 3. Set Up Artifact Registry (if not already done)

```bash
# Create repository for container images
gcloud artifacts repositories create nytex-dashboard \
    --repository-format=docker \
    --location=us-central1 \
    --description="NyTex Dashboard container images"
```

## 🚀 How to Use the Pipeline

### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # Make your changes
   git add .
   git commit -m "Add your feature"
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request**:
   - Automatically triggers staging deployment
   - Runs tests and linting
   - Comments on PR with staging URL

3. **Test in staging**:
   - Visit the staging URL provided in the PR comment
   - Verify your changes work correctly

4. **Merge to main**:
   - Triggers production deployment
   - Includes health checks and rollback on failure

### Manual Deployments

You can trigger deployments manually from the GitHub Actions tab:

1. Go to your repository → Actions
2. Select the workflow (Deploy to Production or Deploy to Staging)
3. Click "Run workflow"

## 📊 Monitoring and Logs

### Health Checks

Both pipelines include automatic health checks:
- Basic connectivity test
- Database connection verification
- Square API configuration check

### Viewing Logs

```bash
# Production logs
gcloud run services logs read nytex-dashboard --region us-central1

# Staging logs
gcloud run services logs read nytex-dashboard-staging --region us-central1
```

### Service URLs

- **Production**: https://nytex-dashboard-932676587025.us-central1.run.app
- **Staging**: https://nytex-dashboard-staging-nndn66l4ua-uc.a.run.app

## 🔐 Security Features

- Service account with minimal required permissions
- Secrets managed via Google Secret Manager
- Automatic rollback on deployment failure
- Environment-specific configurations

## 🚨 Troubleshooting

### Common Issues

1. **Permission Denied Errors**:
   - Verify service account has correct IAM roles
   - Check that GCP_SA_KEY secret is properly set

2. **Database Connection Issues**:
   - Verify Cloud SQL instance is running
   - Check that database-uri secret is properly configured
   - Ensure user has correct permissions

3. **Container Build Failures**:
   - Check Dockerfile syntax
   - Verify all dependencies are in requirements.txt
   - Review build logs in GitHub Actions

### Manual Rollback

If you need to manually rollback:

```bash
# List recent revisions
gcloud run revisions list --service=nytex-dashboard --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic nytex-dashboard \
    --region=us-central1 \
    --to-revisions=REVISION_NAME=100
```

## 🎯 Next Steps

After setting up the CI/CD pipeline:

1. **Test the workflow** by creating a test PR
2. **Monitor deployments** for the first few releases
3. **Configure branch protection** rules in GitHub
4. **Set up notifications** for deployment failures
5. **Consider adding integration tests** for critical paths

## 📝 Pipeline Files

- `.github/workflows/deploy-production.yml` - Production deployment
- `.github/workflows/deploy-staging.yml` - Staging deployment
- `deploy.sh` - Legacy manual deployment script (kept for emergency use)

The new CI/CD pipeline replaces manual deployments while providing better reliability, testing, and rollback capabilities. 