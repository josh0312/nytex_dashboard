# 🚀 NyTex Dashboard - Server Management Guide

## 📋 Quick Reference

| Environment | URL | Status Check |
|-------------|-----|--------------|
| **Local Development** | http://localhost:8000 | `curl http://localhost:8000` |
| **Cloud Production** | https://nytex-dashboard-932676587025.us-central1.run.app | `curl https://nytex-dashboard-932676587025.us-central1.run.app` |

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

### 3. **Deploy to Production**
```bash
./deploy.sh
```
**What it does:**
- 🐳 Builds Docker image for linux/amd64 platform
- 🏷️ Tags with timestamp version (e.g., `20250529-143052`)
- ☁️ Pushes to Google Container Registry
- 🌐 Deploys to Cloud Run with full database configuration
- ✅ Updates live site automatically

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
- **Database**: nytex_dashboard
- **User**: nytex_user
- **Connection**: Automatic via Cloud SQL Proxy

### **Cost Estimates**
- **Cloud SQL**: ~$7-15/month
- **Cloud Run**: ~$0-10/month (usage-based)
- **Total**: ~$7-25/month

---

## 🔧 Troubleshooting

### **Local Development Issues**

**Problem**: `python run.py` fails
```bash
# Solution: Activate virtual environment first
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

**Problem**: Database connection errors locally
```bash
# Check if you have local PostgreSQL running or use cloud fallback
# The app will automatically fall back to local config when cloud vars aren't set
```

### **Cloud Deployment Issues**

**Problem**: Deployment fails
```bash
# Check Docker is running
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
```

### **Data Sync Issues**

**Problem**: "Square access token not configured"
```bash
# Add your Square access token to production
gcloud run services update nytex-dashboard --region us-central1 \
  --set-env-vars SQUARE_ACCESS_TOKEN=your_actual_token
```

**Problem**: Sync times out or fails
```bash
# Large datasets can take 10+ minutes to sync
# Check production logs to see if sync is still running
gcloud run services logs tail nytex-dashboard --region us-central1
```

**Problem**: No data appears in production
```bash
# 1. Verify Square token is configured
# 2. Check sync logs for errors
# 3. Try running sync again: python scripts/sync_inventory_only.py
```

### **Database Issues**

**Problem**: Cannot connect to Cloud SQL
```bash
# Test database connection
gcloud sql connect nytex-main-db --user=nytex_user --database=nytex_dashboard

# Check if instance is running
gcloud sql instances list
```

---

## 🔄 Environment Variables

### **Local Development**
The app automatically detects local vs cloud environment:
- Uses local database fallback when cloud variables aren't present
- Loads from `.env` file if present (not in git)

### **Cloud Production**
Automatically configured during deployment:
```bash
CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1-f:nytex-main-db
DB_USER=nytex_user
DB_NAME=nytex_dashboard
DB_PASS=NytexSecure2024!
SECRET_KEY=prod-secret-key-2024
DEBUG=false
SQUARE_ENVIRONMENT=production
SQUARE_ACCESS_TOKEN=your_square_token_here
```

---

## 📊 Monitoring Your Applications

### **Health Checks**
```bash
# Quick health check - both should return HTML
curl -s http://localhost:8000 | head -5          # Local
curl -s https://nytex-dashboard-932676587025.us-central1.run.app | head -5  # Cloud
```

### **Performance Monitoring**
- **Cloud Console**: https://console.cloud.google.com/run
- **Logs**: Available in Google Cloud Console or via gcloud CLI
- **Metrics**: CPU, Memory, Request count in Cloud Console

---

## 🎯 Quick Test Deployment

Want to test the entire workflow? Here's a safe test:

1. **Make a small change** (like updating a comment)
2. **Test locally**: `./start-local.sh`
3. **Deploy**: `./deploy.sh`
4. **Sync data**: `python scripts/sync_inventory_only.py`
5. **Verify**: Check both URLs work

This ensures your deployment pipeline is working correctly!

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