import os
import subprocess
import time
import shutil
import re

base = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin"
shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/pages/03_Security_Dashboard.py"), os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"))

with open(os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"), "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Remove all st.markdown calls
text = re.sub(r'st\.markdown\(.*?\)', '# st.markdown()', text, flags=re.DOTALL)

with open(os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"), "w", encoding="utf-8") as f:
    f.write(text)

ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

process = subprocess.Popen(
    ["npm.cmd", "--prefix", "desktop", "start"], 
    env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)
for line in iter(process.stdout.readline, ''):
    line = line.strip()
    if line: print(line)
    if "[TEST] Sequence complete" in line or "[RENDER-GONE]" in line or "Error executing JS" in line or "[FAIL-LOAD]" in line:
        break
subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
