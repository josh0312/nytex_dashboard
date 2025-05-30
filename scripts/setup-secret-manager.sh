#!/bin/bash

# Setup Script for Square Access Token in Google Secret Manager
# This script helps configure secure storage of the Square access token

set -e

echo "🔐 Setting up Square Access Token in Google Secret Manager"
echo "=================================================="

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

echo "📋 Current project: $PROJECT_ID"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
echo "📋 Project number: $PROJECT_NUMBER"

# Check if secret already exists
if gcloud secrets describe square-access-token &> /dev/null; then
    echo "⚠️  Secret 'square-access-token' already exists"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📝 Please enter your Square access token:"
        read -s SQUARE_TOKEN
        echo "$SQUARE_TOKEN" | gcloud secrets versions add square-access-token --data-file=-
        echo "✅ Secret updated successfully"
    else
        echo "ℹ️  Skipping secret creation"
    fi
else
    echo "📝 Please enter your Square access token:"
    read -s SQUARE_TOKEN
    echo "$SQUARE_TOKEN" | gcloud secrets create square-access-token --data-file=-
    echo "✅ Secret created successfully"
fi

# Grant access to Cloud Run service account
echo "🔑 Granting access to Cloud Run service account..."
gcloud secrets add-iam-policy-binding square-access-token \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

echo "✅ IAM policy binding added"

# Verify setup
echo "🔍 Verifying setup..."
if gcloud secrets versions access latest --secret="square-access-token" > /dev/null; then
    echo "✅ Secret is accessible"
else
    echo "❌ Error: Cannot access secret"
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Summary:"
echo "   • Secret name: square-access-token"
echo "   • Project: $PROJECT_ID"
echo "   • Service account: ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo ""
echo "🚀 Next steps:"
echo "   1. Deploy your application with the updated cloudbuild.yaml"
echo "   2. The SQUARE_ACCESS_TOKEN will be automatically injected from Secret Manager"
echo ""
echo "💡 To update the token in the future:"
echo "   echo 'new_token' | gcloud secrets versions add square-access-token --data-file=-" 