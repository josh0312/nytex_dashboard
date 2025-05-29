#!/bin/bash

# Production Health Check Script
# Monitors Square API connectivity, database status, and sync functionality

echo "🏥 NyTex Production Health Check"
echo "==============================="

SERVICE_URL="https://nytex-dashboard-932676587025.us-central1.run.app"
PROJECT_ID="nytex-business-systems"
REGION="us-central1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_status() {
    local name="$1"
    local result="$2"
    
    if [ "$result" == "success" ]; then
        echo -e "  ✅ ${GREEN}$name${NC}"
        return 0
    elif [ "$result" == "warning" ]; then
        echo -e "  ⚠️  ${YELLOW}$name${NC}"
        return 1
    else
        echo -e "  ❌ ${RED}$name${NC}"
        return 2
    fi
}

echo ""
echo "🌐 Checking service availability..."

# Check if service is responding
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/" 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" == "200" ]; then
    check_status "Service is responding" "success"
else
    check_status "Service is responding (HTTP: $HTTP_STATUS)" "error"
    echo "   Service may be down or experiencing issues"
    exit 1
fi

echo ""
echo "🔧 Checking system configuration..."

# Get admin status
ADMIN_STATUS=$(curl -s "$SERVICE_URL/admin/status" 2>/dev/null || echo '{"error": "failed"}')

# Parse database status
DB_STATUS=$(echo "$ADMIN_STATUS" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('database', 'unknown'))" 2>/dev/null || echo "error")
if [ "$DB_STATUS" == "connected" ]; then
    check_status "Database connection" "success"
else
    check_status "Database connection ($DB_STATUS)" "error"
fi

# Parse Square configuration
SQUARE_CONFIG=$(echo "$ADMIN_STATUS" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('square_config', 'unknown'))" 2>/dev/null || echo "error")
if [ "$SQUARE_CONFIG" == "configured" ]; then
    check_status "Square API configuration" "success"
else
    check_status "Square API configuration ($SQUARE_CONFIG)" "error"
    echo "   Square access token may be missing or invalid"
fi

# Check location count
LOCATION_COUNT=$(echo "$ADMIN_STATUS" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('location_count', 0))" 2>/dev/null || echo "0")
if [ "$LOCATION_COUNT" -gt 0 ]; then
    check_status "Locations synced ($LOCATION_COUNT locations)" "success"
else
    check_status "Locations synced (0 locations)" "warning"
    echo "   No locations found - sync may have failed"
fi

echo ""
echo "🔄 Checking scheduler job..."

# Check if scheduler job exists and is enabled
JOB_STATUS=$(gcloud scheduler jobs describe daily-sync-job --location=$REGION --format="value(state)" 2>/dev/null || echo "NOT_FOUND")
if [ "$JOB_STATUS" == "ENABLED" ]; then
    check_status "Daily sync job is enabled" "success"
elif [ "$JOB_STATUS" == "PAUSED" ]; then
    check_status "Daily sync job is paused" "warning"
    echo "   Resume with: gcloud scheduler jobs resume daily-sync-job --location=$REGION"
else
    check_status "Daily sync job ($JOB_STATUS)" "error"
    echo "   Create with: ./scripts/setup_daily_sync.sh"
fi

echo ""
echo "📊 Testing Square API connectivity..."

# Test Square API by triggering a small sync test
TEST_RESPONSE=$(curl -s -X POST "$SERVICE_URL/locations/sync" 2>/dev/null || echo '{"success": false}')
TEST_SUCCESS=$(echo "$TEST_RESPONSE" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('success', False))" 2>/dev/null || echo "False")

if [ "$TEST_SUCCESS" == "True" ]; then
    check_status "Square API connectivity test" "success"
else
    check_status "Square API connectivity test" "error"
    echo "   Square API authentication may be failing"
    echo "   Check logs: gcloud run services logs read nytex-dashboard --region $REGION"
fi

echo ""
echo "📈 Recent sync activity..."

# Check recent logs for sync activity
RECENT_SYNC=$(gcloud run services logs read nytex-dashboard --region $REGION --limit=50 2>/dev/null | grep -E "(complete-sync|sync successful)" | tail -1 || echo "")
if [ ! -z "$RECENT_SYNC" ]; then
    echo "  📅 Last sync activity:"
    echo "     $RECENT_SYNC"
else
    echo "  ⚠️  No recent sync activity found"
fi

# Check for recent errors
RECENT_ERRORS=$(gcloud run services logs read nytex-dashboard --region $REGION --limit=50 2>/dev/null | grep -E "(ERROR|AUTHENTICATION_ERROR|UNAUTHORIZED)" | wc -l || echo "0")
if [ "$RECENT_ERRORS" -gt 0 ]; then
    echo "  ❌ $RECENT_ERRORS recent errors found"
    echo "     Run: gcloud run services logs read nytex-dashboard --region $REGION | grep ERROR | tail -5"
else
    echo "  ✅ No recent errors detected"
fi

echo ""
echo "🎯 Quick Actions:"
echo "   Test sync:    curl -X POST $SERVICE_URL/admin/complete-sync"
echo "   View admin:   $SERVICE_URL/admin/sync"
echo "   Check logs:   gcloud run services logs read nytex-dashboard --region $REGION"
echo "   Run sync now: gcloud scheduler jobs run daily-sync-job --location=$REGION"
echo "" 