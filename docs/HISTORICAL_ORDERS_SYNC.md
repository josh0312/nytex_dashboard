# 📅 Historical Orders Sync Documentation

## Overview

The Historical Orders Sync is a comprehensive data synchronization system that imports **ALL** historical order data from Square API into the production database. This system was specifically developed to support the **Annual Sales Comparison** feature and other historical reporting capabilities.

**Date Range**: January 1, 2018 → Present  
**Typical Volume**: 30,000+ orders spanning 7+ years  
**Purpose**: Enable year-over-year sales analysis and historical reporting

---

## 🎯 Why Historical Orders Sync?

### **Problem Solved**
- **Annual Sales Comparison was blank** in production
- Production database only had recent orders (last few months)
- Reports requiring historical data were incomplete
- Year-over-year analysis was impossible

### **Solution Delivered**
- Complete order history from 2018-present
- Chunked processing to handle large datasets
- Rate-limited API calls to respect Square limits
- Real-time progress tracking
- Robust error handling and recovery

---

## 🚀 How to Use

### **Web Interface (Recommended)**

1. **Navigate to Admin Interface**
   ```
   https://your-app-url/admin/sync
   ```

2. **Locate Historical Orders Sync Section**
   - Look for the red section with "📅 Historical Orders Sync"
   - Shows estimated 30,000+ orders and 2-4 hour duration

3. **Prerequisites Check**
   - Ensure database migration is complete (if migration section is visible)
   - Verify Square API connectivity is working
   - Confirm you have 2-4 hours for completion

4. **Start the Sync**
   - Click **"📅 Start Historical Orders Sync"**
   - Confirm the lengthy operation warning
   - Monitor real-time progress updates

### **API Endpoint (Advanced)**
```bash
# Start historical sync
curl -X POST https://your-app-url/admin/historical-orders-sync

# Check sync status
curl https://your-app-url/admin/historical-orders-sync-status

# Sample status response:
{
    "is_running": true,
    "total_chunks": 91,
    "completed_chunks": 45,
    "current_chunk_info": "Chunk 46/91: processed 15,230 orders",
    "total_orders_synced": 15230,
    "progress_percentage": 49.5,
    "estimated_remaining_seconds": 3600,
    "errors": []
}
```

---

## ⚙️ Technical Architecture

### **Chunked Processing Strategy**

**Why Chunked?**
- Square API has rate limits (100 requests/minute)
- Large datasets require pagination
- Memory management for 30,000+ orders
- Error isolation and recovery

**Chunk Configuration:**
```python
chunk_size_days = 30      # Process 30 days at a time
batch_size = 100          # Insert 100 orders per database batch
max_requests_per_minute = 100  # Square API rate limit
request_delay = 0.6       # 600ms delay between requests
```

**Date Range Calculation:**
```
Start: January 1, 2018
End: Current date
Chunks: ~84 chunks (30-day periods)
Example: 
  - Chunk 1: 2018-01-01 to 2018-01-31
  - Chunk 2: 2018-02-01 to 2018-03-02
  - ...
  - Chunk 84: 2024-12-01 to 2024-12-31
```

### **Database Schema**

**Primary Tables Updated:**
1. **`orders`** - Main order records
2. **`order_line_items`** - Individual items within orders
3. **`sync_state`** - Progress tracking

**Order Table Structure:**
```sql
CREATE TABLE orders (
    id VARCHAR PRIMARY KEY,                    -- Square order ID
    location_id VARCHAR,                       -- Store location
    created_at TIMESTAMP,                      -- Order creation time
    updated_at TIMESTAMP,                      -- Last modification
    closed_at TIMESTAMP,                       -- Order completion time
    state VARCHAR,                             -- COMPLETED, OPEN, CANCELED
    version BIGINT,                            -- Square version number
    total_money JSON,                          -- Total amount
    total_tax_money JSON,                      -- Tax amount
    total_discount_money JSON,                 -- Discount amount
    net_amounts JSON,                          -- Net calculations
    source JSON,                               -- Order source info
    return_amounts JSON,                       -- Return/refund data
    order_metadata JSON                        -- Additional Square data
);
```

