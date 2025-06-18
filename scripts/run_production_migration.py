#!/usr/bin/env python3
"""
Manual production migration script
Runs the items_view migration against the production database
"""

import os
import subprocess
import sys
from pathlib import Path

def run_migration():
    """Run the database migration against production"""
    print("🔄 Running production database migration...")
    
    # Get the repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)
    
    try:
        # Load production database URI from Google Secret Manager
        print("📊 Getting production database URI...")
        result = subprocess.run([
            'gcloud', 'secrets', 'versions', 'access', 'latest', 
            '--secret=database-uri'
        ], capture_output=True, text=True, check=True)
        
        database_uri = result.stdout.strip()
        if not database_uri:
            raise ValueError("Database URI is empty")
        
        print("✅ Database URI retrieved")
        
        # Set environment variables
        env = os.environ.copy()
        env['SQLALCHEMY_DATABASE_URI'] = database_uri
        env['PYTHONPATH'] = str(repo_root)
        
        # Run Alembic migration
        print("🔄 Running Alembic migration...")
        cmd = ['alembic', '-c', 'migrations/alembic.ini', 'upgrade', 'head']
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print("Output:", result.stdout)
        else:
            print("❌ Migration failed!")
            print("Error:", result.stderr)
            return False
            
        # Verify the items_view was created
        print("🔍 Verifying items_view creation...")
        
        # Test that we can query the view
        test_cmd = [
            'psql', database_uri, '-c', 
            "SELECT COUNT(*) FROM items_view LIMIT 1;"
        ]
        
        test_result = subprocess.run(test_cmd, capture_output=True, text=True)
        
        if test_result.returncode == 0:
            print("✅ items_view verification successful!")
            print("View output:", test_result.stdout)
        else:
            print("⚠️  Could not verify items_view (may require Cloud SQL proxy)")
            print("Verification error:", test_result.stderr)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1) 