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

# Check for Square access token
SQUARE_TOKEN=""
if [ ! -z "$SQUARE_ACCESS_TOKEN" ]; then
    SQUARE_TOKEN="$SQUARE_ACCESS_TOKEN"
    echo "🔑 Using Square access token from environment"
else
    # Try to get from existing deployment
    EXISTING_TOKEN=$(gcloud run services describe nytex-dashboard --region us-central1 --format="value(spec.template.spec.template.spec.containers[0].env[?(@.name=='SQUARE_ACCESS_TOKEN')].value)" 2>/dev/null || echo "")
    
    if [ ! -z "$EXISTING_TOKEN" ] && [ "$EXISTING_TOKEN" != "REPLACE_WITH_YOUR_SQUARE_TOKEN" ]; then
        SQUARE_TOKEN="$EXISTING_TOKEN"
        echo "🔑 Preserving existing Square access token"
    else
        echo "❌ ERROR: No valid Square access token found!"
        echo "   Please set SQUARE_ACCESS_TOKEN environment variable before deploying"
        echo "   export SQUARE_ACCESS_TOKEN=your_actual_token"
        echo "   Then run this script again"
        exit 1
    fi
fi

# Validate token format (Square tokens start with specific prefixes)
if [[ ! "$SQUARE_TOKEN" =~ ^(EAA|EAAA) ]]; then
    echo "❌ WARNING: Square token doesn't appear to be valid format"
    echo "   Square production tokens typically start with 'EAA' or 'EAAA'"
    echo "   Current token: ${SQUARE_TOKEN:0:10}..."
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
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
    --set-env-vars "SQUARE_ACCESS_TOKEN=$SQUARE_TOKEN"

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