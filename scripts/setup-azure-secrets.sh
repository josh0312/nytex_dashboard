#!/bin/bash

# Setup Script for Azure/O365 Secrets in Google Secret Manager
# This script helps configure secure storage of Azure credentials

set -e

echo "🔐 Setting up Azure/O365 Secrets in Google Secret Manager"
echo "========================================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "   Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "   Please run: gcloud auth login"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No project set"
    echo "   Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Project: $PROJECT_ID"
echo ""

# Function to create secret
create_secret() {
    local secret_name=$1
    local secret_description=$2
    
    echo "🔑 Setting up secret: $secret_name"
    
    # Check if secret already exists
    if gcloud secrets describe "$secret_name" &>/dev/null; then
        echo "   ✅ Secret '$secret_name' already exists"
        read -p "   Do you want to update it? (y/N): " update_secret
        if [[ $update_secret =~ ^[Yy]$ ]]; then
            read -s -p "   Enter the new value for $secret_name: " secret_value
            echo ""
            echo "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
            echo "   ✅ Secret '$secret_name' updated"
        else
            echo "   ⏭️  Skipping '$secret_name'"
        fi
    else
        echo "   Creating new secret '$secret_name'"
        read -s -p "   Enter the value for $secret_name: " secret_value
        echo ""
        
        if [ -z "$secret_value" ]; then
            echo "   ⚠️  Empty value provided, skipping '$secret_name'"
            return
        fi
        
        # Create the secret
        gcloud secrets create "$secret_name" --data-file=- <<< "$secret_value"
        echo "   ✅ Secret '$secret_name' created"
    fi
    echo ""
}

echo "🔐 Azure/O365 Credentials Setup"
echo "================================"
echo ""
echo "You'll need these values from your Azure App Registration:"
echo "1. Application (client) ID"
echo "2. Client Secret Value"  
echo "3. Directory (tenant) ID"
echo ""
echo "If you don't have these yet, follow the guide in docs/AZURE_O365_SETUP.md"
echo ""

read -p "Do you have your Azure credentials ready? (y/N): " has_credentials

if [[ ! $has_credentials =~ ^[Yy]$ ]]; then
    echo ""
    echo "📖 Please complete the Azure App Registration first:"
    echo "   1. Follow the guide in docs/AZURE_O365_SETUP.md"
    echo "   2. Get your Client ID, Client Secret, and Tenant ID"
    echo "   3. Run this script again"
    echo ""
    exit 0
fi

echo ""
echo "🔑 Creating Azure secrets..."
echo ""

# Create Azure secrets
create_secret "azure-client-id" "Azure Application Client ID"
create_secret "azure-client-secret" "Azure Application Client Secret"
create_secret "azure-tenant-id" "Azure Directory Tenant ID"

echo "🔐 Setting up IAM permissions..."
echo ""

# Get the Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe nytex-dashboard --region=us-central1 --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null || echo "")

if [ -z "$SERVICE_ACCOUNT" ]; then
    # Use default compute service account
    SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"
    echo "   Using default service account: $SERVICE_ACCOUNT"
else
    echo "   Using service account: $SERVICE_ACCOUNT"
fi

# Grant access to secrets
for secret in "azure-client-id" "azure-client-secret" "azure-tenant-id"; do
    if gcloud secrets describe "$secret" &>/dev/null; then
        echo "   Granting access to $secret..."
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" &>/dev/null || true
    fi
done

echo ""
echo "✅ Azure secrets setup complete!"
echo ""
echo "📋 Summary:"
echo "   ✅ Azure secrets created in Secret Manager"
echo "   ✅ IAM permissions configured"
echo "   ✅ Ready for deployment"
echo ""
echo "🚀 Next steps:"
echo "   1. Deploy with: gcloud builds submit --config cloudbuild.yaml"
echo "   2. Test O365 login at your dashboard URL"
echo ""
echo "🔗 Your dashboard: https://nytex-dashboard-932676587025.us-central1.run.app/" 