**Order Line Items Table Structure:**
```sql
CREATE TABLE order_line_items (
    uid VARCHAR,                               -- Square line item UID
    order_id VARCHAR,                          -- Foreign key to orders.id
    catalog_object_id VARCHAR,                 -- Product catalog reference
    catalog_version BIGINT,                    -- Catalog version
    name VARCHAR,                              -- Product name
    quantity VARCHAR,                          -- Quantity ordered
    item_type VARCHAR,                         -- ITEM, CUSTOM_AMOUNT, etc.
    base_price_money JSON,                     -- Base price
    variation_total_price_money JSON,          -- Total for this variation
    gross_sales_money JSON,                    -- Gross sales amount
    total_discount_money JSON,                 -- Discounts applied
    total_tax_money JSON,                      -- Tax amount
    total_money JSON,                          -- Final total
    variation_name VARCHAR,                    -- Product variation name
    item_variation_metadata JSON,              -- Additional variation data
    note TEXT,                                 -- Special instructions
    applied_taxes JSON,                        -- Tax details
    applied_discounts JSON,                    -- Discount details
    modifiers JSON,                            -- Product modifiers
    pricing_blocklists JSON,                   -- Pricing restrictions
    PRIMARY KEY (order_id, uid)               -- Composite primary key
);
```

### **Square API Integration**

**API Endpoints Used:**
```
POST /v2/orders/search      # Primary order search
GET /v2/locations           # Location validation
```

**Search Query Structure:**
```json
{
    "location_ids": ["location1", "location2", ...],
    "query": {
        "filter": {
            "date_time_filter": {
                "created_at": {
                    "start_at": "2018-01-01T00:00:00Z",
                    "end_at": "2018-01-31T23:59:59Z"
                }
            },
            "state_filter": {
                "states": ["COMPLETED", "OPEN", "CANCELED"]
            }
        }
    },
    "limit": 500,
    "cursor": "optional_pagination_cursor"
}
```

---

## 📊 Progress Monitoring

### **Real-time Status Updates**

The system provides comprehensive progress tracking:

**Progress Metrics:**
- **Total Chunks**: Number of 30-day periods to process
- **Completed Chunks**: Chunks successfully processed
- **Progress Percentage**: Visual progress indicator
- **Orders Synced**: Running total of orders imported
- **Current Chunk Info**: Details about active processing
- **Estimated Time Remaining**: Dynamic completion estimate
- **Errors**: Any issues encountered

**Status Polling:**
```javascript
// Frontend polls every 3 seconds
setInterval(async () => {
    const response = await fetch('/admin/historical-orders-sync-status');
    const status = await response.json();
    
    if (status.is_running) {
        updateProgressBar(status.progress_percentage);
        updateDetails(status.current_chunk_info);
        updateOrderCount(status.total_orders_synced);
    }
}, 3000);
```

### **Log Monitoring**

**Production Logs:**
```bash
# Real-time log monitoring
gcloud run services logs tail nytex-dashboard --region us-central1

# Recent sync activity
gcloud run services logs read nytex-dashboard --region us-central1 --limit 50

# Filter for sync-specific logs
gcloud run services logs read nytex-dashboard --region us-central1 | grep "historical"
```

**Expected Log Patterns:**
```
2024-06-13 15:03:37 [INFO] 📅 Processing chunk 55/91: 2022-03-01 to 2022-03-31
2024-06-13 15:03:37 [INFO] 💾 Inserted batch of 100 orders (total: 9715)
2024-06-13 15:04:36 [INFO] ✅ Processed 156 orders for period
2024-06-13 15:07:43 [INFO] 💾 Inserted batch of 100 orders (total: 9915)
```

---

## 🛡️ Error Handling & Recovery

### **Built-in Safeguards**

**Graceful Error Handling:**
- **Chunk Isolation**: If one chunk fails, others continue
- **Transaction Rollback**: Database consistency maintained
- **Progress Preservation**: Completed chunks are saved
- **Detailed Error Logging**: Specific failure information

**Automatic Recovery Features:**
- **Idempotent Operations**: Can be run multiple times safely
- **Upsert Logic**: INSERT...ON CONFLICT prevents duplicates
- **Partial Completion**: Sync can resume from where it left off

### **Common Issues & Solutions**

**1. Timeout Errors**
```
Error: Request timeout after 60 seconds
Solution: Automatic retry with exponential backoff
```

**2. Rate Limit Exceeded**
```
Error: Rate limit exceeded (429)
Solution: Built-in delays (600ms between requests)
```

**3. Database Schema Mismatch**
```
Error: column "variation_total_price_money" does not exist
Solution: Run database migration first
```

