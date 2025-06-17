#!/usr/bin/env python3
"""
Development Cron Job Setup and Testing
Sets up cron jobs for the sync system in development environment
"""

import os
import subprocess
import sys
from pathlib import Path

def get_project_root():
    """Get the absolute path to the project root"""
    return Path(__file__).parent.absolute()

def get_python_path():
    """Get the Python path for the virtual environment"""
    if 'VIRTUAL_ENV' in os.environ:
        return os.path.join(os.environ['VIRTUAL_ENV'], 'bin', 'python')
    else:
        return sys.executable

def create_cron_script():
    """Create a wrapper script for cron to use"""
    project_root = get_project_root()
    python_path = get_python_path()
    
    cron_script_content = f"""#!/bin/bash
# NyTex Sync System Cron Job Wrapper
# Generated automatically - do not edit manually

# Set up environment
export PATH="{os.environ.get('PATH', '')}"
export VIRTUAL_ENV="{os.environ.get('VIRTUAL_ENV', '')}"

# Change to project directory
cd "{project_root}"

# Load environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

# Run the sync orchestrator
"{python_path}" scripts/sync_orchestrator.py "$@" >> logs/cron.log 2>&1
"""
    
    script_path = project_root / "scripts" / "cron_sync.sh"
    
    with open(script_path, 'w') as f:
        f.write(cron_script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    
    print(f"✅ Created cron wrapper script: {script_path}")
    return script_path

def create_cron_jobs():
    """Create cron job entries for development"""
    project_root = get_project_root()
    script_path = project_root / "scripts" / "cron_sync.sh"
    
    # Development cron jobs (more frequent for testing)
    cron_jobs = [
        # Daily sync at 2:00 AM (production schedule)
        f"0 2 * * * {script_path} > /dev/null 2>&1",
        
        # Test sync every 30 minutes during business hours (dev only)
        f"*/30 9-17 * * 1-5 {script_path} --data-type catalog_items > /dev/null 2>&1",
    ]
    
    return cron_jobs

def show_current_cron():
    """Show current crontab"""
    print("\n📋 Current Crontab:")
    print("=" * 50)
    
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No crontab currently installed")
    except Exception as e:
        print(f"Error reading crontab: {e}")

def test_cron_script():
    """Test the cron script manually"""
    print("\n🧪 Testing Cron Script:")
    print("=" * 50)
    
    project_root = get_project_root()
    script_path = project_root / "scripts" / "cron_sync.sh"
    
    if not script_path.exists():
        print("❌ Cron script not found - run setup first")
        return False
    
    print("Running test sync (dry-run mode)...")
    
    try:
        # Test with dry-run and catalog items (fast)
        result = subprocess.run([
            str(script_path), 
            '--dry-run', 
            '--data-type', 'catalog_items'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Cron script test successful!")
            print("\nOutput:")
            print(result.stdout)
            return True
        else:
            print("❌ Cron script test failed!")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Cron script test timed out (>60s)")
        return False
    except Exception as e:
        print(f"❌ Error testing cron script: {e}")
        return False

def setup_dev_cron():
    """Set up development cron jobs"""
    print("🔧 Setting up Development Cron Jobs")
    print("=" * 50)
    
    # Create necessary directories
    project_root = get_project_root()
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create cron script
    script_path = create_cron_script()
    
    # Test the script
    if not test_cron_script():
        print("⚠️  Cron script test failed - please fix issues before proceeding")
        return False
    
    # Show suggested cron jobs
    cron_jobs = create_cron_jobs()
    
    print(f"\n📅 Suggested Cron Jobs for Development:")
    print("=" * 50)
    for job in cron_jobs:
        print(f"  {job}")
    
    print(f"\n📝 To install these cron jobs:")
    print("1. Copy the cron job lines above")
    print("2. Run: crontab -e")
    print("3. Paste the lines and save")
    print("\n⚠️  Note: These are development cron jobs with more frequent syncing")
    print("Production will use different schedule (daily at 2 AM)")
    
    return True

def show_production_cron():
    """Show what the production cron jobs should look like"""
    print("\n🏭 Production Cron Jobs (for reference):")
    print("=" * 50)
    
    prod_jobs = [
        "# NyTex Sync System - Production Schedule",
        "0 2 * * * /app/scripts/cron_sync.sh > /dev/null 2>&1",
        "# Runs daily at 2:00 AM UTC"
    ]
    
    for job in prod_jobs:
        print(f"  {job}")

def main():
    """Main function"""
    print("🚀 NyTex Development Cron Setup")
    print("=" * 60)
    
    # Show current cron
    show_current_cron()
    
    # Setup development cron
    success = setup_dev_cron()
    
    if success:
        # Show production reference
        show_production_cron()
        
        print("\n" + "=" * 60)
        print("🎉 Development cron setup complete!")
        print("\n📋 Next Steps:")
        print("1. Install the suggested cron jobs using 'crontab -e'")
        print("2. Monitor logs/cron.log for sync activity")
        print("3. Test with: scripts/cron_sync.sh --dry-run")
        print("4. Ready for production deployment!")
    else:
        print("\n❌ Cron setup failed - please fix the issues above")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 