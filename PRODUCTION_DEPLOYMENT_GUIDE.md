# NyTex Dashboard - Production Deployment Guide

## 🚀 Sync System Production Deployment

### Prerequisites
- [ ] All secrets configured in Google Secret Manager  
- [ ] Database schema updated (Alembic migrations applied)
- [ ] Gmail app password configured for notifications
- [ ] Development sync tested and working

### Deployment Steps

#### 1. Deploy Application
```bash
# Deploy the main application
./deploy.sh
```

#### 2. Set Up Production Sync Schedule

**Option A: Cloud Scheduler (Recommended)**
```bash
# Create Cloud Scheduler job for daily sync
gcloud scheduler jobs create http nytex-daily-sync \
    --schedule="0 2 * * *" \
    --uri="https://your-app-url.run.app/admin/sync/all" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --body='{"force": true}' \
    --time-zone="UTC"
```

**Option B: Cloud Run Jobs (Alternative)**
```bash
# Deploy sync as a separate Cloud Run job
gcloud run jobs create nytex-sync \
    --image=gcr.io/nytex-business-systems/nytex-dashboard \
    --region=us-central1 \
    --set-secrets="[all secrets from cloudbuild.yaml]" \
    --memory=1Gi \
    --cpu=1 \
    --max-retries=3 \
    --task-count=1 \
    --task-timeout=3600

# Schedule with Cloud Scheduler
gcloud scheduler jobs create http nytex-sync-trigger \
    --schedule="0 2 * * *" \
    --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/nytex-business-systems/jobs/nytex-sync:run" \
    --http-method=POST \
    --oauth-service-account-email="your-service-account@nytex-business-systems.iam.gserviceaccount.com" \
    --time-zone="UTC"
```

#### 3. Verify Production Setup

1. **Check sync endpoint:**
   ```bash
   curl -X POST https://your-app-url.run.app/admin/sync/status
   ```

2. **Test manual sync:**
   ```bash
   curl -X POST https://your-app-url.run.app/admin/sync/catalog_items
   ```

3. **Monitor logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" --limit=50
   ```

### Sync Schedule Summary

| Environment | Time (Local) | Time (UTC) | Separation |
|-------------|-------------|------------|------------|
| **Production** | 9 PM CT (prev day) | **2 AM UTC** | - |
| **Development** | 2 AM CT | **7 AM UTC** | 5 hours later |

### Monitoring & Alerts

#### Email Notifications
- ✅ Configured automatically via notification service
- Recipients: Set in `SYNC_NOTIFICATION_RECIPIENTS` secret
- Alerts: Sync failures and daily success reports

#### Manual Monitoring
```bash
# Check sync status
curl https://your-app-url.run.app/admin/sync/status

# View recent sync history  
curl https://your-app-url.run.app/admin/sync/history

# Force immediate sync (if needed)
curl -X POST https://your-app-url.run.app/admin/sync/all
```

### Troubleshooting

#### Common Issues

1. **Sync Failures**
   - Check Cloud Logging for detailed error messages
   - Verify Square API credentials are current
   - Ensure database connectivity

2. **Missing Email Notifications**
   - Verify `SMTP_*` secrets in Secret Manager
   - Check Gmail app password hasn't expired
   - Review notification service logs

3. **Database Connection Issues**
   - Verify Cloud SQL proxy configuration
   - Check database instance is running
   - Validate connection string format

#### Emergency Manual Sync
If automated sync fails, run manual sync:
```bash
# Connect to production container
gcloud run services proxy nytex-dashboard --port=8080

# Run sync orchestrator directly
python scripts/sync_orchestrator.py --force
```

### Post-Deployment Checklist

- [ ] Automated sync running daily at 2 AM UTC
- [ ] Email notifications working
- [ ] Development sync running at 7 AM UTC (2 AM Central)
- [ ] No overlap between dev/prod sync times
- [ ] Manual sync endpoints accessible via admin panel
- [ ] Monitoring and logging configured
- [ ] Emergency procedures documented

### Support

For sync system issues:
1. Check logs in Google Cloud Logging
2. Review email notifications for error details
3. Use admin panel for manual sync testing
4. Refer to `SYNC_SYSTEM_IMPLEMENTATION.md` for technical details 