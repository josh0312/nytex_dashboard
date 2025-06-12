# Square Catalog Export System

## Overview

The Square Catalog Export System is a comprehensive solution for exporting Square catalog data in a format that matches Square's official Item Library Export. This system extracts data from the Square API and creates a complete 76-column export that can be used for inventory management, data analysis, and integration with other systems.

## Architecture

### Components

1. **External Microservice** (`square_catalog_export/`)
   - Standalone Flask application
   - Handles Square API communication
   - Processes and transforms data
   - Stores export data in database

2. **Main Application Integration**
   - Web interface for triggering exports
   - Excel export functionality
   - Status monitoring and reporting

3. **Database Schema**
   - `square_item_library_export` table
   - 76 columns matching Square's official format
   - Location-specific inventory data

## Features

### ✅ Complete Data Export
- **76 columns** matching Square's official Item Library Export format
- **986 product variations** (as of latest export)
- **All 7 locations** with individual inventory tracking
- **Real-time data** directly from Square API

### ✅ Category Management
- Categories extracted from Square API
- Both `categories` and `reporting_category` fields populated
- Automatic category mapping and validation

### ✅ Vendor Information
- Vendor names from database relationships
- Vendor codes from Square API vendor SKUs
- Fallback logic for missing data

### ✅ Location-Specific Data
- Individual columns for each location:
  - Aubrey, Bridgefarmer, Building, FloMo, Justin, Quinlan, Terrell
- Per-location fields:
  - Enabled status
  - Current quantity
  - New quantity
  - Stock alert settings
  - Pricing

### ✅ Excel Export
- Direct download of complete export
- Properly formatted column headers
- Timestamp-based filenames

## Usage

### Web Interface

1. **Access the Tool**
   ```
   http://localhost:8080/tools/square-catalog-export
   ```

2. **Start Export**
   - Click "Start Export" to trigger a fresh data sync
   - Monitor progress in the export log
   - Check API and database status

3. **Download Excel**
   - Click "Export to Excel" to download the complete dataset
   - File includes all 76 columns and current data

### API Endpoints

#### Main Application
```bash
# Trigger export
POST /catalog/export

# Download Excel
GET /catalog/export/excel

# Check status
GET /catalog/status
```

#### External Service
```bash
# Start export (external service)
POST http://localhost:5001/export

# Check health
GET http://localhost:5001/health

# Get status
GET http://localhost:5001/status
```

## Data Schema

### Core Fields
- `reference_handle` - Square item ID
- `token` - Square variation ID
- `item_name` - Product name
- `variation_name` - Variation name
- `sku` - Product SKU
- `description` - Product description
- `categories` - Product categories (from Square API)
- `reporting_category` - Same as categories
- `price` - Current price
- `default_unit_cost` - Unit cost from database
- `default_vendor_name` - Vendor name from database
- `default_vendor_code` - Vendor SKU from Square API

### Location-Specific Fields (per location)
- `enabled_{location}` - Whether item is enabled at location
- `current_quantity_{location}` - Current inventory quantity
- `new_quantity_{location}` - New quantity (same as current)
- `stock_alert_enabled_{location}` - Stock alert status
- `stock_alert_count_{location}` - Stock alert threshold
- `price_{location}` - Location-specific pricing

### Locations
- `aubrey`
- `bridgefarmer` 
- `building`
- `flomo`
- `justin`
- `quinlan`
- `terrell`

## Configuration

### Environment Variables

#### Main Application
```bash
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:pass@host:5432/db
SQUARE_ACCESS_TOKEN=your_square_token
SQUARE_ENVIRONMENT=production  # or sandbox
```

#### External Service
```bash
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:pass@host:5432/db
SQUARE_ACCESS_TOKEN=your_square_token
SQUARE_ENVIRONMENT=production  # or sandbox
PORT=5001  # Service port
```

### Docker Configuration

The external service can be run alongside the main application:

