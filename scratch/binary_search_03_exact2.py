import os
import subprocess
import time

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

original_code = open("backups/binary_search_baseline/03_Security_Dashboard.py", "r", encoding="utf-8").read()

STAGES = {
    "NO_METRICS": original_code.replace('st.metric("Total Records", f"{total_records:,}")', 'pass').replace('st.metric("Manipulated", f"{manipulated_count:,}")', 'pass').replace('st.metric("FDI Attacks", f"{attack_count}")', 'pass').replace('st.metric("Affected Rooms", f"{len(attacked_locations)}")', 'pass'),
    "NO_DATAFRAME_REGISTRY": original_code.replace("st.dataframe(registry_df, width='stretch', hide_index=True)", 'pass'),
    "NO_PLOTLY": original_code.replace("st.plotly_chart(fig, width='stretch')", 'pass').replace("st.plotly_chart(fig_mag, width='stretch')", 'pass'),
    "NO_DATAFRAME_RAW": original_code.replace("st.dataframe(room_attacks[avail_cols], width='stretch')", 'pass'),
}

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
