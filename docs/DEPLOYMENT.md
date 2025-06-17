# 🚀 NyTex Dashboard - Enhanced Deployment & Monitoring Guide

## 📋 Quick Reference

| Environment | URL | Status Check |
|-------------|-----|--------------|
| **Local Development** | http://localhost:8000 | `curl http://localhost:8000` |
| **Cloud Production** | https://nytex-dashboard-932676587025.us-central1.run.app | `curl https://nytex-dashboard-932676587025.us-central1.run.app` |

---

## 🎯 **NEW: Enhanced Deployment System**

### **One-Command Deployment with Built-in Safety**
```bash
# Enhanced deployment with automatic IAM setup and monitoring
python deploy.py
```

**What the enhanced deployment does:**
- ✅ **Automatic IAM Permission Setup** - Prevents deployment failures
- ✅ **Cloud Run Access Verification** - Ensures service connectivity
- ✅ **Comprehensive Testing** - Multi-stage validation before deployment
- ✅ **Enhanced Monitoring** - Real-time deployment progress tracking
- ✅ **Automatic Rollback** - Falls back on failure
- ✅ **Visual Progress** - Beautiful colored output with spinners

### **Advanced Deployment Options**
```bash
# Direct enhanced deployment script
python scripts/enhanced_deploy.py

# Legacy deployment (for emergencies only)
./deploy.sh
```

---

## 🔍 **NEW: Production Health Monitoring**

### **Automated Health Monitoring**
```bash
# Single health check with auto-fix capability
python scripts/deployment_monitor.py --auto-fix

# Continuous monitoring (every 30 minutes)
python scripts/deployment_monitor.py --continuous 30

# Check current monitoring status
./scripts/check_monitoring.sh
```

### **Monitoring Management**
```bash
# Start background monitoring
./scripts/start_monitoring.sh

# Stop background monitoring  
./scripts/stop_monitoring.sh

# Setup automated cron jobs
./scripts/setup_monitoring.sh
```

### **What Health Monitoring Checks:**
- 🔐 **IAM Permissions** - GitHub Actions service account permissions
- ☁️ **Cloud Run Service** - Service status and revision health
- 🌐 **Application Health** - HTTP response and connectivity
- 📊 **Recent Deployments** - Failure detection and analysis
- 🗄️ **Database Connectivity** - Connection verification

### **Automatic Issue Resolution**
The monitoring system can automatically fix:
- **IAM Permission Issues** - Restores GitHub Actions permissions
- **Service Account Problems** - Reconfigures compute service account access
- **Traffic Routing Issues** - Ensures proper revision activation

---

## 🔄 Daily Development Workflow

### 1. **Start Local Development**
```bash
./start-local.sh
```
**What it does:**
- ✅ Auto-activates virtual environment (`.venv`)
- ✅ Installs/updates dependencies from `requirements.txt`
- ✅ Starts FastAPI server at http://localhost:8000
- ✅ Enables hot-reload for development

### 2. **Make Changes & Test**
- Edit your code in your preferred editor
- Changes auto-reload in the browser (thanks to uvicorn)
- Test thoroughly at http://localhost:8000
- Check logs in the terminal for any errors

### 3. **Deploy to Production (Enhanced)**
```bash
# Use the new enhanced deployment system
python deploy.py
```

**Enhanced deployment process:**
1. 🔧 **IAM Permission Setup** - Ensures GitHub Actions can manage deployments
2. ☁️ **Cloud Run Verification** - Confirms service accessibility
3. 🧪 **Deployment Readiness Tests** - Comprehensive pre-deployment validation
4. 📤 **Git Push & CI/CD Trigger** - Automated commit and push
5. 👀 **Real-time Monitoring** - Tracks deployment progress with visual feedback
6. ✅ **Health Verification** - Confirms successful deployment

**⚠️ Important**: The deployment script now uses Google Secret Manager for all sensitive configuration. See [Secrets Management Guide](SECRETS_GUIDE.md) for details.

**🔧 If deployment fails**: The enhanced system includes automatic rollback and detailed error reporting. See [Troubleshooting Guide](TROUBLESHOOTING.md) for additional help.

---

## 📊 **NEW: Monitoring Dashboard**

