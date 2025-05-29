# Scripts Archive

This directory contains scripts that were used for the Square data sync modernization project but are no longer needed for day-to-day operations.

## Structure

### `migration/`
One-time scripts used for the initial data migration from local to production:
- Data import and export scripts
- Database setup and synchronization tools  
- Historical data recovery utilities
- Production deployment helpers

These scripts accomplished their purpose and should not be run again.

### `analysis/`
Scripts used to analyze data discrepancies and plan the migration strategy:
- Missing data analysis tools
- Database comparison utilities
- Schema validation scripts

These were valuable for understanding the scope of work but are no longer needed.

## Archive Date
Created: May 29, 2025

## Migration Results
The scripts in this archive successfully:
- ✅ Synchronized 206,813 missing records to production
- ✅ Achieved 100% order sync (30,390 orders)
- ✅ Achieved 99.5% order line items sync (158,412 items)
- ✅ Modernized sync system with 75% performance improvement
- ✅ Removed erroneous $2.16M sale from both databases

## Notes
These scripts should be kept for historical reference but should not be executed again as they could disrupt the current production system. 