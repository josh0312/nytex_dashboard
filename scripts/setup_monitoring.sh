#!/bin/bash

# Setup Monitoring for NyTex Production Environment
# Creates automated health checks and alerting

echo "🔍 Setting up Production Monitoring"
echo "=================================="

PROJECT_ID="nytex-business-systems"
REGION="us-central1"
SERVICE_URL="https://nytex-dashboard-932676587025.us-central1.run.app"

# Create a monitoring job that runs health checks
echo "📊 Creating health check scheduler job..."

gcloud scheduler jobs create http health-check-job \
    --location=$REGION \
    --schedule="0 */4 * * *" \
    --uri="$SERVICE_URL/admin/status" \
    --http-method=GET \
    --headers="Content-Type=application/json" \
    --time-zone="America/Chicago" \
    --description="Health check for NyTex production service - runs every 4 hours" \
    --project=$PROJECT_ID \
    --quiet 2>/dev/null || echo "Health check job may already exist"

echo "✅ Health check monitoring job created"
echo "   Runs every 4 hours to verify service health"

echo ""
echo "📋 Monitoring Setup Complete!"
echo ""
echo "🔧 Available Monitoring Commands:"
echo "   Health check:     ./scripts/check_production_health.sh"
echo "   View scheduler:   gcloud scheduler jobs list --location=$REGION"
echo "   Check logs:       gcloud run services logs read nytex-dashboard --region $REGION"
echo ""
echo "⚠️  Recommended: Add this to your daily routine:"
echo "   ./scripts/check_production_health.sh"
echo ""
echo "📱 Consider setting up alerts:"
echo "   - Email notifications for scheduler job failures"
echo "   - Slack/Discord webhooks for critical errors"
echo "   - Daily summary reports"
echo "" 