import os
import subprocess
import sys
from pathlib import Path

def main():
    dashboard_app = Path("src/dashboard/app.py")
    if not dashboard_app.exists():
        print(f"Error: {dashboard_app} not found.")
        sys.exit(1)
        
    # Set PYTHONPATH so absolute imports like rom config.models import ... work
    env = os.environ.copy()
    src_path = str(Path("src").resolve())
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    print(f"Starting Streamlit dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_app)], env=env)

if __name__ == "__main__":
    main()
