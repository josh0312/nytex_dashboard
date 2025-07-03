#!/bin/bash

# Setup Orchestrator Sync for Google Cloud Scheduler
# This creates a new comprehensive sync job that runs 1 hour earlier than current sync

echo "🔧 Setting up Orchestrator Sync for Google Cloud"
echo "================================================"

# Configuration
PROJECT_ID="nytex-business-systems"
REGION="us-central1"
SERVICE_NAME="nytex-dashboard"
JOB_NAME="nytex-orchestrator-sync"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not logged into gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

echo "📋 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"  
echo "🚀 Service: $SERVICE_NAME"
echo "📅 Job: $JOB_NAME"

# Get the current service URL
echo ""
echo "🔍 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    echo "❌ Could not get service URL. Is the service deployed?"
    exit 1
fi

echo "✅ Service URL: $SERVICE_URL"

# Check if job already exists
echo ""
echo "🔍 Checking if scheduler job already exists..."
if gcloud scheduler jobs describe $JOB_NAME --location=$REGION >/dev/null 2>&1; then
    echo "⚠️  Job $JOB_NAME already exists"
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting existing job..."
        gcloud scheduler jobs delete $JOB_NAME --location=$REGION --quiet
    else
        echo "ℹ️  Keeping existing job. Exiting."
        exit 0
    fi
fi

# Create the new comprehensive orchestrator sync job
echo ""
echo "⏰ Creating orchestrator sync scheduler job..."

gcloud scheduler jobs create http $JOB_NAME \
    --location=$REGION \
    --schedule="0 6 * * *" \
    --uri="$SERVICE_URL/admin/orchestrator-sync" \
    --http-method=POST \
    --oidc-service-account-email="daily-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --headers="Content-Type=application/json" \
    --time-zone="America/Chicago" \
    --description="Comprehensive daily sync using orchestrator (all data types: orders, catalog, locations, inventory)" \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Orchestrator sync job created successfully!"
    echo ""
    echo "📋 Job Details:"
    echo "   Name: $JOB_NAME"
    echo "   Schedule: 1:00 AM Central Time (daily)"
    echo "   Endpoint: $SERVICE_URL/admin/orchestrator-sync"
    echo "   Data Types: orders, catalog_items, catalog_categories, locations, inventory"
    echo "   Timezone: America/Chicago"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View job: gcloud scheduler jobs describe $JOB_NAME --location=$REGION"
    echo "   Run now: gcloud scheduler jobs run $JOB_NAME --location=$REGION"
    echo "   Pause: gcloud scheduler jobs pause $JOB_NAME --location=$REGION"
    echo "   Resume: gcloud scheduler jobs resume $JOB_NAME --location=$REGION"
    echo "   Delete: gcloud scheduler jobs delete $JOB_NAME --location=$REGION"
    echo ""
    echo "📊 Monitor logs:"
    echo "   gcloud run services logs read $SERVICE_NAME --region $REGION --filter='orchestrator-sync'"
    echo ""
    echo "🎯 Current Schedule Setup:"
    echo "   📅 1:00 AM CDT - $JOB_NAME (comprehensive)"
    echo "   📅 2:00 AM CDT - Development sync (laptop)"
    echo "   📅 7:00 AM CDT - Legacy nytex-sync-daily (orders only)"
    echo ""
    echo "🚦 Next Steps:"
    echo "   1. Test the new endpoint manually"
    echo "   2. Monitor parallel operation for 2-3 days"
    echo "   3. Switch traffic to new comprehensive method"
    echo "   4. Remove legacy sync job"
else
    echo ""
    echo "❌ Failed to create orchestrator sync job"
    echo "This might be because of a permission issue or missing service account"
    echo ""
    echo "To check/create service account:"
    echo "   gcloud iam service-accounts describe daily-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com"
    echo ""
    echo "If service account doesn't exist, create it:"
    echo "   gcloud iam service-accounts create daily-sync-scheduler --display-name='Daily Sync Scheduler'"
    echo "   gcloud projects add-iam-policy-binding $PROJECT_ID --member='serviceAccount:daily-sync-scheduler@$PROJECT_ID.iam.gserviceaccount.com' --role='roles/run.invoker'"
fi

echo ""
echo "�� Setup complete!" 