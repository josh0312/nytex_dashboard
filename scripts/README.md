# Scripts Directory

This directory contains utility scripts for database maintenance, verification, and administrative tasks.

## Scripts

### `final_verification.py`
**Purpose**: Verification script for the Missing SKU report
- Checks the final state of Missing SKU report
- Verifies that specific items (Big Win and Pyro Supply) are included
- Provides detailed logging and analysis of the data

**Usage**:
```bash
python scripts/final_verification.py
```

### `update_seasons.py`
**Purpose**: Database maintenance script for updating operating seasons
- Updates all July 4th seasons to run from June 24th to July 4th
- Modifies season dates and rule descriptions
- Logs all changes made

**Usage**:
```bash
python scripts/update_seasons.py
```

## Running Scripts

All scripts should be run from the project root directory to ensure proper path resolution:

```bash
# From the project root
cd /path/to/nytex_dashboard
python scripts/script_name.py
```

## Note

These scripts are designed for administrative use and should be run with caution, especially those that modify database records. Always backup your database before running maintenance scripts. 