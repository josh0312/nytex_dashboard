# Incremental Sync Strategy

## 🎯 **Objective**
Replace the current "full clear + rebuild" daily sync with an intelligent incremental sync that:
1. **Preserves data integrity** 
2. **Detects changes** efficiently
3. **Syncs only what changed**
4. **Covers ALL tables** (not just 5 core ones)
5. **Maintains auditability**

---

## 📊 **Current State Analysis**

### **Production Tables (Missing 14 tables):**
```
locations: 9
catalog_categories: 23  
catalog_items: 865
catalog_variations: 986
catalog_inventory: 6,960
```

### **Local Tables (Complete dataset):**
```
alembic_version: 1
catalog_categories: 25 (+2 vs prod)
catalog_inventory: 9,018 (+2,058 vs prod) 
catalog_items: 867 (+2 vs prod)
catalog_location_availability: 7,801 (MISSING in prod)
catalog_variations: 1,002 (+16 vs prod)
catalog_vendor_info: 989 (MISSING in prod)
inventory_counts: 4,932 (MISSING in prod)
locations: 9 (MATCH)
operating_seasons: 42 (MISSING in prod)
order_fulfillments: 0 (MISSING in prod)
order_line_items: 159,131 (MISSING in prod)
order_refunds: 0 (MISSING in prod)
order_returns: 0 (MISSING in prod)
orders: 30,390 (MISSING in prod)
payments: 49 (MISSING in prod)
square_item_library_export: 986 (MISSING in prod)
square_sales: 0 (MISSING in prod)
tenders: 2,493 (MISSING in prod)
transactions: 0 (MISSING in prod)
vendors: 11 (MISSING in prod)
```

## 🔧 **Revised Architecture (API-Based)**

Since direct database connections to production are restricted, we'll use a **hybrid approach**:

### **1. Local Development & Testing**
- ✅ Full database access for local testing
- ✅ Complete incremental sync development locally
- ✅ Data integrity validation locally

### **2. Production Interaction via API**
- 🌐 Use existing `/admin/*` endpoints
- 🌐 Create new `/admin/incremental-sync` endpoints
- 🌐 Batch data transfer via web API
- 🌐 Status monitoring via `/admin/status`

---

## 🏗️ **Sync Architecture Design**

### **1. Sync Categories & Data Sources**

#### **A. Square API Sync (Primary)**
**Real-time data from Square:**
- ✅ `locations` - Square Locations API
- ✅ `catalog_categories` - Square Catalog API  
- ✅ `catalog_items` - Square Catalog API
- ✅ `catalog_variations` - Square Catalog API
- ✅ `catalog_inventory` - Square Inventory API
- 🆕 `catalog_location_availability` - Square Catalog API
- 🆕 `catalog_vendor_info` - Square Vendor API
- 🆕 `vendors` - Square Vendor API
- 🆕 `orders` - Square Orders API
- 🆕 `order_line_items` - Square Orders API
- 🆕 `order_fulfillments` - Square Orders API  
- 🆕 `order_refunds` - Square Orders API
- 🆕 `order_returns` - Square Orders API
- 🆕 `payments` - Square Payments API
- 🆕 `tenders` - Square Tenders API
- 🆕 `transactions` - Square Transactions API

#### **B. Internal/Static Data**
**Dashboard-managed data:**
- ✅ `operating_seasons` - Internal business logic
- ✅ `inventory_counts` - Historical tracking
- ✅ `square_sales` - Processed sales data

#### **C. Export/Analytics Data (Full Rebuild)**
**Always clear & rebuild:**
- ✅ `square_item_library_export` - Daily fresh export

### **2. Change Detection Strategy**

#### **A. Version-Based Detection**
```sql
-- Add sync tracking columns to existing tables
ALTER TABLE locations ADD COLUMN square_version BIGINT;
ALTER TABLE catalog_items ADD COLUMN square_version BIGINT;
ALTER TABLE catalog_categories ADD COLUMN square_version BIGINT;
ALTER TABLE catalog_variations ADD COLUMN square_version BIGINT;
```

#### **B. Timestamp-Based Detection**
```sql
-- Use Square's updated_at vs our last_synced_at
SELECT * FROM square_api 
WHERE updated_at > last_sync_timestamp
```

#### **C. Sync State Tracking**
```sql
CREATE TABLE sync_state (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) UNIQUE,
    last_sync_timestamp TIMESTAMP,
    last_sync_version BIGINT,
    records_synced INTEGER,
    sync_duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 **Revised Implementation Plan**

### **Step 1: Local Development (Complete)**
```bash
# 1. Develop incremental sync locally
./scripts/incremental_sync.py --target=local --mode=develop