### **Health Report Example**
```
============================================================
NyTex Dashboard - Deployment Health Report
============================================================
Timestamp: 2025-06-17 17:12:09
Production URL: https://nytex-dashboard-nndn66l4ua-uc.a.run.app

✅ ALL SYSTEMS HEALTHY

✅ IAM permissions are correctly configured
✅ Cloud Run service is ready
✅ Application healthy (HTTP 302)
✅ No recent deployment failures
✅ Database connectivity appears healthy
============================================================
```

### **Scheduled Monitoring (Optional)**
Set up automated monitoring with intelligent scheduling:
```bash
./scripts/setup_monitoring.sh
```

**Monitoring Schedule:**
- **Business Hours** (8 AM - 8 PM, Mon-Fri): Every 15 minutes
- **Off Hours & Weekends**: Every hour  
- **Daily Comprehensive Check**: 6 AM with detailed reporting

---

## 📦 Production Data Sync

**After deploying to production, you need to sync data from Square:**

### **Step 1: Configure Square Access Token**
```bash
# Replace YOUR_SQUARE_ACCESS_TOKEN with your actual token
gcloud run services update nytex-dashboard --region us-central1 \
  --set-env-vars SQUARE_ACCESS_TOKEN=YOUR_SQUARE_ACCESS_TOKEN
```

### **Step 2: Sync Inventory Data**
```bash
# Run the inventory sync script
python scripts/sync_inventory_only.py
```

### **Step 3: Verify Data**
- Visit: https://nytex-dashboard-932676587025.us-central1.run.app
- Check the "Low Item Stock Report" to see if data is loading
- If no data appears, check production logs

---

## ⚡ Quick Commands

### **Server Management**
```bash
# Start local development server
./start-local.sh

# Deploy to cloud production
./deploy.sh

# Sync production data from Square
python scripts/sync_inventory_only.py

# Stop local server
# Press Ctrl+C in the terminal where it's running
```

### **Status Checking**
```bash
# Check cloud service status
gcloud run services list --region us-central1

# View cloud service details
gcloud run services describe nytex-dashboard --region us-central1

# Check if local server is responding
curl http://localhost:8000

# Check if cloud server is responding
curl https://nytex-dashboard-932676587025.us-central1.run.app
```

### **Monitoring & Logs**
```bash
# View recent cloud logs
gcloud run services logs read nytex-dashboard --region us-central1 --limit=50

# Follow cloud logs in real-time
gcloud run services logs tail nytex-dashboard --region us-central1

# Check database connection
gcloud sql instances list
```

---

## 🏗️ Infrastructure Details

### **Google Cloud Setup**
- **Project**: nytex-business-systems
- **Region**: us-central1 (Iowa)
- **Database**: Cloud SQL PostgreSQL 17
- **Container**: Cloud Run (auto-scaling)

### **Database Configuration**
- **Instance**: nytex-main-db
- **Database**: square_data_sync *(production database)*
- **User**: nytex_user
- **Connection**: Automatic via Cloud SQL Proxy in Cloud Run
- **Connection Name**: nytex-business-systems:us-central1:nytex-main-db

### **Cost Estimates**
- **Cloud SQL**: ~$7-15/month
- **Cloud Run**: ~$0-10/month (usage-based)
- **Total**: ~$7-25/month

### **Database Issues**

**🚨 CRITICAL**: If you're experiencing database connectivity issues, see the **[Complete Troubleshooting Guide](TROUBLESHOOTING.md)** for detailed solutions.

**Problem**: Cannot connect to Cloud SQL
```bash
# Test database connection
gcloud sql connect nytex-main-db --user=nytex_user --database=square_data_sync

# Check if instance is running  
gcloud sql instances list

# Verify correct connection name
gcloud sql instances describe nytex-main-db --format="value(connectionName)"
```

**Problem**: "Connect call failed" or "Connection refused"
```bash
# Check service status immediately
curl -s https://nytex-dashboard-932676587025.us-central1.run.app/admin/status | python3 -m json.tool

# See TROUBLESHOOTING.md for complete solutions
```

---

## 🔧 Enhanced Troubleshooting

### **IAM Permission Issues (Auto-Fixable)**

