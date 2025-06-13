# 🔧 NyTex Dashboard - Production Troubleshooting Guide

## 📋 Critical Production Issues & Solutions

This guide documents common production issues and their solutions, based on real troubleshooting experiences.

---

## 🚨 Database Connectivity Issues

### **Issue**: Production app shows "Connect call failed ('127.0.0.1', 5432)"

**Symptoms:**
- `/admin/status` endpoint returns `"database": "connected"` but `"tables_exist": false`
- Error: `[Errno 111] Connect call failed ('127.0.0.1', 5432)` or `Connection refused`
- Application starts but can't access database tables

**Root Causes & Solutions:**

#### 1. **Configuration Error in app/config.py**
**Problem**: `TypeError: 'classmethod' object is not callable`

```python
# ❌ WRONG - This causes a TypeError
class Config:
    @classmethod
    def get_database_url(cls):
        return get_database_url()
    
    SQLALCHEMY_DATABASE_URI = get_database_url()  # Error here!
```

**Solution**: Remove static attribute, use method everywhere:
```python
# ✅ CORRECT - Use method consistently
class Config:
    @classmethod
    def get_database_url(cls):
        return get_database_url()
    
    # Remove the static SQLALCHEMY_DATABASE_URI attribute
```

#### 2. **Wrong Cloud SQL Connection Name**
**Problem**: Using zone in connection name when instance connection name doesn't include it

```bash
# ❌ WRONG - Adding zone when instance doesn't use it
CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1-f:nytex-main-db

# ✅ CORRECT - Use actual instance connection name
CLOUD_SQL_CONNECTION_NAME=nytex-business-systems:us-central1:nytex-main-db
```

**How to verify correct connection name:**
```bash
gcloud sql instances describe nytex-main-db --format="value(connectionName)"
```

#### 3. **Incorrect Database URI Format**
**Problem**: Wrong socket path format for Cloud SQL

```bash
# ❌ WRONG - Old format that doesn't work
postgresql+asyncpg://user:pass@/cloudsql/connection/database

# ✅ CORRECT - Proper Cloud SQL socket format  
postgresql+asyncpg://user:pass@/database?host=/cloudsql/connection
```

#### 4. **Wrong Database Name**
**Problem**: Using development database name in production

```bash
# ❌ WRONG - Development database name
DB_NAME=nytex_dashboard

# ✅ CORRECT - Production database name
DB_NAME=square_data_sync
```

---

## 🔐 Secrets Management Issues

### **Issue**: Hardcoded secrets in deployment script

**Problem**: Deployment script hardcodes sensitive values instead of using Secret Manager

**Solution**: Use proper secrets-based deployment:

```bash
# ❌ WRONG - Hardcoded secrets
gcloud run deploy nytex-dashboard \
    --set-env-vars "SECRET_KEY=prod-secret-key-2024" \
    --set-env-vars "SQUARE_ACCESS_TOKEN=$SQUARE_TOKEN"

# ✅ CORRECT - Use Secret Manager
gcloud run deploy nytex-dashboard \
    --update-secrets "SECRET_KEY=secret-key:latest" \
    --update-secrets "SQUARE_ACCESS_TOKEN=square-access-token:latest"
```

**Manage secrets properly:**
```bash
# Pull current secrets to local file
python scripts/secrets_manager.py pull

# Edit .env.local file with correct values
# Push updated secrets back to Secret Manager
python scripts/secrets_manager.py push

# Deploy using secrets
./deploy.sh
```

---

## 🔍 Debugging Steps

### **1. Check Service Status**
```bash
# Basic connectivity test
curl -s https://nytex-dashboard-932676587025.us-central1.run.app/admin/status | python3 -m json.tool
```

**Expected Success Response:**
```json
{
    "database": "connected",
    "square_config": "configured", 
    "locations": [...],  // Array of locations
    "tables_exist": true,
    "location_count": 9
}
```

