#!/bin/bash

# NyTex Dashboard - Legacy Manual Deployment Script
# 🚨 EMERGENCY USE ONLY - Use GitHub Actions CI/CD for normal deployments
# 
# For normal deployments, use: git push origin master
# This script is kept for emergency manual deployments only.

set -e  # Exit on any error

echo "⚠️  LEGACY MANUAL DEPLOYMENT"
echo "🚨 WARNING: This bypasses CI/CD testing and validation!"
echo "Recommended: Use 'git push origin master' for automated deployment"
echo ""
read -p "Continue with manual deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled. Use GitHub Actions for safe deployment."
    exit 1
fi

echo ""
echo "🚀 Starting Manual NyTex Dashboard Deployment..."
echo "=================================================="

# Get current timestamp for versioning
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="us-central1-docker.pkg.dev/nytex-business-systems/nytex-dashboard/nytex-dashboard:manual-$TIMESTAMP"

echo "📦 Building Docker image: $IMAGE_NAME"

# Build for linux/amd64 platform (required for Cloud Run)
docker build --platform linux/amd64 -t $IMAGE_NAME .

echo "☁️  Pushing image to Artifact Registry..."
docker push $IMAGE_NAME

echo "🌐 Deploying to Cloud Run..."

# Deploy to Cloud Run with secrets from Secret Manager
gcloud run deploy nytex-dashboard \
    --image $IMAGE_NAME \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 0 \
    --timeout 300 \
    --concurrency 80 \
    --add-cloudsql-instances nytex-business-systems:us-central1:nytex-main-db \
    --set-env-vars "CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1:nytex-main-db" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=nytex-business-systems" \
    --set-env-vars "DEBUG=false" \
    --set-env-vars "SQLALCHEMY_ECHO=false" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "SQUARE_CATALOG_EXPORT_URL=https://square-catalog-export-932676587025.us-central1.run.app" \
    --update-secrets "SECRET_KEY=secret-key:latest" \
    --update-secrets "SQLALCHEMY_DATABASE_URI=database-uri:latest" \
    --update-secrets "SQUARE_ACCESS_TOKEN=square-access-token:latest" \
    --update-secrets "SQUARE_ENVIRONMENT=square-environment:latest" \
    --update-secrets "OPENWEATHER_API_KEY=openweather-api-key:latest" \
    --update-secrets "MANUAL_USER_EMAIL=manual-user-email:latest" \
    --update-secrets "MANUAL_USER_PASSWORD=manual-user-password:latest" \
    --update-secrets "MANUAL_USER_NAME=manual-user-name:latest" \
    --update-secrets "AZURE_CLIENT_ID=azure-client-id:latest" \
    --update-secrets "AZURE_CLIENT_SECRET=azure-client-secret:latest" \
    --update-secrets "AZURE_TENANT_ID=azure-tenant-id:latest" \
    --update-secrets "AZURE_REDIRECT_URI=azure-redirect-uri:latest" \
    --update-secrets "SMTP_USERNAME=smtp-username:latest" \
    --update-secrets "SMTP_PASSWORD=smtp-password:latest" \
    --update-secrets "SMTP_SENDER_EMAIL=smtp-sender-email:latest" \
    --update-secrets "SYNC_NOTIFICATIONS_ENABLED=sync-notifications-enabled:latest" \
    --update-secrets "SYNC_NOTIFICATION_RECIPIENTS=sync-notification-recipients:latest"

echo "✅ Deployment completed successfully!"
echo ""
echo "🔍 Testing Square API connection..."

# Test the Square API connection
sleep 10  # Wait for deployment to be ready
TEST_RESULT=$(curl -s "https://nytex-dashboard-932676587025.us-central1.run.app/admin/status" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('square_config', 'unknown'))" 2>/dev/null || echo "error")

if [ "$TEST_RESULT" == "configured" ]; then
    echo "✅ Square API configuration verified"
else
    echo "⚠️  Square API configuration may have issues"
fi

echo ""
echo "🌐 Your application is available at:"
echo "   https://nytex-dashboard-932676587025.us-central1.run.app"
echo ""