```yaml
# docker-compose.yml
services:
  square-catalog-export:
    build: ./square_catalog_export
    ports:
      - "5001:5001"
    environment:
      - SQLALCHEMY_DATABASE_URI=postgresql://user:pass@db:5432/database
      - SQUARE_ACCESS_TOKEN=${SQUARE_ACCESS_TOKEN}
      - SQUARE_ENVIRONMENT=${SQUARE_ENVIRONMENT}
    depends_on:
      - db
```

## Development

### Running Locally

1. **Start External Service**
   ```bash
   cd square_catalog_export
   SQLALCHEMY_DATABASE_URI="postgresql://user:pass@localhost:5432/db" python app.py
   ```

2. **Start Main Application**
   ```bash
   docker-compose -f docker-compose.simple.yml up
   ```

3. **Access Interface**
   ```
   http://localhost:8080/tools/square-catalog-export
   ```

### Testing

```bash
# Test external service health
curl http://localhost:5001/health

# Trigger export
curl -X POST http://localhost:5001/export

# Check status
curl http://localhost:5001/status

# Test Excel export
curl -X GET "http://localhost:8080/catalog/export/excel" -o export.xlsx
```

## Data Flow

1. **Square API Request**
   - Fetch all catalog items with related objects
   - Include categories, variations, vendor info
   - Process in batches of 1000 items

2. **Data Processing**
   - Extract categories from API response
   - Map vendor information from database and API
   - Combine with inventory data from database
   - Transform to match Square's export format

3. **Database Storage**
   - Clear existing export data
   - Insert new records in batches
   - Commit every 100 records for performance

4. **Excel Generation**
   - Query complete dataset from database
   - Format with proper column headers
   - Generate downloadable Excel file

## Troubleshooting

### Common Issues

#### "API Down" Status
- Check if external service is running on port 5001
- Verify network connectivity between containers
- Check Docker networking configuration

#### Empty Categories
- Ensure categories are being extracted from Square API
- Check that `categories` field structure is correct
- Verify category lookup is working

#### Missing Vendor Codes
- Vendor codes come from Square API vendor SKUs
- Check that items have vendor information in Square
- Database `account_number` field is not used

#### Database Connection Issues
- For Docker: Use `host.docker.internal` instead of `localhost`
- Check database credentials and connectivity
- Verify database exists and is accessible

### Logs

#### External Service Logs
```bash
# View service logs
docker-compose logs square-catalog-export

# Or if running locally
tail -f logs/square_catalog_export.log
```

#### Main Application Logs
```bash
# View application logs
docker-compose logs nytex-dashboard

# Check specific export logs
grep "catalog export" logs/app.log
```

## Performance

### Current Metrics
- **Export Time**: ~30-60 seconds for 986 variations
- **Database Size**: ~1MB for complete export
- **Excel File Size**: ~387KB
- **Memory Usage**: <100MB during export

### Optimization
- Batch processing (100 records per commit)
- Async HTTP requests to Square API
- Efficient database queries with proper indexing
- Streaming Excel generation for large datasets

## Security

### API Access
- Square API tokens stored in environment variables
- No API credentials in code or logs
- Secure token handling in production

### Database Access
- Connection strings in environment variables
- No hardcoded credentials
- Proper SQL parameterization

### File Downloads
- Temporary files cleaned up automatically
- No persistent file storage
- Secure file serving through FastAPI

## Maintenance

### Regular Tasks
- Monitor export success rates
- Check for Square API changes
- Update column mappings if needed
- Clean up old export data periodically

### Updates
- External service can be updated independently
- Database schema changes require migration
- Column additions need both service and schema updates

## Support

### Documentation
- This file: Complete system overview
- `square_catalog_export/app.py`: Service implementation
- `app/routes/catalog.py`: Main application integration
- `app/templates/tools/square_catalog_export.html`: Web interface

### Contact
- Check application logs for detailed error messages
- Review Square API documentation for changes
- Test with sandbox environment before production changes 