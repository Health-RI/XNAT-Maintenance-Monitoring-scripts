#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: docker run -v $(pwd):/data xnat-scripts <script_name> [script_args...]")
        print("\nAvailable scripts:")
        
        # List all Python scripts in the scripts directory
        script_dir = Path("/app/scripts")
        python_scripts = [f.name for f in script_dir.glob("*.py")]
        
        for script in sorted(python_scripts):
            print(f"  {script}")
        
        sys.exit(1)
    
    script_name = sys.argv[1]
    script_args = sys.argv[2:]
    
    # Ensure script has .py extension
    if not script_name.endswith('.py'):
        script_name += '.py'
    
    script_path = Path("/app/scripts") / script_name
    
    if not script_path.exists():
        print(f"Error: Script '{script_name}' not found.")
        sys.exit(1)
    
    # Change to the data directory (mounted volume)
    os.chdir("/data")
    
    # Execute the script
    try:
        subprocess.run([sys.executable, str(script_path)] + script_args, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()