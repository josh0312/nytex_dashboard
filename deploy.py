#!/usr/bin/env python3
"""
Simple deployment wrapper - calls the enhanced deployment script
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the enhanced deployment script"""
    script_path = Path(__file__).parent / "scripts" / "enhanced_deploy.py"
    
    try:
        # Run the enhanced deployment script
        result = subprocess.run([sys.executable, str(script_path)], cwd=Path(__file__).parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nDeployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error running deployment script: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 