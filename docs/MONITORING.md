# 🔍 NyTex Dashboard - Production Monitoring Guide

## 🎯 Overview

The NyTex Dashboard includes a comprehensive monitoring system that proactively detects issues, automatically fixes common problems, and provides detailed health reporting for production deployments.

---

## 🚀 Quick Start

### **Instant Health Check**
```bash
# Single health check with auto-fix
python scripts/deployment_monitor.py --auto-fix
```

### **Start Continuous Monitoring**
```bash
# Background monitoring every 30 minutes
./scripts/start_monitoring.sh

# Check monitoring status
./scripts/check_monitoring.sh

# Stop monitoring
./scripts/stop_monitoring.sh
```

### **Setup Automated Monitoring**
```bash
# Setup cron jobs for 24/7 monitoring
./scripts/setup_monitoring.sh
```

---

## 🔍 What Gets Monitored

### **1. IAM Permissions** 🔐
- **What**: GitHub Actions service account permissions for Cloud Run deployments
- **Why**: Prevents "Permission denied" deployment failures
- **Auto-Fix**: ✅ Automatically restores missing permissions

### **2. Cloud Run Service** ☁️
- **What**: Service status, revision health, and traffic allocation
- **Why**: Ensures the production service is running and accessible
- **Auto-Fix**: ⚠️ Reports issues (manual intervention may be needed)

### **3. Application Health** 🌐
- **What**: HTTP response codes and application responsiveness
- **Why**: Confirms the application is serving requests correctly
- **Auto-Fix**: ⚠️ Reports issues (application-level debugging needed)

### **4. Recent Deployments** 📊
- **What**: GitHub Actions workflow success/failure rates
- **Why**: Identifies patterns in deployment issues
- **Auto-Fix**: ⚠️ Reports trends (investigation needed)

### **5. Database Connectivity** 🗄️
- **What**: Database connection and query capability
- **Why**: Ensures data access is working correctly
- **Auto-Fix**: ⚠️ Reports issues (database troubleshooting needed)

---

## 📊 Monitoring Commands Reference

### **Manual Monitoring**
```bash
# Basic health check
python scripts/deployment_monitor.py

# Health check with automatic fixes
python scripts/deployment_monitor.py --auto-fix

# Continuous monitoring (custom interval)
python scripts/deployment_monitor.py --continuous 15  # Every 15 minutes
```

### **Background Monitoring**
```bash
# Start background monitoring (30-minute intervals)
./scripts/start_monitoring.sh

# Check if monitoring is running
./scripts/check_monitoring.sh

# Stop background monitoring
./scripts/stop_monitoring.sh
```

### **Automated Scheduling**
```bash
# Setup cron jobs for automated monitoring
./scripts/setup_monitoring.sh

# Remove monitoring cron jobs
crontab -l | grep -v "deployment_monitor" | crontab -
```

---

## 📅 Monitoring Schedules

### **Recommended Cron Schedule**
When you run `./scripts/setup_monitoring.sh`, it sets up:

- **Business Hours** (8 AM - 8 PM, Mon-Fri): Every 15 minutes
- **Off Hours** (Nights, Early Morning): Every hour
- **Weekends**: Every hour
- **Daily Comprehensive Check**: 6 AM with detailed logging

### **Custom Scheduling**
```bash
# Edit crontab manually for custom schedules
crontab -e

# Example: Check every 5 minutes during peak hours
*/5 9-17 * * 1-5 cd /path/to/project && python3 scripts/deployment_monitor.py --auto-fix
```

---

## 📋 Health Report Examples

### **Healthy System Report**
```
============================================================
NyTex Dashboard - Deployment Health Report
============================================================
Timestamp: 2025-06-17 17:12:09
Production URL: https://nytex-dashboard-nndn66l4ua-uc.a.run.app

✅ ALL SYSTEMS HEALTHY

Monitoring completed successfully.
============================================================
```

### **Issues Detected Report**
```
============================================================
NyTex Dashboard - Deployment Health Report
============================================================
Timestamp: 2025-06-17 17:12:09
Production URL: https://nytex-dashboard-nndn66l4ua-uc.a.run.app

🚨 CRITICAL ISSUES:
  ❌ GitHub Actions service account missing serviceAccountUser role

⚠️  WARNINGS:
  ⚠️  Recent deployment failures: #6 (2025-06-17T21:55:27Z)

Monitoring completed successfully.
============================================================
```

