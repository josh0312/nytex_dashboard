# NYTex Dashboard Scripts

This directory contains operational scripts for the NYTex Dashboard system.

## Core Operational Scripts

### `daily_sync.py`
The main Square data synchronization script. Runs daily to sync new orders, inventory, and catalog data.

### `sync_catalog_from_square.py`
Dedicated script for syncing catalog data from Square API.

### `sync_inventory_only.py`
Inventory-specific sync script for updating stock levels.

### `update_seasons.py`
Updates operating seasons data for sales reporting.

### `check_production_health.sh`
Health check script for monitoring production database status.

### `setup_monitoring.sh`
Sets up monitoring and alerting for the sync system.

## Additional Directories

### `operational/`
Scripts that might be used occasionally for system maintenance:
- Production verification tools
- Testing utilities  
- Error handling scripts
- Scheduler configuration

### `archive/`
Historical scripts from the Square data sync modernization project (May 2025). These accomplished their purpose and should not be run again. See `archive/README.md` for details.

## Usage

Most scripts are designed to be run from the project root directory:

```bash
# Run daily sync
python scripts/daily_sync.py

# Check production health
./scripts/check_production_health.sh

# Sync catalog data
python scripts/sync_catalog_from_square.py
```

## Notes

- All scripts use the application's logging configuration
- Scripts assume proper environment variables are set
- Production scripts require appropriate database credentials 