### **2. Verify Cloud SQL Instance**
```bash
# Check instance status
gcloud sql instances describe nytex-main-db

# Get correct connection name
gcloud sql instances describe nytex-main-db --format="value(connectionName)"

# Test direct database connection
gcloud sql connect nytex-main-db --user=nytex_user --database=square_data_sync
```

### **3. Check Secrets Configuration**
```bash
# List all secrets
python scripts/secrets_manager.py list

# Verify specific secret
gcloud secrets versions access latest --secret="database-uri"

# Check Cloud Run environment
gcloud run services describe nytex-dashboard --region us-central1 --format="export" | grep -A10 env:
```

### **4. Monitor Deployment Logs**
```bash
# Watch deployment logs
gcloud run services logs tail nytex-dashboard --region us-central1

# Check recent errors
gcloud run services logs read nytex-dashboard --region us-central1 --limit=50
```

---

## ✅ Verification Checklist

After fixing database issues, verify:

- [ ] `/admin/status` returns `"database": "connected"`
- [ ] `/admin/status` returns `"tables_exist": true` 
- [ ] `/admin/status` shows populated `"locations"` array
- [ ] No connection errors in Cloud Run logs
- [ ] All secrets properly configured in Secret Manager
- [ ] Deployment script uses `--update-secrets` not `--set-env-vars`

---

## 🎯 Prevention Tips

### **1. Always Use Secrets Manager**
- Never hardcode credentials in deployment scripts
- Use `scripts/secrets_manager.py` for all secret operations
- Verify secrets before deployment: `python scripts/secrets_manager.py list`

### **2. Verify Connection Names**
- Always check actual Cloud SQL connection names before deployment
- Use `gcloud sql instances describe <instance> --format="value(connectionName)"`
- Don't assume zone suffixes in connection names

### **3. Test Database Format**
- Use correct Cloud SQL socket format: `?host=/cloudsql/connection`
- Verify database name matches production: `square_data_sync`
- Test connection string format locally when possible

### **4. Monitor After Deployment**
- Always test `/admin/status` after deployment
- Check Cloud Run logs for errors
- Verify table access with actual queries

---

## 📞 Emergency Recovery

If production is completely down:

1. **Quick Status Check:**
   ```bash
   curl -s https://nytex-dashboard-932676587025.us-central1.run.app/admin/status
   ```

2. **Check Latest Deployment:**
   ```bash
   gcloud run services describe nytex-dashboard --region us-central1
   ```

3. **Rollback if Needed:**
   ```bash
   # Find previous working revision
   gcloud run revisions list --service=nytex-dashboard --region=us-central1
   
   # Rollback to previous revision
   gcloud run services update-traffic nytex-dashboard --region=us-central1 \
     --to-revisions=nytex-dashboard-PREVIOUS_REVISION=100
   ```

4. **Check Database Independently:**
   ```bash
   gcloud sql connect nytex-main-db --user=nytex_user --database=square_data_sync
   ```

---

## 📚 Related Documentation

- [Secrets Management Guide](SECRETS_GUIDE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Cloud Configuration](CLOUD_CONFIG.md)

---

## 🗃️ Database Schema & Migration Issues

### **Issue**: Historical Orders Sync Fails - Missing Columns Error

**Symptoms:**
- Historical orders sync starts but fails with `UndefinedColumnError`
- Error: `column "variation_total_price_money" of relation "order_line_items" does not exist`
- Error: `column "item_variation_metadata" of relation "order_line_items" does not exist`
- Sync gets 60-90% complete then crashes

**Root Cause:**
Production database schema missing columns that were added during development. The `order_line_items` table was missing two JSON columns required for full Square API compatibility:
- `variation_total_price_money` (JSON)
- `item_variation_metadata` (JSON)

**Solution:**

#### 1. **Run Database Migration via Admin Interface**
1. Go to `/admin/sync` in production
2. Look for **"Database Migration"** section 
3. Click **"🔧 Run Database Migration"** button
4. Confirm the migration when prompted
5. Wait for success confirmation

