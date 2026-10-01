import os
import subprocess
import time

STAGES = {
    "METRIC_1": """import streamlit as st; st.metric("Total Records", "1,000")""",
    "METRIC_2": """import streamlit as st; st.metric("Total Records", 1000)""",
    "METRIC_3": """import streamlit as st; st.metric("Total Records", f"{1000:,}")""",
    "DATAFRAME_EMPTY": """import streamlit as st; import pandas as pd; st.dataframe(pd.DataFrame(columns=["A", "B"]))""",
    "DATAFRAME_HIDE_INDEX": """import streamlit as st; import pandas as pd; st.dataframe(pd.DataFrame({"A": [1,2]}), hide_index=True)""",
    "PLOTLY": """import streamlit as st; import pandas as pd; import plotly.express as px; st.plotly_chart(px.line(pd.DataFrame({"A": [1], "B": [2]}), x="A", y="B"))""",
    "SELECTBOX": """import streamlit as st; st.selectbox("Test", ["A", "B"])"""
}

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
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
