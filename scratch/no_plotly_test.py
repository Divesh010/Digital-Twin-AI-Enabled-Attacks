import os
import subprocess
import time

ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

with open(r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

text = text.replace("st.plotly_chart(fig, use_container_width=True)", "# st.plotly_chart(fig)")
text = text.replace("st.plotly_chart(fig_mag, use_container_width=True)", "# st.plotly_chart(fig_mag)")

with open(r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py", "w", encoding="utf-8") as f:
    f.write(text)

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