#### 2. **Manual Migration (if needed)**
```bash
# Connect to production database
curl -X POST https://your-app-url/admin/migrate-order-line-items

# Expected response:
# {"success":true,"message":"Migration completed successfully","added_columns":["variation_total_price_money","item_variation_metadata"]}
```

#### 3. **Verify Migration Success**
```sql
-- Check if columns exist
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'order_line_items' 
AND column_name IN ('variation_total_price_money', 'item_variation_metadata');
```

### **Issue**: Historical Orders Sync Progress Not Updating

**Symptoms:**
- Sync starts successfully but progress bar doesn't update
- Browser appears to "hang" waiting for response
- Admin interface becomes unresponsive during sync

**Root Cause:**
Browser waiting for entire sync response (2-4 hours) instead of using background processing with status polling.

**Solution:**
The system now uses background processing with real-time status updates:

1. **Sync runs in background** - API returns immediately
2. **Progress polling** - JavaScript polls `/admin/historical-orders-sync-status` every 3 seconds
3. **Real-time updates** - Progress bar and status update automatically

**Monitoring Commands:**
```bash
# Check current sync status
curl https://your-app-url/admin/historical-orders-sync-status

# Monitor production logs
gcloud run services logs read nytex-dashboard --region us-central1 --limit 20

# Watch for completion
watch "curl -s https://your-app-url/admin/historical-orders-sync-status | python3 -m json.tool"
```

### **Issue**: ON CONFLICT Constraint Errors in Order Line Items

**Symptoms:**
- `UNIQUE constraint failed` or `duplicate key value` errors
- Order line items failing to insert/update
- Inconsistent primary key behavior

**Root Cause:**
Incorrect primary key configuration. The `order_line_items` table primary key is `(order_id, uid)` not just `(uid)`.

**Solution:**
Ensure all upsert queries use the correct ON CONFLICT clause:

```sql
-- ✅ CORRECT - Use composite primary key
ON CONFLICT (order_id, uid) DO UPDATE SET...

-- ❌ WRONG - Missing order_id in conflict resolution  
ON CONFLICT (uid) DO UPDATE SET...
```

**Verification:**
```sql
-- Check table constraints
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'order_line_items';

-- View primary key definition
\d order_line_items
```

---

## 📊 Historical Orders Sync Troubleshooting

### **Issue**: Sync Incomplete - Only Partial Data

**Symptoms:**
- Sync reports "completed" but with very few orders
- Expected 30,000+ orders but only got 39-100
- Annual sales comparison still showing blank data

**Root Causes & Solutions:**

#### 1. **Date Range Too Narrow**
```python
# ❌ WRONG - Too recent start date
start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

# ✅ CORRECT - Include full historical range
start_date = datetime(2018, 1, 1, tzinfo=timezone.utc)
```

#### 2. **Location Filtering Issues**
```python
# ❌ WRONG - Missing locations or wrong IDs
location_ids = ["ACTIVE_ONLY"]

# ✅ CORRECT - Include all relevant locations
location_ids = await get_active_locations()  # Gets all active Square locations
```

#### 3. **API Rate Limiting**
**Symptoms:** Sync stalls or gets fewer results than expected

**Solution:** Proper rate limiting implemented:
```python
# Current configuration (safe for production)
max_requests_per_minute = 100
request_delay = 0.6  # 600ms between requests
chunk_size_days = 30  # Process 30 days at a time
```

#### 4. **Chunk Processing Errors**
Monitor logs for chunk-specific failures:
```bash
# Look for chunk errors
gcloud run services logs read nytex-dashboard --region us-central1 | grep "Error processing chunk"

# Example error patterns:
# "Error processing chunk 55: connection timeout"
# "Error processing chunk 91: schema error"
```

### **Expected Results for Complete Sync**
- **Total Orders**: 30,000+ (varies by business history)
- **Date Range**: January 2018 - Present
- **Duration**: 2-4 hours for complete historical sync
- **Chunks**: ~84 chunks (30-day periods from 2018-2025)
- **Success Rate**: 95%+ (some chunks may have no orders)

--- 