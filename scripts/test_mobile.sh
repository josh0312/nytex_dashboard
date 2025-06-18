#!/bin/bash

# Mobile Items Test Runner
# This script runs all mobile-related tests to ensure mobile functionality works before deployment

set -e  # Exit on any error

echo "🧪 Running Mobile Items Functionality Tests..."
echo "=================================================="

# Change to project directory
cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📱 Running Mobile UI Tests...${NC}"
python -m pytest -m mobile_ui -v --tb=short

echo ""
echo -e "${YELLOW}📋 Running Mobile Items Functionality Tests...${NC}"
python -m pytest -m mobile -v --tb=short

echo ""
echo -e "${YELLOW}🚀 Running Deployment Readiness Tests...${NC}"
python -m pytest -m deployment -v --tb=short

echo ""
echo -e "${GREEN}✅ All mobile tests completed successfully!${NC}"
echo ""
echo "🎯 Mobile functionality is ready for deployment:"
echo "   • Mobile navigation and UI components ✓"
echo "   • Mobile items table with responsive design ✓"
echo "   • Slide panel for item details ✓"
echo "   • Collapsible header and mobile filters ✓"
echo "   • Development toggle functionality ✓"
echo "   • Production deployment readiness ✓"
echo ""
echo "Ready to deploy with: python deploy.py" 