#!/bin/bash
# Development Secrets Management Helper Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ID="nytex-business-systems"
ENV_FILE=".env.local"

print_usage() {
    echo "📋 NyTex Dashboard Secrets Management"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  init     - Initialize local environment and authenticate"
    echo "  push     - Push local .env.local to Google Secret Manager"
    echo "  pull     - Pull secrets from Google Secret Manager to .env.local"
    echo "  compare  - Compare local vs remote secrets"
    echo "  list     - List all secrets in Secret Manager"
    echo "  backup   - Backup current .env.local file"
    echo "  restore  - Restore .env.local from backup"
    echo ""
    echo "Examples:"
    echo "  $0 init     # Set up development environment"
    echo "  $0 push     # Upload your local secrets to production"
    echo "  $0 pull     # Download production secrets to local"
}

check_auth() {
    echo -e "${BLUE}🔐 Checking Google Cloud authentication...${NC}"
    
    if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | grep -q .; then
        echo -e "${RED}❌ Not authenticated with Google Cloud${NC}"
        echo -e "${YELLOW}💡 Run: gcloud auth login${NC}"
        return 1
    fi
    
    if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
        echo -e "${RED}❌ Application Default Credentials not set${NC}"
        echo -e "${YELLOW}💡 Run: gcloud auth application-default login${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Authentication OK${NC}"
    return 0
}

check_project() {
    echo -e "${BLUE}📁 Checking Google Cloud project...${NC}"
    
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        echo -e "${YELLOW}⚠️  Current project: $CURRENT_PROJECT${NC}"
        echo -e "${YELLOW}💡 Setting project to: $PROJECT_ID${NC}"
        gcloud config set project $PROJECT_ID
    fi
    
    echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"
}

backup_env() {
    if [ -f "$ENV_FILE" ]; then
        BACKUP_FILE="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$BACKUP_FILE"
        echo -e "${GREEN}✅ Backed up $ENV_FILE to $BACKUP_FILE${NC}"
    fi
}

case "${1:-help}" in
    init)
        echo -e "${BLUE}🚀 Initializing development environment...${NC}"
        
        # Check authentication
        check_auth || exit 1
        check_project
        
        # Install Python dependencies
        echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
        pip install -q google-cloud-secret-manager google-auth
        
        # Initialize secrets manager
        echo -e "${BLUE}🔧 Initializing secrets management...${NC}"
        python scripts/secrets_manager.py init --env-file "$ENV_FILE"
        
        echo -e "${GREEN}✅ Development environment initialized!${NC}"
        echo -e "${YELLOW}💡 Next steps:${NC}"
        echo "   1. Edit $ENV_FILE with your actual values"
        echo "   2. Run: $0 push    # Upload to Secret Manager"
        echo "   3. Run: docker-compose up    # Start development"
        ;;
        
    push)
        echo -e "${BLUE}⬆️  Pushing secrets to Google Secret Manager...${NC}"
        check_auth || exit 1
        check_project
        backup_env
        python scripts/secrets_manager.py push --env-file "$ENV_FILE"
        ;;
        
    pull)
        echo -e "${BLUE}⬇️  Pulling secrets from Google Secret Manager...${NC}"
        check_auth || exit 1
        check_project
        backup_env
        python scripts/secrets_manager.py pull --env-file "$ENV_FILE"
        ;;
        
    compare)
        echo -e "${BLUE}🔍 Comparing local vs remote secrets...${NC}"
        check_auth || exit 1
        check_project
        python scripts/secrets_manager.py compare --env-file "$ENV_FILE"
        ;;
        
    list)
        echo -e "${BLUE}📋 Listing secrets in Google Secret Manager...${NC}"
        check_auth || exit 1
        check_project
        python scripts/secrets_manager.py list
        ;;
        
    backup)
        echo -e "${BLUE}💾 Backing up environment file...${NC}"
        backup_env
        ;;
        
    restore)
        echo -e "${BLUE}🔄 Restoring environment file...${NC}"
        LATEST_BACKUP=$(ls -t $ENV_FILE.backup.* 2>/dev/null | head -1)
        if [ -n "$LATEST_BACKUP" ]; then
            cp "$LATEST_BACKUP" "$ENV_FILE"
            echo -e "${GREEN}✅ Restored $ENV_FILE from $LATEST_BACKUP${NC}"
        else
            echo -e "${RED}❌ No backup files found${NC}"
            exit 1
        fi
        ;;
        
    help|--help|-h|"")
        print_usage
        ;;
        
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        print_usage
        exit 1
        ;;
esac 