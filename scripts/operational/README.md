# Operational Scripts

These scripts are used for system maintenance, testing, and occasional operational tasks.

## Monitoring & Verification

### `verify_production_status.py`
Comprehensive production database health check:
- Verifies table counts and data integrity
- Compares local vs production data
- Reports sync status

### `check_production_health.sh` 
Basic health monitoring script

## System Management

### `setup_daily_sync.sh`
Configures the daily sync schedule and monitoring

### `update_scheduler_to_incremental.sh`
Updates Google Cloud Scheduler to use the new incremental sync

## Error Handling

### `delete_erroneous_sale.py`
Tool for safely removing erroneous sales data from both databases
- Includes safety checks and confirmations
- Verifies deletion across environments

## Usage

These scripts may be run occasionally for maintenance but are not part of the daily operations:

```bash
# Check production status
python scripts/operational/verify_production_status.py

# Test sync functionality  
python scripts/operational/test_incremental_sync.py

# Remove erroneous data (use with caution)
python scripts/operational/delete_erroneous_sale.py
```

## Safety Notes

- Always test scripts in development first
- Some scripts modify production data - use with extreme caution
- Review script output carefully before confirming destructive operations
- For testing scripts, see the `tests/` directory 