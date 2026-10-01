import os
import subprocess
import time

STAGES = {
    "FLOAT_DF": """import streamlit as st
import pandas as pd
import numpy as np
st.set_page_config(layout="wide")
df = pd.DataFrame({"Float": [1.1234, 2.5678], "Int": [1, 2]})
st.dataframe(df)
""",
    "DATETIME_TZ_DF": """import streamlit as st
import pandas as pd
st.set_page_config(layout="wide")
df = pd.DataFrame({"Time": pd.date_range("2026-01-01", periods=2, tz="UTC+05:30")})
st.dataframe(df)
"""
}

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\05_Campus_Configuration.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Campus Configuration"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

for stage_name, stage_code in STAGES.items():
    print(f"\\n{'='*50}\\nRUNNING {stage_name}\\n{'='*50}")
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(stage_code)
        
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
    time.sleep(2)