**4. Memory Issues (Large Chunks)**
```
Error: Out of memory processing chunk
Solution: Batch processing (100 orders at a time)
```

### **Manual Recovery Steps**

If sync fails or stops unexpectedly:

1. **Check Current Status**
   ```bash
   curl https://your-app-url/admin/historical-orders-sync-status
   ```

2. **Review Error Logs**
   ```bash
   gcloud run services logs read nytex-dashboard --region us-central1 | grep "ERROR"
   ```

3. **Restart Sync**
   - The system will resume from the last completed chunk
   - Already-synced data will not be duplicated
   - Progress will continue from where it left off

---

## 🎯 Expected Results

### **Successful Completion Metrics**

**Typical Results (varies by business):**
```
✅ Total orders synced: 30,391
✅ Total line items: 159,535
✅ Date range: May 2018 - June 2025 (2,573 days)
✅ Processing time: 2-4 hours
✅ Success rate: 95%+ (some periods may have no orders)
✅ Chunks processed: 84/91 (some future chunks empty)
```

**Database Impact:**
```sql
-- Before sync
SELECT COUNT(*) FROM orders;          -- ~100 orders
SELECT COUNT(*) FROM order_line_items; -- ~500 items

-- After sync  
SELECT COUNT(*) FROM orders;          -- ~30,000 orders
SELECT COUNT(*) FROM order_line_items; -- ~160,000 items
```

### **Feature Enablement**

**Once sync completes, these features will work:**
- ✅ **Annual Sales Comparison** - Year-over-year revenue analysis
- ✅ **Historical Reports** - Multi-year sales trends
- ✅ **Customer Analysis** - Long-term customer behavior
- ✅ **Product Performance** - Historical product sales
- ✅ **Seasonal Analysis** - Multi-year seasonal patterns

---

## 🔒 Security & Performance

### **Security Considerations**

**Data Protection:**
- All API calls use secure HTTPS
- Square access tokens stored in Google Secret Manager
- Database connections use Cloud SQL with encryption
- No sensitive data logged in plaintext

**Access Control:**
- Admin-level authentication required
- Sync operations logged for audit trail
- Production environment isolation

### **Performance Optimization**

**API Efficiency:**
- Maximum batch size (500 orders per request)
- Optimized pagination handling
- Rate limiting to prevent API throttling
- Efficient JSON parsing and storage

**Database Performance:**
- Batch insertions (100 orders at a time)
- Proper indexing on order IDs and dates
- UPSERT operations prevent duplicate processing
- Connection pooling for efficiency

**Resource Management:**
- Memory-conscious chunk processing
- Cloud Run auto-scaling for demand
- Efficient async/await patterns
- Garbage collection optimization

---

## 📋 Maintenance & Best Practices

### **Regular Maintenance**

**Monthly Tasks:**
- Monitor sync performance and duration
- Review error logs for patterns
- Check database storage growth
- Validate data integrity with sample queries

**Quarterly Tasks:**
- Review sync configuration for optimization
- Update API rate limits if Square changes policies
- Backup database before major syncs
- Performance testing with latest data volumes

### **Best Practices**

**Before Running Sync:**
- ✅ Verify Square API connectivity
- ✅ Check database storage capacity
- ✅ Ensure migration is complete
- ✅ Plan for 2-4 hour completion time
- ✅ Monitor system resources

**During Sync:**
- ✅ Monitor progress via admin interface
- ✅ Watch logs for any error patterns
- ✅ Avoid other intensive operations
- ✅ Keep browser tab open for progress updates

**After Sync:**
- ✅ Verify expected order counts
- ✅ Test annual sales comparison feature
- ✅ Run sample historical reports
- ✅ Check database statistics
- ✅ Document any issues encountered

### **Troubleshooting Quick Reference**

| Issue | Quick Check | Solution |
|-------|-------------|----------|
| Progress not updating | Check status endpoint | Browser refresh or wait for polling |
| Schema errors | Run migration | Use admin migration tool |
| Low order count | Check date range | Verify start date = 2018-01-01 |
| API errors | Check token | Verify Square access token in secrets |
| Memory issues | Check batch size | Default 100 orders per batch is optimal |

---

**Last Updated**: June 2025  
**System Version**: Historical Orders Sync v2.0  
**Documentation Author**: Generated from production implementation 