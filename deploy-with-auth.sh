#!/bin/bash
# Deploy NyTex Dashboard with Authentication to Google Cloud Run

echo "🚀 Deploying NyTex Dashboard with Authentication System"
echo "=================================================="

# Check if required Azure values are provided
if [ -z "$AZURE_CLIENT_ID" ] || [ -z "$AZURE_CLIENT_SECRET" ] || [ -z "$AZURE_TENANT_ID" ]; then
    echo "⚠️  Azure environment variables not set. Setting up with manual auth only."
    echo "   To enable O365 integration later, set these environment variables:"
    echo "   - AZURE_CLIENT_ID"
    echo "   - AZURE_CLIENT_SECRET" 
    echo "   - AZURE_TENANT_ID"
    echo ""
fi

# Deploy to Cloud Run with authentication environment variables
gcloud run deploy nytex-dashboard \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "SECRET_KEY=NwdCDlUofwGFus3gco9wYncf0JiwxBRD_Z0v6eEaSjk" \
    --set-env-vars "MANUAL_USER_EMAIL=guest@nytexfireworks.com" \
    --set-env-vars "MANUAL_USER_PASSWORD=NytexD@shboard2025!" \
    --set-env-vars "MANUAL_USER_NAME=Guest User" \
    --set-env-vars "AZURE_REDIRECT_URI=https://nytex-dashboard-932676587025.us-central1.run.app/auth/callback" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "DEBUG=False" \
    ${AZURE_CLIENT_ID:+--set-env-vars "AZURE_CLIENT_ID=$AZURE_CLIENT_ID"} \
    ${AZURE_CLIENT_SECRET:+--set-env-vars "AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET"} \
    ${AZURE_TENANT_ID:+--set-env-vars "AZURE_TENANT_ID=$AZURE_TENANT_ID"} \
    --cpu 1 \
    --memory 1Gi \
    --timeout 300 \
    --max-instances 10 \
    --port 8080

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "🔗 Your dashboard URL: https://nytex-dashboard-932676587025.us-central1.run.app/"
    echo ""
    echo "🔐 Authentication Status:"
    echo "   ✅ Manual Login: guest@nytexfireworks.com / NytexD@shboard2025!"
    if [ -n "$AZURE_CLIENT_ID" ]; then
        echo "   ✅ O365 Login: Configured for @nytexfireworks.com users"
    else
        echo "   ⚠️  O365 Login: Not configured (manual auth only)"
    fi
    echo ""
    echo "📖 Next Steps:"
    echo "   1. Visit your dashboard URL"
    echo "   2. You should be redirected to login page"
    echo "   3. Test manual login with guest credentials"
    if [ -n "$AZURE_CLIENT_ID" ]; then
        echo "   4. Test O365 login with @nytexfireworks.com account"
    else
        echo "   4. Set up O365 integration using AZURE_O365_SETUP.md"
    fi
    echo ""
else
    echo "❌ Deployment failed. Check the logs above for errors."
    exit 1
fi 