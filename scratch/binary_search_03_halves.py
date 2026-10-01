import os
import subprocess
import time

ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"
TARGET = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"

with open(TARGET, "r", encoding="utf-8") as f:
    lines = f.readlines()

def run_test(code):
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(code)
    process = subprocess.Popen(
        ["npm.cmd", "--prefix", "desktop", "start"], 
        env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    crashed = False
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line: print(line)
        if "[RENDER-GONE]" in line:
            crashed = True
            break
        if "[TEST] Sequence complete" in line or "Error executing JS" in line or "[FAIL-LOAD]" in line:
            break
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    time.sleep(2)
    return crashed

print("Testing top half...")
top_half = "".join(lines[:40])
if not run_test(top_half):
    print("TOP HALF PASSED. BUG IS IN BOTTOM HALF.")
else:
    print("TOP HALF CRASHED. BUG IS IN TOP HALF.")
