#!/bin/bash
set -e

echo "🔐 Loading secrets from Google Secret Manager..."

# Load secrets from Google Secret Manager
python3 /app/scripts/load_secrets.py

echo "🚀 Starting NyTex Dashboard application..."

# Start the application with uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT 