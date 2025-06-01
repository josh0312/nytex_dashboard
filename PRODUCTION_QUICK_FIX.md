# 🚨 Production Database Issues - Quick Fix Guide

## Immediate Check
```bash
curl -s https://nytex-dashboard-932676587025.us-central1.run.app/admin/status | python3 -m json.tool
```

**Expected**: `"database": "connected"`, `"tables_exist": true`, `"locations": [...]`

---

## Common Issues & Quick Fixes

### 1. **"Connect call failed" Error**

**Check Cloud SQL Connection Name:**
```bash
gcloud sql instances describe nytex-main-db --format="value(connectionName)"
# Should be: nytex-business-systems:us-central1:nytex-main-db
```

**Fix deployment if wrong:**
```bash
# Edit deploy.sh - use correct connection name (no -f suffix)
./deploy.sh
```

### 2. **Wrong Database URI Format**

**Check current secret:**
```bash
gcloud secrets versions access latest --secret="database-uri"
```

**Should be:**
```
postgresql+asyncpg://nytex_user:NytexSecure2024!@/square_data_sync?host=/cloudsql/nytex-business-systems:us-central1:nytex-main-db
```

**Fix if wrong:**
```bash
python scripts/secrets_manager.py pull
# Edit .env.local file - fix SQLALCHEMY_DATABASE_URI
python scripts/secrets_manager.py push
./deploy.sh
```

### 3. **Config Error in app/config.py**

**Look for:** `TypeError: 'classmethod' object is not callable`

**Fix:** Remove static `SQLALCHEMY_DATABASE_URI` attribute, use method only.

---

## Emergency Commands

```bash
# Quick redeploy
./deploy.sh

# Check logs for errors  
gcloud run services logs read nytex-dashboard --region us-central1 --limit=20

# Test database directly
gcloud sql connect nytex-main-db --user=nytex_user --database=square_data_sync

# Rollback to previous revision
gcloud run revisions list --service=nytex-dashboard --region=us-central1
gcloud run services update-traffic nytex-dashboard --region=us-central1 --to-revisions=REVISION_NAME=100
```

---

## 📖 Complete Documentation

See **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** for detailed explanations and solutions. 