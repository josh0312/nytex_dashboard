#!/bin/bash

# Setup Daily Sync Automation for Google Cloud
# This script creates a Cloud Scheduler job to run daily sync

echo "🔧 Setting up Daily Sync Automation for Google Cloud"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not logged into gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set project
PROJECT_ID="nytex-business-systems"
REGION="us-central1"
SERVICE_NAME="nytex-dashboard"

echo "📋 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "🚀 Service: $SERVICE_NAME"

# Enable Cloud Scheduler API
echo ""
echo "🔌 Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Create service account for scheduler (if it doesn't exist)
echo ""
echo "👤 Creating service account for scheduler..."
gcloud iam service-accounts create daily-sync-scheduler \
    --display-name="Daily Sync Scheduler" \
    --description="Service account for running daily sync jobs" \
    --project=$PROJECT_ID 2>/dev/null || echo "Service account already exists"

# Grant necessary permissions
echo ""
echo "🔐 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:daily-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

# Create the scheduler job
echo ""
echo "⏰ Creating daily sync scheduler job..."

# Get the service URL
SERVICE_URL="https://$SERVICE_NAME-932676587025.$REGION.run.app"

gcloud scheduler jobs create http daily-sync-job \
    --location=$REGION \
    --schedule="0 6 * * *" \
    --uri="$SERVICE_URL/admin/complete-sync" \
    --http-method=POST \
    --oidc-service-account-email="daily-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --headers="Content-Type=application/json" \
    --time-zone="America/Chicago" \
    --description="Daily sync job to update production data from Square" \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Daily sync automation setup complete!"
    echo ""
    echo "📋 Job Details:"
    echo "   Name: daily-sync-job"
    echo "   Schedule: 6:00 AM Central Time (daily)"
    echo "   Endpoint: $SERVICE_URL/admin/complete-sync"
    echo "   Timezone: America/Chicago"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View job: gcloud scheduler jobs describe daily-sync-job --location=$REGION"
    echo "   Run now: gcloud scheduler jobs run daily-sync-job --location=$REGION"
    echo "   Pause: gcloud scheduler jobs pause daily-sync-job --location=$REGION"
    echo "   Resume: gcloud scheduler jobs resume daily-sync-job --location=$REGION"
    echo "   Delete: gcloud scheduler jobs delete daily-sync-job --location=$REGION"
    echo ""
    echo "📊 Monitor logs:"
    echo "   gcloud run services logs read $SERVICE_NAME --region $REGION"
else
    echo ""
    echo "❌ Failed to create scheduler job"
    echo "This might be because the job already exists or there's a permission issue"
    echo ""
    echo "To delete existing job and recreate:"
    echo "   gcloud scheduler jobs delete daily-sync-job --location=$REGION"
    echo "   Then run this script again"
fi

echo ""
echo "🎉 Setup complete! Your production data will now sync daily at 6 AM Central Time." 