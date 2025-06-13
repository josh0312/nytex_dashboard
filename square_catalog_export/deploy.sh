#!/bin/bash

# Square Catalog Export Service Deployment Script
set -e

echo "🚀 Starting Square Catalog Export Service deployment..."

# Configuration
PROJECT_ID="nytex-business-systems"
SERVICE_NAME="square-catalog-export"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Generate timestamp for image tagging
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${IMAGE_NAME}:${TIMESTAMP}"

echo "📦 Building Docker image for linux/amd64 platform..."
docker build --platform linux/amd64 -t ${IMAGE_TAG} .

echo "🔄 Pushing image to Google Container Registry..."
docker push ${IMAGE_TAG}

echo "☁️ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_TAG} \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --port=5001 \
    --memory=1Gi \
    --cpu=1 \
    --timeout=900 \
    --max-instances=10 \
    --set-env-vars="ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --add-cloudsql-instances=nytex-business-systems:us-central1:nytex-main-db

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: https://${SERVICE_NAME}-932676587025.${REGION}.run.app"
echo "🔍 Health check: https://${SERVICE_NAME}-932676587025.${REGION}.run.app/health"
echo ""
echo "📋 Next steps:"
echo "1. Verify the service is healthy: curl https://${SERVICE_NAME}-932676587025.${REGION}.run.app/health"
echo "2. Update main application SQUARE_CATALOG_EXPORT_URL to: https://${SERVICE_NAME}-932676587025.${REGION}.run.app"
echo "3. Ensure all secrets are configured in Google Secret Manager" 