#!/usr/bin/env python3
"""
Run database migration against production Cloud SQL database
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def run_production_migration():
    """Run the migration against production database"""
    
    print("🔄 Running production database migration...")
    print("=" * 50)
    
    # Set environment variables for production database connection
    # These should match the production secrets
    env = os.environ.copy()
    
    # Use the production database URI from secrets
    # This will be loaded from Google Secret Manager in production
    production_db_uri = "postgresql://postgres:NytexSecure2024!@/square_data_sync?host=/cloudsql/nytex-business-systems:us-central1:nytex-main-db"
    
    env['SQLALCHEMY_DATABASE_URI'] = production_db_uri
    env['PYTHONPATH'] = '.'
    
    print(f"📋 Database: Cloud SQL (nytex-business-systems:us-central1:nytex-main-db)")
    print(f"📋 Migration: Add location-specific columns to square_item_library_export")
    
    try:
        # Run the migration
        cmd = ['alembic', '-c', 'migrations/alembic.ini', 'upgrade', 'head']
        
        print(f"🚀 Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print("\nOutput:")
            print(result.stdout)
        else:
            print("❌ Migration failed!")
            print("\nError output:")
            print(result.stderr)
            print("\nStandard output:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_production_migration()
    sys.exit(0 if success else 1) 