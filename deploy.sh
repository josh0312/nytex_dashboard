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

# Get current Square access token if it exists
CURRENT_SQUARE_TOKEN=""
EXISTING_TOKEN=$(gcloud run services describe nytex-dashboard --region us-central1 --format="value(spec.template.spec.containers[0].env[?(@.name=='SQUARE_ACCESS_TOKEN')].value)" 2>/dev/null || echo "")

if [ ! -z "$EXISTING_TOKEN" ]; then
    CURRENT_SQUARE_TOKEN="$EXISTING_TOKEN"
    echo "🔑 Preserving existing Square access token"
else
    CURRENT_SQUARE_TOKEN="REPLACE_WITH_YOUR_SQUARE_TOKEN"
    echo "⚠️  No existing Square token found - will need to be configured"
fi

# Deploy to Cloud Run with all necessary environment variables
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
    --set-env-vars "DB_USER=nytex_user" \
    --set-env-vars "DB_NAME=nytex_dashboard" \
    --set-env-vars "DB_PASS=NytexSecure2024!" \
    --set-env-vars "SECRET_KEY=prod-secret-key-2024" \
    --set-env-vars "DEBUG=false" \
    --set-env-vars "SQUARE_ENVIRONMENT=production" \
    --set-env-vars "SQUARE_ACCESS_TOKEN=$CURRENT_SQUARE_TOKEN"

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Your application is available at:"
echo "   https://nytex-dashboard-932676587025.us-central1.run.app"
echo ""
if [ "$CURRENT_SQUARE_TOKEN" == "REPLACE_WITH_YOUR_SQUARE_TOKEN" ]; then
echo "📋 Important: Configure your Square access token:"
echo "   gcloud run services update nytex-dashboard --region us-central1 \\"
echo "     --set-env-vars SQUARE_ACCESS_TOKEN=your_actual_token"
echo ""
fi
echo "🎯 Ready to sync data:"
echo "   1. Visit: https://nytex-dashboard-932676587025.us-central1.run.app/admin/sync"
echo "   2. Click 'Start Inventory Sync'"
echo "" 