import os
import subprocess
import time

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

minimal_03 = """import streamlit as st
import pandas as pd
st.set_page_config(page_title="Security Dashboard", layout="wide")
st.title("Minimal 03")
st.write("Hello")
"""

with open(TARGET_FILE, "w", encoding="utf-8") as f:
    f.write(minimal_03)
    
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