# 2. Test change detection locally
./scripts/test_incremental_sync.py --simulate-changes

# 3. Validate data integrity locally  
./scripts/verify_sync_integrity.py --target=local
```

### **Step 2: Create Production API Endpoints**
**New admin endpoints for production sync:**

```python
@router.post("/admin/foundation-sync")
async def foundation_sync_api():
    """API endpoint to establish foundation data"""

@router.post("/admin/incremental-sync") 
async def incremental_sync_api():
    """API endpoint for incremental sync operations"""

@router.get("/admin/sync-status")
async def get_sync_status():
    """Get detailed sync status and metrics"""

@router.post("/admin/table-migration")
async def migrate_missing_tables():
    """Migrate missing table schemas to production"""
```

### **Step 3: Production Foundation Setup**
```bash
# 1. Deploy new API endpoints
./deploy.sh

# 2. Migrate missing table schemas
curl -X POST "https://production-url/admin/table-migration"

# 3. Run foundation sync via API
curl -X POST "https://production-url/admin/foundation-sync"

# 4. Verify foundation setup
curl "https://production-url/admin/sync-status"
```

### **Step 4: Switch to Incremental**
```bash
# 1. Update daily scheduler to use incremental sync
gcloud scheduler jobs update daily-sync-job --uri="...admin/incremental-sync"

# 2. Monitor incremental sync performance
./scripts/monitor_production_sync.py

# 3. Validate business reports still work
./scripts/validate_reports.py --target=production
```

---

## 📋 **Implementation Priority**

### **Phase 1: Foundation (This Week)**
1. ✅ **Create local incremental sync logic**
2. ✅ **Test change detection locally**  
3. ✅ **Develop API endpoints for production**
4. ✅ **Deploy foundation sync API**

### **Phase 2: Production Migration (Next Week)**
1. ✅ **Create missing tables in production**
2. ✅ **Run foundation sync to populate all data**
3. ✅ **Switch scheduler to incremental mode**
4. ✅ **Monitor and validate**

---

## 🛡️ **Safety & Validation**

### **A. Data Integrity Checks**
```python
async def validate_sync_integrity():
    """Validate data consistency after sync"""
    # Check foreign key constraints
    # Verify record counts match expectations
    # Validate business logic constraints
    # Compare sample data with Square API
```

### **B. Rollback Strategy**
```python
async def rollback_sync(sync_id: str):
    """Rollback changes from a specific sync"""
    # Restore from backup
    # Reset sync_state
    # Log rollback reason
```

### **C. Monitoring & Alerting**
```python
async def monitor_sync_health():
    """Monitor sync performance and data quality"""
    # Track sync duration trends
    # Alert on large data discrepancies  
    # Monitor API error rates
    # Validate data freshness
```

---

## 🚀 **Expected Benefits**

### **Performance Improvements:**
- ⚡ **Faster syncs**: 2-4 minutes → 30-60 seconds
- 🛡️ **Data safety**: No more daily full clears
- 📊 **Complete coverage**: All 21 tables synced
- 🔍 **Better monitoring**: Detailed sync tracking

### **Operational Benefits:**
- 🕐 **Reduced downtime** during syncs
- 📈 **Historical data preservation**
- 🚨 **Better error detection** and recovery
- 📋 **Audit trail** for all changes

---

## 🧪 **Testing Strategy**

### **Local Testing Phase:**
1. ✅ **Set up test data** in local database
2. ✅ **Simulate Square API changes**
3. ✅ **Test incremental detection**
4. ✅ **Validate change application**
5. ✅ **Test error scenarios**

### **Production Validation:**
1. ✅ **Deploy new API endpoints**
2. ✅ **Run foundation sync** via API
3. ✅ **Compare data integrity** with expectations
4. ✅ **Monitor first week** of incremental syncs
5. ✅ **Validate business reports** still work

---

## 📝 **Next Steps**

1. **✅ Create incremental sync service locally**
2. **✅ Add API endpoints for production sync**
3. **✅ Test thoroughly with local data**
4. **✅ Deploy foundation sync API to production**
5. **✅ Run foundation sync to populate all tables**
6. **✅ Switch to incremental daily sync**
7. **✅ Monitor and optimize**

---

This revised strategy works within the constraints of production access while still achieving our goals of comprehensive, incremental syncing. 