**Problem**: Deployment fails with "Permission 'iam.serviceaccounts.actAs' denied"
```bash
# Automatic fix
python scripts/deployment_monitor.py --auto-fix

# Manual fix
gcloud iam service-accounts add-iam-policy-binding \
  932676587025-compute@developer.gserviceaccount.com \
  --member="serviceAccount:github-actions@nytex-business-systems.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### **Deployment Monitoring Issues**

**Problem**: Want to check deployment health
```bash
# Quick health check
python scripts/deployment_monitor.py

# Comprehensive check with auto-fix
python scripts/deployment_monitor.py --auto-fix

# Check monitoring status
./scripts/check_monitoring.sh
```

**Problem**: Deployment seems stuck
```bash
# Enhanced deployment with better monitoring
python deploy.py

# Direct monitoring of Cloud Run revisions
gcloud run revisions list --service=nytex-dashboard --region=us-central1
```

### **Local Development Issues**

**Problem**: `python run.py` fails
```bash
# Solution: run.py has been removed - use the modern approach
./start-local.sh

# Or manually:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **Cloud Deployment Issues**

**Problem**: Deployment fails
```bash
# Use enhanced deployment for better error handling
python deploy.py

# Check deployment health
python scripts/deployment_monitor.py --auto-fix

# Verify Docker is running
docker --version

# Verify gcloud authentication
gcloud auth list

# Check project is set correctly
gcloud config get project
```

**Problem**: Cloud app returns 500 errors
```bash
# Check logs for detailed error messages
gcloud run services logs read nytex-dashboard --region us-central1 --limit=20

# Run health monitoring
python scripts/deployment_monitor.py
```

---

## 📚 **Enhanced Documentation Structure**

- **[Enhanced Deployment Guide](DEPLOYMENT.md)** - This document (primary deployment & monitoring guide)
- **[CI/CD Pipeline Guide](../PRODUCTION_DEPLOYMENT_GUIDE.md)** - GitHub Actions CI/CD pipeline details
- **[Production Monitoring Guide](MONITORING.md)** - Complete monitoring setup and management
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Issue resolution
- **[Secrets Management Guide](SECRETS_GUIDE.md)** - Security configuration

---

## 🎉 **What's New in Enhanced Deployment**

### **Reliability Improvements:**
- ✅ **Zero IAM Permission Failures** - Automatic setup prevents common deployment issues
- ✅ **Enhanced Error Handling** - Better timeout management and fallback strategies  
- ✅ **Comprehensive Pre-flight Checks** - Multi-stage verification before deployment
- ✅ **Visual Progress Tracking** - Beautiful colored output with real-time updates

### **Monitoring & Alerting:**
- ✅ **Proactive Issue Detection** - Catches problems before they cause outages
- ✅ **Automated Recovery** - Auto-fix capability reduces manual intervention
- ✅ **Intelligent Scheduling** - More frequent checks during business hours
- ✅ **Comprehensive Logging** - All monitoring activity logged for analysis

### **Operational Excellence:**
- ✅ **One-Command Deployment** - `python deploy.py` handles everything
- ✅ **Production-Ready Monitoring** - Enterprise-grade health checking
- ✅ **Easy Management** - Simple start/stop/check commands for monitoring
- ✅ **Historical Tracking** - All reports saved with timestamps

**The enhanced deployment system provides bulletproof reliability with multiple layers of protection against common deployment failures!** 🛡️

---

## 🚨 Emergency Procedures

### **Rollback Cloud Deployment**
```bash
# List recent revisions
gcloud run revisions list --service=nytex-dashboard --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic nytex-dashboard --region=us-central1 --to-revisions=REVISION_NAME=100
```

### **Database Recovery**
```bash
# Connect to database directly
gcloud sql connect nytex-main-db --user=nytex_user --database=nytex_dashboard

# View database backups
gcloud sql backups list --instance=nytex-main-db
```

### **Complete Service Reset**
```bash
# Delete and recreate service (nuclear option)
gcloud run services delete nytex-dashboard --region=us-central1
./deploy.sh  # Redeploy from scratch
```

---

## 📞 Support Information

**Created**: May 29, 2025  
**Google Cloud Project**: nytex-business-systems  
**Primary Developer**: joshgoble@gmail.com

For issues or questions, check the troubleshooting section above or review the deployment logs. 