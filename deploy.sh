#!/bin/bash

# NyTex Dashboard - Google Cloud Run Deployment Script
# Automatically builds, tags, and deploys the application

set -e  # Exit on any error

echo "🚀 Starting NyTex Dashboard Deployment..."
echo "=================================================="

# Get current timestamp for versioning
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="gcr.io/nytex-business-systems/nytex-dashboard:$TIMESTAMP"

echo "📦 Building Docker image: $IMAGE_NAME"

# Build for linux/amd64 platform (required for Cloud Run)
docker build --platform linux/amd64 -t $IMAGE_NAME .

echo "☁️  Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

echo "🌐 Deploying to Cloud Run..."

# Deploy to Cloud Run with secrets from Secret Manager
gcloud run deploy nytex-dashboard \
    --image $IMAGE_NAME \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --add-cloudsql-instances nytex-business-systems:us-central1:nytex-main-db \
    --set-env-vars "CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1:nytex-main-db" \
    --set-env-vars "DEBUG=false" \
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
    --update-secrets "AZURE_REDIRECT_URI=azure-redirect-uri:latest"

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
echo "🎯 Next steps:"
echo "   1. Visit: https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync"
echo "   2. Test with 'Start Complete Sync'"
echo "   3. Monitor logs: gcloud run services logs read nytex-dashboard --region us-central1"
echo "" 