---

## 🔧 Auto-Fix Capabilities

### **What Gets Auto-Fixed**
When you use `--auto-fix` flag, the system can automatically resolve:

1. **IAM Permission Issues**
   - Missing `serviceAccountUser` role
   - Incorrect service account bindings
   - GitHub Actions deployment permissions

### **What Requires Manual Intervention**
- Application code errors (500 errors, crashes)
- Database connectivity issues
- Cloud Run service configuration problems
- Network or infrastructure issues

---

## 📁 Log Files & Storage

### **Log Locations**
```bash
# All logs stored in project logs directory
ls -la logs/

# Monitoring logs
logs/monitoring.log              # Regular monitoring output
logs/continuous_monitoring.log   # Background monitoring output
logs/daily_health_YYYYMMDD.log  # Daily comprehensive reports
logs/health_report_YYYYMMDD_HHMMSS.txt  # Individual health reports
```

### **Log Management**
```bash
# View recent monitoring activity
tail -f logs/monitoring.log

# View today's comprehensive report
cat logs/daily_health_$(date +%Y%m%d).log

# Clean old logs (older than 30 days)
find logs/ -name "*.log" -mtime +30 -delete
```

---

## 🚨 Alert Integration (Future Enhancement)

### **Planned Integrations**
- **Email Alerts**: Critical issue notifications
- **Slack/Discord Webhooks**: Real-time team notifications  
- **SMS Alerts**: Emergency notifications for production outages
- **PagerDuty Integration**: Escalation for unresolved issues

### **Current Notification Methods**
- **Log Files**: All activity logged locally
- **Cron Job Output**: Email notifications if cron jobs fail
- **Exit Codes**: Scripts return proper exit codes for monitoring systems

---

## 🔍 Troubleshooting Monitoring

### **Monitoring Script Won't Run**
```bash
# Check script permissions
ls -la scripts/deployment_monitor.py

# Make executable if needed
chmod +x scripts/deployment_monitor.py

# Test script manually
python scripts/deployment_monitor.py
```

### **Cron Jobs Not Working**
```bash
# Check if cron service is running
pgrep cron

# View cron logs
tail -f /var/log/cron.log  # Linux
tail -f /var/log/system.log | grep cron  # macOS

# Test cron job manually
cd /path/to/project && python3 scripts/deployment_monitor.py --auto-fix
```

### **Auto-Fix Not Working**
```bash
# Check Google Cloud authentication
gcloud auth list

# Verify project is set correctly
gcloud config get project

# Test IAM permissions manually
gcloud iam service-accounts get-iam-policy 932676587025-compute@developer.gserviceaccount.com
```

---

## 📈 Monitoring Best Practices

### **Development Workflow**
1. **Before Deployment**: Run `python scripts/deployment_monitor.py --auto-fix`
2. **After Deployment**: Monitor logs for 10-15 minutes
3. **Regular Checks**: Setup automated monitoring with cron jobs
4. **Issue Response**: Use auto-fix first, then investigate manually

### **Production Maintenance**
- **Daily**: Review comprehensive health reports
- **Weekly**: Check monitoring logs for trends
- **Monthly**: Clean old logs and review monitoring effectiveness
- **Quarterly**: Review and update monitoring schedules

### **Emergency Response**
1. **Run immediate health check**: `python scripts/deployment_monitor.py --auto-fix`
2. **Check recent logs**: `tail -50 logs/monitoring.log`
3. **Verify application**: `curl -I https://nytex-dashboard-nndn66l4ua-uc.a.run.app`
4. **Check Cloud Run status**: `gcloud run services describe nytex-dashboard --region=us-central1`

---

## 🎯 Monitoring Metrics & KPIs

### **System Health Metrics**
- **Uptime**: Application availability percentage
- **Response Time**: Average HTTP response time
- **Error Rate**: Percentage of failed health checks
- **Auto-Fix Success Rate**: Percentage of issues resolved automatically

### **Deployment Metrics**
- **Deployment Success Rate**: Percentage of successful deployments
- **Time to Deploy**: Average deployment duration
- **Rollback Frequency**: Number of rollbacks per month
- **IAM Issue Frequency**: How often permission issues occur

---

**The monitoring system provides enterprise-grade observability with intelligent automation to keep your NyTex Dashboard running smoothly!** 🚀 