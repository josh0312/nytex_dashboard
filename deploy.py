#!/usr/bin/env python3
"""
Simple Deploy Script
One-command deployment with integrated testing and monitoring
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the comprehensive test, deploy, and monitor script"""
    script_path = Path(__file__).parent / "scripts" / "test_deploy_monitor.py"
    
    try:
        # Run the comprehensive script
        result = subprocess.run([sys.executable, str(script_path)], 
                              cwd=Path(__file__).parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error running deployment script: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 