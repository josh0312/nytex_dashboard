#!/bin/bash

echo "🔧 Starting NyTex Dashboard Local Development Server..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️ Virtual environment not activated. Activating .venv..."
    source .venv/bin/activate
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
pip install -q -r requirements.txt

# Start the development server
echo "🚀 Starting local server..."
echo "📱 Local app will be available at: http://localhost:8000"
echo "🌍 Cloud app is available at: https://nytex-dashboard-932676587025.us-central1.run.app"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"

python run.py 