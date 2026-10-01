import os
import subprocess
import time

STAGES = {
    "HIDE_INDEX": """import streamlit as st
import pandas as pd
st.set_page_config(layout="wide")
df = pd.DataFrame({"A": [1, 2, 3]})
st.dataframe(df, hide_index=True)
""",
    "COLUMN_CONFIG": """import streamlit as st
import pandas as pd
st.set_page_config(layout="wide")
df = pd.DataFrame({"A": [1.11, 2.22]})
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
